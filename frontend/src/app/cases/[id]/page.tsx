'use client';

import React, { useEffect, useState, use, useRef } from 'react';
import axios from 'axios';
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
    id: number;
    status: string;
    case_file: string | null;
    client_id: number;
  };
  messages: DBMessage[];
}

export default function CaseDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const caseId = parseInt(id);
  const [data, setData] = useState<CaseData | null>(null);
  const [chatInput, setChatInput] = useState('');
  const { messages: chatMessages, setMessages: setChatMessages, sendMessage, isConnected, isThinking } = useCaseChat(caseId);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Подписываемся на стор, чтобы ловить обновления статуса в реальном времени
  const storeCase = useCaseStore((state) => state.cases.find(c => c.id === caseId));

  const fetchData = React.useCallback(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    axios.get(`${apiUrl}/cases/${id}`)
      .then(res => {
        setData(res.data);
        const existingAssists = res.data.messages
          .filter((m: any) => m.sender_role === 'lawyer' || m.sender_role === 'ai_case')
          .map((m: any) => ({ role: m.sender_role, content: m.content }));
        setChatMessages(existingAssists);
      })
      .catch(err => console.error(err));
  }, [id, setChatMessages]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Если статус в сторе изменился на ready, и у нас еще нет досье в локальном стейте — переподтягиваем данные
  useEffect(() => {
    if (storeCase?.status === 'ready' && data?.case.status !== 'ready') {
      fetchData();
    }
  }, [storeCase?.status, data?.case.status, fetchData]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo(0, scrollRef.current.scrollHeight);
    }
  }, [chatMessages, data?.case.case_file]);

  const handleSend = () => {
    if (!chatInput.trim()) return;
    sendMessage(chatInput);
    setChatInput('');
  };

  if (!data) return (
    <div className="flex items-center justify-center h-full text-muted-foreground animate-pulse">
      Загрузка материалов дела...
    </div>
  );

  return (
    <div className="flex flex-col flex-1 h-full overflow-hidden bg-white dark:bg-[#171717]">
      {/* Шапка чата */}
      <div className="h-14 border-b dark:border-gray-800 px-6 flex items-center justify-between sticky top-0 z-10 bg-white/80 dark:bg-[#171717]/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <h1 className="font-semibold text-sm">Дело №{id}</h1>
          <div 
            className={`h-2 w-2 rounded-full ${
              (storeCase?.status || data.case.status) === 'ready' ? 'bg-emerald-500' : 
              (storeCase?.status || data.case.status) === 'researching' ? 'bg-blue-500 animate-pulse' : 'bg-amber-500'
            }`} 
          />
          <span className="text-[10px] text-gray-400 uppercase font-medium tracking-wider">
            {(storeCase?.status || data.case.status) === 'ready' ? 'Исследование завершено' : 'В процессе анализа'}
          </span>
        </div>

        <div className="flex items-center gap-2">
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
                    {data.messages.filter(m => m.sender_role === 'client' || m.sender_role === 'ai_intake').map((m, i) => (
                      <div key={i} className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-[10px] uppercase font-bold text-gray-400">
                          {m.sender_role === 'client' ? <UserCircle className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                          {m.sender_role === 'client' ? 'Клиент' : 'ИИ-Приемщик'}
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
        </div>
      </div>

      {/* Область сообщений */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto scroll-smooth no-scrollbar"
      >
        <div className="max-w-5xl mx-auto py-10 px-6 space-y-12">
          
          {/* Досье как первое сообщение */}
          <div className="flex gap-4 group">
            <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
              <AvatarFallback className="bg-emerald-50 text-emerald-600">
                <FileText className="h-4 w-4" />
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 space-y-3 overflow-hidden">
              <div className="font-semibold text-sm flex items-center gap-2">
                Сформированное досье
                {(storeCase?.status || data.case.status) !== 'ready' && (
                  <Badge variant="secondary" className="text-[10px] py-0 h-4 bg-blue-50 text-blue-600 border-blue-100 animate-pulse">
                    ФОРМИРУЕТСЯ
                  </Badge>
                )}
              </div>
              
              <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200 prose prose-neutral dark:prose-invert max-w-none bg-emerald-50/30 dark:bg-emerald-900/10 p-6 rounded-2xl border border-emerald-100/50 dark:border-emerald-800/20 shadow-sm">
                {data.case.case_file ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {data.case.case_file}
                  </ReactMarkdown>
                ) : (
                  <div className="flex items-center gap-3 py-4 text-emerald-600/60 dark:text-emerald-400/60 italic">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    ИИ проводит исследование и формирует отчет...
                  </div>
                )}
              </div>
            </div>
          </div>

          {chatMessages.length === 0 && data.case.case_file && (
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
                <div className="font-semibold text-sm">
                  {m.role === 'lawyer' ? 'Вы' : 'Yuriy AI'}
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
                <div className="font-semibold text-sm">Yuriy AI</div>
                <div className="flex items-center gap-1.5 py-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" />
                  <span className="text-xs text-gray-400 ml-2 font-medium">Ищет информацию...</span>
                </div>
              </div>
            </div>
          )}

          <div className="h-32" /> {/* Увеличенный отступ снизу */}
        </div>
      </div>

      {/* Плавающее поле ввода */}
      <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-white via-white/80 to-transparent dark:from-[#171717] dark:via-[#171717]/80 pointer-events-none">
        <div className="max-w-5xl mx-auto relative pointer-events-auto">
          <div className="relative flex items-center bg-white dark:bg-[#212121] border dark:border-gray-800 shadow-2xl rounded-2xl overflow-hidden p-1.5 focus-within:ring-2 focus-within:ring-black/5 dark:focus-within:ring-white/5 transition-all">
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Спросите ассистента о деталях дела..."
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
    </div>
  );
}
