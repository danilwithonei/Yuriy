'use client';

import React, { useEffect, useState, use, useRef } from 'react';
import api, { API_URL } from '@/lib/api';
import { Send, User, Bot, History, FileText, MessageSquare, Info, ChevronRight, UserCircle, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useCaseChat } from '@/hooks/useCaseChat';
import { useCaseStore } from '@/store/useCaseStore';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface DBMessage {
  sender_role: string;
  content: string;
  timestamp: string;
}

interface CaseData {
  case: {
    id: string;
    status: string;
    case_file: string | null;
    client_id: number;
    case_type: string;
    title?: string | null;
    summary?: string | null;
  };
  messages: DBMessage[];
}

function formatTime(ts?: string): string {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const hh = d.getHours().toString().padStart(2, '0');
  const mm = d.getMinutes().toString().padStart(2, '0');
  if (d.toDateString() === now.toDateString()) return `${hh}:${mm}`;
  const dd = d.getDate().toString().padStart(2, '0');
  const mo = (d.getMonth() + 1).toString().padStart(2, '0');
  return `${dd}.${mo} ${hh}:${mm}`;
}

export default function CaseDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const caseId = id;
  const [data, setData] = useState<CaseData | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [intakeInput, setIntakeInput] = useState('');
  const [isIntakeSending, setIsIntakeSending] = useState(false);
  const [intakeReady, setIntakeReady] = useState(false);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [streamingIntakeContent, setStreamingIntakeContent] = useState('');
  const [forbidden, setForbidden] = useState(false);
  const { messages: chatMessages, setMessages: setChatMessages, sendMessage, isConnected, isThinking, streamingContent, error, clearError } = useCaseChat(caseId);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const storeCase = useCaseStore((state) => state.cases.find(c => c.id === caseId));
  const fetchData = React.useCallback(() => {
    setForbidden(false);
    api.get(`/cases/${id}`)
      .then(res => {
        setData(res.data);
        const existingAssists = res.data.messages
          .filter((m: any) => m.sender_role === 'lawyer' || m.sender_role === 'ai_case')
          .map((m: any) => ({ role: m.sender_role, content: m.content, timestamp: m.timestamp }));
        setChatMessages(existingAssists);
      })
      .catch(err => {
        if (err?.response?.status === 403) {
          setForbidden(true);
        } else {
          console.error(err);
        }
      });
  }, [id, setChatMessages]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (storeCase?.status === 'ready' && data?.case.status !== 'ready') {
      fetchData();
    }
  }, [storeCase?.status, data?.case.status, fetchData]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo(0, scrollRef.current.scrollHeight);
    }
  }, [chatMessages, data?.case.case_file, data?.messages]);

  const handleSend = () => {
    if (!chatInput.trim()) return;
    sendMessage(chatInput);
    setChatInput('');
  };

  const handleIntakeSend = async () => {
    if (!intakeInput.trim() || isIntakeSending) return;
    const msg = intakeInput;
    setIntakeInput('');
    setIsIntakeSending(true);
    setIntakeError(null);
    setStreamingIntakeContent('');
    // Показываем сообщение клиента сразу (optimistic)
    const clientTs = new Date().toISOString();
    setData(prev => prev ? {
      ...prev,
      messages: [...prev.messages, { sender_role: 'client', content: msg, timestamp: clientTs }]
    } : prev);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/cases/${id}/intake/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ message: msg })
      });
      if (!response.ok) {
        let errMsg = 'Ошибка отправки';
        try { errMsg = (await response.json()).detail; } catch {}
        throw new Error(errMsg);
      }
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullContent = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let data;
          try { data = JSON.parse(line.slice(6)); } catch { continue; }
          if (data.token) {
            fullContent += data.token;
            setStreamingIntakeContent(fullContent);
          } else if (data.response) {
            fullContent = data.response;
            setStreamingIntakeContent(fullContent);
          } else if (data.is_ready !== undefined) {
            setIntakeReady(data.is_ready);
          } else if (data.done) {
            if (data.is_ready !== undefined) setIntakeReady(data.is_ready);
          } else if (data.error) {
            throw new Error(data.error);
          }
        }
      }
      // Финализируем: добавляем сообщение в список
      setStreamingIntakeContent('');
      setData(prev => prev ? {
        ...prev,
        messages: [...prev.messages, { sender_role: 'ai_intake', content: fullContent, timestamp: new Date().toISOString() }]
      } : prev);
    } catch (e: any) {
      const errMsg = e?.message || 'Ошибка отправки';
      setIntakeError(errMsg);
      setStreamingIntakeContent('');
    } finally {
      setIsIntakeSending(false);
    }
  };

  const handleIntakeConfirm = async () => {
    try {
      await api.post(`/cases/${id}/intake/confirm`);
      setData(prev => prev ? { ...prev, case: { ...prev.case, status: 'researching' } } : prev);
      useCaseStore.getState().updateCaseStatus(caseId, 'researching');
    } catch (e: any) {
      setIntakeError(e?.response?.data?.detail || 'Ошибка подтверждения');
    }
  };

  if (forbidden) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center space-y-3">
        <div className="text-4xl font-bold text-gray-300">403</div>
        <p className="text-sm text-gray-500">Нет доступа к этому делу</p>
      </div>
    </div>
  );

  if (!data) return (
    <div className="flex items-center justify-center h-full text-muted-foreground animate-pulse">
      Загрузка материалов дела...
    </div>
  );

  const status = data.case.status;
  const caseType = data.case.case_type;
  const isDirect = caseType === 'direct';
  const isIntakeMode = caseType === 'intake' && (status === 'open' || status === 'researching');
  const isAssistantMode = caseType === 'direct' || (caseType === 'intake' && status === 'ready');

  // Intake history messages
  const intakeMessages = data.messages.filter(m => m.sender_role === 'client' || m.sender_role === 'ai_intake');

  return (
    <div className="flex flex-col flex-1 h-full overflow-hidden bg-white dark:bg-[#171717]">
      {/* Шапка чата */}
      <div className="h-14 border-b dark:border-gray-800 px-6 flex items-center justify-between sticky top-0 z-10 bg-white/80 dark:bg-[#171717]/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <h1 className="font-semibold text-sm">{data.case.title || (isDirect ? 'Чат' : 'Дело') + ' №' + id.slice(0, 8)}</h1>
          {isIntakeMode && (
            <>
              <div className="h-2 w-2 rounded-full bg-amber-500" />
              <span className="text-[10px] text-gray-400 uppercase font-medium tracking-wider">
                {status === 'researching' ? 'Идёт исследование' : 'Сбор данных'}
              </span>
            </>
          )}
          {isAssistantMode && !isDirect && (
            <>
              <div className={`h-2 w-2 rounded-full ${status === 'ready' ? 'bg-emerald-500' : 'bg-gray-300'}`} />
              <span className="text-[10px] text-gray-400 uppercase font-medium tracking-wider">
                {status === 'ready' ? 'Исследование завершено' : ''}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isAssistantMode && !isDirect && (
            <Sheet>
              <SheetTrigger 
                render={
                  <button className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors">
                    <History className="h-4 w-4" />
                    <span>История приема</span>
                  </button>
                }
              />
              <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto p-0 border-l dark:border-gray-800">
                <div className="flex flex-col h-full">
                  <SheetHeader className="p-6 border-b dark:border-gray-800">
                    <SheetTitle>История приема</SheetTitle>
                    <SheetDescription>Первичный диалог клиента с ИИ-приемщиком</SheetDescription>
                  </SheetHeader>
                  <ScrollArea className="flex-1">
                    <div className="p-8 space-y-8">
                      {intakeMessages.map((m, i) => (
                        <div key={i} className="flex flex-col gap-2">
                          <div className="flex items-center gap-2 text-[10px] uppercase font-bold text-gray-400">
                            {m.sender_role === 'client' ? <UserCircle className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                            {m.sender_role === 'client' ? 'Клиент' : 'ИИ-Помощник'}
                          </div>
                          <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300 bg-gray-50/50 dark:bg-gray-900/50 p-4 rounded-xl border dark:border-gray-800 shadow-sm">
                            {m.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              </SheetContent>
            </Sheet>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-3 flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/30 text-sm text-red-700 dark:text-red-400 animate-in fade-in slide-in-from-top-2 duration-300">
          <span>{error}</span>
          <button onClick={clearError} className="p-1 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-md transition-colors">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
      )}

      {intakeError && (
        <div className="mx-6 mt-3 flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/30 text-sm text-red-700 dark:text-red-400 animate-in fade-in slide-in-from-top-2 duration-300">
          <span>{intakeError}</span>
          <button onClick={() => setIntakeError(null)} className="p-1 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-md transition-colors">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
      )}

      {/* INTAKE MODE */}
      {isIntakeMode && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {status === 'researching' ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="flex flex-col items-center gap-4 text-center">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Идёт исследование...</span>
                </div>
                <p className="text-xs text-gray-400 max-w-xs">
                  ИИ изучает законы по вашему делу и формирует досье. Это может занять до минуты.
                </p>
              </div>
            </div>
          ) : (
            <>
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto scroll-smooth no-scrollbar"
              >
                <div className="max-w-5xl mx-auto py-10 px-6 space-y-6">
                  {intakeMessages.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-16 text-center space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                      <Avatar className="h-12 w-12 border shadow-sm">
                        <AvatarFallback className="bg-amber-50 text-amber-600">
                          <FileText className="h-6 w-6" />
                        </AvatarFallback>
                      </Avatar>
                      <div className="space-y-2">
                        <h3 className="font-medium text-sm">Приём данных</h3>
                        <p className="text-xs text-gray-400 max-w-sm">
                          Опишите ситуацию от лица клиента. ИИ будет задавать уточняющие вопросы.
                        </p>
                      </div>
                    </div>
                  )}

                  {intakeMessages.map((m, i) => (
                    <div key={i} className="flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300">
                      <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
                        {m.sender_role === 'client' ? (
                          <AvatarFallback className="bg-gray-100 text-gray-600">
                            <UserCircle className="h-4 w-4" />
                          </AvatarFallback>
                        ) : (
                          <AvatarFallback className="bg-amber-50 text-amber-600">
                            <Bot className="h-4 w-4" />
                          </AvatarFallback>
                        )}
                      </Avatar>
                      <div className="flex-1 space-y-1.5 overflow-hidden">
                        <div className="font-semibold text-sm flex items-center gap-2">
                          {m.sender_role === 'client' ? 'Вы (от лица клиента)' : 'ИИ-Приёмщик'}
                          {m.timestamp && <span className="text-[10px] text-gray-400 font-normal">{formatTime(m.timestamp)}</span>}
                        </div>
                        <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200 prose prose-neutral dark:prose-invert max-w-none">
                          {m.content}
                        </div>
                      </div>
                    </div>
                  ))}

                  {isIntakeSending && (
                    <div className="flex gap-4 group animate-in fade-in duration-500">
                      <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
                        <AvatarFallback className="bg-amber-50 text-amber-600">
                          <Bot className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 space-y-2 overflow-hidden">
                        <div className="font-semibold text-sm">ИИ-Приёмщик</div>
                        {streamingIntakeContent ? (
                          <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200">
                            {streamingIntakeContent}
                            <span className="inline-block w-1.5 h-4 bg-amber-500 ml-0.5 animate-pulse" />
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 py-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-bounce [animation-delay:-0.3s]" />
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-bounce [animation-delay:-0.15s]" />
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-bounce" />
                            <span className="text-xs text-gray-400 ml-2 font-medium">Анализирует...</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {intakeReady && (
                    <div className="flex justify-center pt-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                      <Button
                        onClick={handleIntakeConfirm}
                        className="h-11 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-lg"
                      >
                        Подтвердить отправку
                      </Button>
                    </div>
                  )}

                  <div className="h-8" />
                </div>
              </div>

              <div className="px-6 pb-4 bg-gradient-to-t from-white via-white/80 to-transparent dark:from-[#171717] dark:via-[#171717]/80">
                <div className="max-w-5xl mx-auto">
                  <div className="relative flex items-center bg-white dark:bg-[#212121] border dark:border-gray-800 shadow-2xl rounded-2xl overflow-hidden p-1.5 focus-within:ring-2 focus-within:ring-amber-500/20 transition-all">
                    <Input
                      value={intakeInput}
                      onChange={(e) => setIntakeInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleIntakeSend()}
                      placeholder="Опишите ситуацию от лица клиента..."
                      className="border-0 focus-visible:ring-0 bg-transparent h-12 py-3 px-4 text-[15px]"
                      disabled={isIntakeSending || intakeReady}
                    />
                    <Button 
                      size="icon" 
                      onClick={handleIntakeSend} 
                      disabled={isIntakeSending || intakeReady || !intakeInput.trim()}
                      className="h-10 w-10 rounded-xl bg-amber-600 hover:bg-amber-700 text-white shadow-sm"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ASSISTANT MODE */}
      {isAssistantMode && (
        <>
          <div 
            ref={scrollRef}
            className="flex-1 overflow-y-auto scroll-smooth no-scrollbar"
          >
            <div className="max-w-5xl mx-auto py-10 px-6 space-y-12">
              
              {!isDirect && (
                <div className="flex gap-4 group">
                  <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
                    <AvatarFallback className="bg-emerald-50 text-emerald-600">
                      <FileText className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-3 overflow-hidden">
                    <div className="font-semibold text-sm flex items-center gap-2">
                      Сформированное досье
                    </div>
                    <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200 prose prose-neutral dark:prose-invert max-w-none bg-emerald-50/30 dark:bg-emerald-900/10 p-6 rounded-2xl border border-emerald-100/50 dark:border-emerald-800/20 shadow-sm">
                      {data.case.case_file ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {data.case.case_file}
                        </ReactMarkdown>
                      ) : (
                        <div className="flex items-center gap-3 py-4 text-emerald-600/60 dark:text-emerald-400/60 italic">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Досье не сформировано
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {chatMessages.length === 0 && isDirect && (
                <div className="flex flex-col items-center justify-center py-16 text-center space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <Avatar className="h-12 w-12 border shadow-sm">
                    <AvatarFallback className="bg-blue-50 text-blue-600">
                      <Bot className="h-6 w-6" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <h3 className="font-medium text-sm">Чем могу помочь?</h3>
                    <p className="text-xs text-gray-400 max-w-sm">
                      Задайте юридический вопрос, и я найду нужную информацию с веб-поиском.
                    </p>
                  </div>
                </div>
              )}

              {chatMessages.length === 0 && !isDirect && data.case.case_file && (
                <div className="flex flex-col items-center justify-center py-10 text-center space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <Avatar className="h-10 w-10 border shadow-sm">
                    <AvatarFallback className="bg-blue-50 text-blue-600 italic font-serif">Y</AvatarFallback>
                  </Avatar>
                  <div className="space-y-1">
                    <h3 className="font-medium text-sm">Досье готово к анализу</h3>
                    <p className="text-xs text-gray-400 max-w-sm">
                      Вы можете задать уточняющие вопросы по этому делу или попросить меня подготовить документы.
                    </p>
                  </div>
                </div>
              )}

              {chatMessages.map((m, i) => (
                <div key={i} className="flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
                    {m.role === 'lawyer' ? (
                      <AvatarFallback className="bg-gray-100 text-gray-600">U</AvatarFallback>
                    ) : (
                      <AvatarFallback className="bg-blue-50 text-blue-600">
                        <Bot className="h-4 w-4" />
                      </AvatarFallback>
                    )}
                  </Avatar>
                  <div className="flex-1 space-y-1.5 overflow-hidden">
                    <div className="font-semibold text-sm flex items-center gap-2">
                      {m.role === 'lawyer' ? 'Вы' : 'ИИ-Ассистент'}
                      {m.timestamp && <span className="text-[10px] text-gray-400 font-normal">{formatTime(m.timestamp)}</span>}
                    </div>
                    <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200 prose prose-neutral dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {m.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))}

              {isThinking && (
                <div className="flex gap-4 group animate-in fade-in duration-500">
                  <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
                    <AvatarFallback className="bg-blue-50 text-blue-600">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-2 overflow-hidden">
                    <div className="font-semibold text-sm">ИИ-Ассистент</div>
                    <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200 prose prose-neutral dark:prose-invert max-w-none">
                      {streamingContent ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {streamingContent}
                        </ReactMarkdown>
                      ) : (
                        <div className="flex items-center gap-1.5 py-1">
                          <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.3s]" />
                          <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.15s]" />
                          <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" />
                          <span className="text-xs text-gray-400 ml-2 font-medium">Ищет информацию...</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div className="h-32" />
            </div>
          </div>

          <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-white via-white/80 to-transparent dark:from-[#171717] dark:via-[#171717]/80 pointer-events-none">
            <div className="max-w-5xl mx-auto relative pointer-events-auto">
              <div className="relative flex items-center bg-white dark:bg-[#212121] border dark:border-gray-800 shadow-2xl rounded-2xl overflow-hidden p-1.5 focus-within:ring-2 focus-within:ring-black/5 dark:focus-within:ring-white/5 transition-all">
                <Input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={isDirect ? "Задайте юридический вопрос..." : "Спросите ассистента о деталях дела..."}
                  className="border-0 focus-visible:ring-0 bg-transparent h-12 py-3 px-4 text-[15px]"
                  disabled={!isConnected}
                />
                <Button 
                  size="icon" 
                  onClick={handleSend} 
                  disabled={!isConnected || !chatInput.trim()}
                  className="h-10 w-10 rounded-xl bg-black dark:bg-white text-white dark:text-black hover:opacity-90 transition-opacity shadow-sm"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="text-[10px] text-center mt-3 text-gray-400 tracking-wide font-medium">
                YURIY AI МОЖЕТ ОШИБАТЬСЯ • ПРОВЕРЯЙТЕ ВАЖНУЮ ИНФОРМАЦИЮ
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
