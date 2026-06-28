'use client';

import { Bot, FileText, Loader2, Send } from 'lucide-react';
import React, { RefObject } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { ChatMessage } from '@/hooks/useCaseChat';
import type { CaseData } from '@/types/case';

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

interface AssistantChatProps {
  data: CaseData;
  isDirect: boolean;
  chatMessages: ChatMessage[];
  isConnected: boolean;
  isThinking: boolean;
  streamingContent: string;
  error: string | null;
  clearError: () => void;
  chatInput: string;
  setChatInput: React.Dispatch<React.SetStateAction<string>>;
  handleSend: () => void;
  scrollRef?: RefObject<HTMLDivElement | null>;
}

export default function AssistantChat({
  data, isDirect, chatMessages, isConnected, isThinking, streamingContent, error, clearError,
  chatInput, setChatInput, handleSend, scrollRef,
}: AssistantChatProps) {
  return (
    <>
      {error && (
        <div className="mx-6 mt-3 flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/30 text-sm text-red-700 dark:text-red-400 animate-in fade-in slide-in-from-top-2 duration-300">
          <span>{error}</span>
          <button onClick={clearError} className="p-1 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-md transition-colors">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
      )}

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
  );
}
