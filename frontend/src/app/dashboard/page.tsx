'use client';

import { MessageSquare, ShieldCheck, Zap } from 'lucide-react';


export default function Dashboard() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8 text-center bg-white dark:bg-[#171717]">
      <div className="max-w-2xl space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white">Чем я могу помочь?</h1>
          <p className="text-lg text-gray-500 dark:text-gray-400">
            Выберите юридическое дело из списка слева, чтобы начать анализ.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12">
          <div className="p-6 rounded-2xl border dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 space-y-3 text-left">
            <Zap className="h-6 w-6 text-amber-500" />
            <h3 className="font-semibold text-sm">Быстрый старт</h3>
            <p className="text-xs text-gray-500 leading-relaxed">Мгновенный доступ к деталям дела и истории переписки с клиентом.</p>
          </div>
          
          <div className="p-6 rounded-2xl border dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 space-y-3 text-left">
            <ShieldCheck className="h-6 w-6 text-emerald-500" />
            <h3 className="font-semibold text-sm">Автономный анализ</h3>
            <p className="text-xs text-gray-500 leading-relaxed">ИИ уже изучил законы и подготовил структурированное досье.</p>
          </div>
          
          <div className="p-6 rounded-2xl border dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 space-y-3 text-left">
            <MessageSquare className="h-6 w-6 text-blue-500" />
            <h3 className="font-semibold text-sm">Умный ассистент</h3>
            <p className="text-xs text-gray-500 leading-relaxed">Задавайте любые вопросы по материалам дела в режиме реального времени.</p>
          </div>
        </div>

        <div className="pt-8 text-[11px] text-gray-400 uppercase tracking-[0.2em]">
          Yuriy AI • Intellectual Legal Assistant
        </div>
      </div>
    </div>
  );
}
