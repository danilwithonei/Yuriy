'use client';

import { History } from 'lucide-react';
import { useRouter } from 'next/navigation';
import React, { use, useEffect, useRef, useState } from 'react';

import AssistantChat from '@/components/cases/AssistantChat';
import IntakeChat from '@/components/cases/IntakeChat';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useCaseChat } from '@/hooks/useCaseChat';
import api from '@/lib/api';
import { useCaseStore } from '@/store/useCaseStore';
import type { CaseData } from '@/types/case';

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
  const { messages: chatMessages, setMessages: setChatMessages, sendMessage, isConnected, isThinking, streamingContent, error, caseDeleted, clearError } = useCaseChat(caseId);
  const router = useRouter();
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

  const handleIntakeConfirm = async () => {
    try {
      await api.post(`/cases/${id}/intake/confirm`);
      setData(prev => prev ? { ...prev, case: { ...prev.case, status: 'researching' } } : prev);
      useCaseStore.getState().updateCaseStatus(caseId, 'researching');
    } catch (e: any) {
      setIntakeError(e?.response?.data?.detail || 'Ошибка подтверждения');
    }
  };

  if (caseDeleted) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center space-y-4">
        <div className="text-4xl font-bold text-gray-300">404</div>
        <p className="text-sm text-gray-500">Дело удалено</p>
        <button
          onClick={() => router.push('/')}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl bg-black dark:bg-white text-white dark:text-black hover:opacity-90 transition-opacity"
        >
          Вернуться к списку
        </button>
      </div>
    </div>
  );

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
  const intakeMessages = data.messages.filter(m => m.sender_role === 'client' || m.sender_role === 'ai_intake');

  return (
    <div className="flex flex-col flex-1 h-full overflow-hidden bg-white dark:bg-[#171717]">
      {/* Header */}
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
                  <div className="flex-1 overflow-y-auto p-8 space-y-8">
                    {intakeMessages.map((m, i) => (
                      <div key={i} className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-[10px] uppercase font-bold text-gray-400">
                          {m.sender_role === 'client' ? 'Клиент' : 'ИИ-Помощник'}
                        </div>
                        <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300 bg-gray-50/50 dark:bg-gray-900/50 p-4 rounded-xl border dark:border-gray-800 shadow-sm">
                          {m.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </SheetContent>
            </Sheet>
          )}
        </div>
      </div>

      {/* Error Banner */}
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

      {/* Intake Mode */}
      {isIntakeMode && (
        <IntakeChat
          data={data}
          setData={setData}
          caseId={caseId}
          intakeInput={intakeInput}
          setIntakeInput={setIntakeInput}
          isIntakeSending={isIntakeSending}
          setIntakeReady={setIntakeReady}
          intakeReady={intakeReady}
          setIntakeError={setIntakeError}
          streamingIntakeContent={streamingIntakeContent}
          setStreamingIntakeContent={setStreamingIntakeContent}
          setIsIntakeSending={setIsIntakeSending}
          handleIntakeConfirm={handleIntakeConfirm}
          scrollRef={scrollRef}
        />
      )}

      {/* Assistant Mode */}
      {isAssistantMode && (
        <AssistantChat
          data={data}
          isDirect={isDirect}
          chatMessages={chatMessages}
          isConnected={isConnected}
          isThinking={isThinking}
          streamingContent={streamingContent}
          error={error}
          clearError={clearError}
          chatInput={chatInput}
          setChatInput={setChatInput}
          handleSend={handleSend}
          scrollRef={scrollRef}
        />
      )}
    </div>
  );
}
