'use client';

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { Briefcase, Clock, CheckCircle, AlertCircle } from 'lucide-react';

interface Case {
  id: number;
  client_id: number;
  status: string;
  created_at: string;
}

export default function Dashboard() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    axios.get(`${apiUrl}/cases`)
      .then(res => {
        setCases(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready': return <CheckCircle className="text-green-500" />;
      case 'researching': return <Clock className="text-blue-500" />;
      case 'open': return <AlertCircle className="text-yellow-500" />;
      default: return <Briefcase className="text-gray-500" />;
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Панель управления юриста</h1>
      
      {loading ? (
        <p>Загрузка заявок...</p>
      ) : (
        <div className="grid gap-4">
          {cases.map((c) => (
            <Link key={c.id} href={`/cases/${c.id}`}>
              <div className="border p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow flex items-center justify-between bg-white">
                <div className="flex items-center gap-4">
                  {getStatusIcon(c.status)}
                  <div>
                    <h2 className="font-semibold text-lg text-black">Дело №{c.id}</h2>
                    <p className="text-sm text-gray-500">Клиент ID: {c.client_id} • {new Date(c.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    c.status === 'ready' ? 'bg-green-100 text-green-800' : 
                    c.status === 'open' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100'
                  }`}>
                    {c.status.toUpperCase()}
                  </span>
                </div>
              </div>
            </Link>
          ))}
          {cases.length === 0 && <p className="text-gray-500 text-center py-10">Новых заявок пока нет.</p>}
        </div>
      )}
    </div>
  );
}
