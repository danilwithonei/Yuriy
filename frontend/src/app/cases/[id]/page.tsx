'use client';

import React, { useEffect, useState, use } from 'react';
import axios from 'axios';
import { Send, User, Bot, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface Message {
  sender_role: string;
  content: string;
  timestamp: string;
}

interface CaseData {
  case: {
    id: number;
    status: string;
    case_file: string | null;
  };
  messages: Message[];
}

export default function CaseDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<CaseData | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<any[]>([]);

  useEffect(() => {
    axios.get(`http://localhost:8000/cases/${id}`)
      .then(res => {
        setData(res.data);
        const existingAssists = res.data.messages
          .filter((m: any) => m.sender_role === 'lawyer' || m.sender_role === 'ai_case')
          .map((m: any) => ({ role: m.sender_role, content: m.content }));
        setChatMessages(existingAssists);
      })
      .catch(err => console.error(err));
  }, [id]);

  const handleSend = async () => {
    if (!chatInput.trim()) return;
    
    const newMsg = { role: 'lawyer', content: chatInput };
    setChatMessages(prev => [...prev, newMsg]);
    setChatInput('');
    
    try {
      const res = await axios.post(`http://localhost:8000/cases/${id}/assist`, { message: chatInput });
      setChatMessages(prev => [...prev, { role: 'ai_case', content: res.data.response }]);
    } catch (err) {
      console.error(err);
      setChatMessages(prev => [...prev, { role: 'ai_case', content: "Произошла ошибка при обращении к ассистенту." }]);
    }
  };

  if (!data) return <div className="p-8">Загрузка данных дела...</div>;

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-black">
      {/* Header */}
      <div className="bg-white border-b p-4 flex items-center gap-4">
        <Link href="/dashboard" className="p-2 hover:bg-gray-100 rounded-full transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-xl font-bold italic">Дело №{id}</h1>
        <span className="ml-auto px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
          {data.case.status.toUpperCase()}
        </span>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Column: Intake History & Case File */}
        <div className="w-1/2 overflow-y-auto p-6 border-r bg-white">
          <section className="mb-8">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2 border-b pb-2">
              <User size={18} /> История приема
            </h2>
            <div className="space-y-4">
              {data.messages.filter(m => m.sender_role === 'client' || m.sender_role === 'ai_intake').map((m, i) => (
                <div key={i} className={`p-3 rounded-lg ${m.sender_role === 'client' ? 'bg-blue-50 border-l-4 border-blue-400' : 'bg-gray-50 border-l-4 border-gray-400'}`}>
                  <p className="text-xs font-bold text-gray-500 uppercase mb-1">{m.sender_role === 'client' ? 'Клиент' : 'ИИ-Приемщик'}</p>
                  <p className="text-sm">{m.content}</p>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2 border-b pb-2">
              <Bot size={18} /> Досье дела (Сгенерировано ИИ)
            </h2>
            <div className="prose prose-sm max-w-none bg-indigo-50 p-6 rounded-xl border border-indigo-100 whitespace-pre-wrap font-sans leading-relaxed text-black">
              {data.case.case_file || "Досье еще не сформировано. Ожидайте подтверждения от клиента."}
            </div>
          </section>
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div className="w-1/2 flex flex-col bg-white">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <div className="bg-indigo-600 text-white p-4 rounded-2xl rounded-tl-none max-w-[85%] shadow-lg">
              <p className="text-xs font-bold opacity-75 mb-1 uppercase tracking-wider">ИИ-Ассистент</p>
              <p className="text-sm leading-relaxed">Приветствую! Я готов помочь вам проанализировать это дело. Вы можете спрашивать меня о деталях переписки, результатах поиска или попросить сделать выводы.</p>
            </div>
            
            {chatMessages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'lawyer' ? 'justify-end' : 'justify-start'}`}>
                <div className={`p-4 rounded-2xl max-w-[85%] shadow-md ${
                  m.role === 'lawyer' 
                    ? 'bg-gray-100 text-gray-800 rounded-tr-none' 
                    : 'bg-indigo-600 text-white rounded-tl-none'
                }`}>
                  <p className="text-xs font-bold opacity-75 mb-1 uppercase tracking-wider">{m.role === 'lawyer' ? 'Вы' : 'ИИ-Ассистент'}</p>
                  <p className="text-sm leading-relaxed">{m.content}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 border-t bg-gray-50">
            <div className="flex gap-2 bg-white p-2 rounded-xl border shadow-inner">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Спросите ассистента о деле..."
                className="flex-1 bg-transparent border-none focus:ring-0 px-2 text-sm text-black"
              />
              <button
                onClick={handleSend}
                className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
