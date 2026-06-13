'use client';

import React, { useEffect, useState, use, useRef } from 'react';
import axios from 'axios';
import { Send, User, Bot, History, FileText, MessageSquare, Info, ChevronRight, UserCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useCaseChat } from '@/hooks/useCaseChat';
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
  const { messages: chatMessages, setMessages: setChatMessages, sendMessage, isConnected } = useCaseChat(caseId);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
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
    if (scrollRef.current) {
      scrollRef.current.scrollTo(0, scrollRef.current.scrollHeight);
    }
  }, [chatMessages]);

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
              data.case.status === 'ready' ? 'bg-emerald-500' : 
              data.case.status === 'researching' ? 'bg-blue-500 animate-pulse' : 'bg-amber-500'
            }`} 
          />
          <span className="text-[10px] text-gray-400 uppercase font-medium tracking-wider">
            {data.case.status === 'ready' ? 'Исследование завершено' : 'В процессе анализа'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Sheet>
            <SheetTrigger asChild>
              <button className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors">
                <FileText className="h-4 w-4" />
                <span>Досье</span>
              </button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
              <SheetHeader className="mb-6">
                <SheetTitle>Сформированное досье</SheetTitle>
                <SheetDescription>Результаты автономного исследования ИИ по делу №{id}</SheetDescription>
              </SheetHeader>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                {data.case.case_file ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.case.case_file}</ReactMarkdown>
                ) : (
                  <div className="text-muted-foreground italic py-10 text-center">
                    Досье еще формируется. Пожалуйста, подождите...
                  </div>
                )}
              </div>
            </SheetContent>
          </Sheet>

          <Sheet>
            <SheetTrigger asChild>
              <button className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors">
                <History className="h-4 w-4" />
                <span>История</span>
              </button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
              <SheetHeader className="mb-6">
                <SheetTitle>История приема</SheetTitle>
                <SheetDescription>Первичный диалог клиента с ИИ-приемщиком</SheetDescription>
              </SheetHeader>
              <div className="space-y-6">
                {data.messages.filter(m => m.sender_role === 'client' || m.sender_role === 'ai_intake').map((m, i) => (
                  <div key={i} className="flex flex-col gap-1">
                    <div className="flex items-center gap-2 text-[10px] uppercase font-bold text-gray-400">
                      {m.sender_role === 'client' ? 'Клиент' : 'ИИ-Приемщик'}
                    </div>
                    <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg border dark:border-gray-800">
                      {m.content}
                    </p>
                  </div>
                ))}
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
        <div className="max-w-3xl mx-auto py-10 px-6 space-y-10">
          {chatMessages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
              <Avatar className="h-12 w-12 border">
                <AvatarFallback className="bg-emerald-50 text-emerald-600">AI</AvatarFallback>
              </Avatar>
              <div className="space-y-2">
                <h3 className="font-medium">Чем я могу помочь?</h3>
                <p className="text-sm text-gray-400 max-w-sm">
                  Я проанализировал материалы дела №{id}. Вы можете попросить меня сделать выводы, найти противоречия или подготовить вопросы для клиента.
                </p>
              </div>
            </div>
          )}

          {chatMessages.map((m, i) => (
            <div key={i} className="flex gap-4 group">
              <Avatar className="h-8 w-8 shrink-0 border">
                {m.role === 'lawyer' ? (
                  <AvatarFallback className="bg-gray-100 text-gray-600">U</AvatarFallback>
                ) : (
                  <AvatarFallback className="bg-emerald-50 text-emerald-600">
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
          <div className="h-24" /> {/* Отступ снизу для плавающего ввода */}
        </div>
      </div>

      {/* Плавающее поле ввода */}
      <div className="absolute bottom-0 left-0 right-0 p-6 bg-transparent pointer-events-none">
        <div className="max-w-3xl mx-auto relative pointer-events-auto">
          <div className="relative flex items-center bg-white dark:bg-[#212121] border dark:border-gray-800 shadow-lg rounded-2xl overflow-hidden p-1.5 focus-within:ring-1 focus-within:ring-gray-300 transition-all">
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
              className="h-10 w-10 rounded-xl bg-black dark:bg-white text-white dark:text-black hover:opacity-80 transition-opacity"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-[10px] text-center mt-2 text-gray-400">
            Yuriy AI может ошибаться. Проверяйте важную информацию.
          </div>
        </div>
      </div>
    </div>
  );
}
