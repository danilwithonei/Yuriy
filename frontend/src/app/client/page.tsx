'use client';

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, User, Bot, AlertCircle } from 'lucide-react';
import Link from 'next/link';

interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
}

export default function ClientChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'ai', content: 'Здравствуйте! Я ИИ-ассистент юриста. Опишите, пожалуйста, вашу юридическую проблему, и я помогу вам составить заявку.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [caseId, setCaseId] = useState<number | null>(null);
  const [status, setStatus] = useState<string>('open');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Generate a random user ID only on the client side to avoid hydration mismatch
  const [userId, setUserId] = useState<number | null>(null);

  useEffect(() => {
    setUserId(Math.floor(Math.random() * 10000));
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading || status === 'ready') return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const payload: any = {
        user_id: userId,
        message: userMsg
      };
      
      if (caseId) {
        payload.case_id = caseId;
      }

      const res = await axios.post(`${apiUrl}/chat`, payload);
      
      setCaseId(res.data.case_id);
      setStatus(res.data.status);
      setMessages(prev => [...prev, { role: 'ai', content: res.data.response }]);
      
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'ai', content: 'Извините, произошла ошибка при отправке сообщения. Пожалуйста, убедитесь, что бэкенд запущен.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-black max-w-3xl mx-auto border-x shadow-xl">
      {/* Header */}
      <div className="bg-indigo-600 text-white p-4 flex items-center justify-between shadow-md z-10">
        <div>
          <h1 className="text-xl font-bold">Юридическая консультация (Тест)</h1>
          <p className="text-indigo-200 text-sm">Ваш временный ID: {userId} {caseId && `| Дело №${caseId}`}</p>
        </div>
        <Link href="/dashboard" className="text-sm bg-indigo-500 hover:bg-indigo-400 px-3 py-1 rounded transition-colors">
          Панель юриста
        </Link>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-100">
        {status === 'ready' && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4 flex items-center gap-2">
            <AlertCircle size={20} />
            <span>Ваша заявка успешно сформирована и передана юристу! Ожидайте ответа.</span>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.role === 'user' ? 'bg-blue-500 text-white' : 'bg-indigo-600 text-white'}`}>
                {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className={`p-4 rounded-2xl shadow-sm ${
                m.role === 'user' 
                  ? 'bg-blue-500 text-white rounded-tr-none' 
                  : 'bg-white text-gray-800 border border-gray-200 rounded-tl-none'
              }`}>
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="flex gap-3 max-w-[85%]">
              <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0">
                <Bot size={16} />
              </div>
              <div className="p-4 rounded-2xl shadow-sm bg-white text-gray-800 border border-gray-200 rounded-tl-none flex items-center gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t">
        <div className="flex gap-2 max-w-full relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={status === 'ready' || loading}
            placeholder={status === 'ready' ? "Заявка отправлена" : "Опишите вашу проблему..."}
            className="flex-1 resize-none bg-gray-50 border border-gray-300 rounded-xl p-3 pr-12 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-black disabled:bg-gray-200 disabled:cursor-not-allowed"
            rows={1}
            style={{ minHeight: '50px', maxHeight: '150px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || status === 'ready' || loading}
            className="absolute right-2 bottom-2 p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2">
          Нажмите Enter для отправки, Shift+Enter для переноса строки
        </p>
      </div>
    </div>
  );
}
