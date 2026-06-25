'use client';

import React, { useEffect } from 'react';
import { useCaseStore } from '@/store/useCaseStore';
import { useAuthStore } from '@/store/useAuthStore';
import { WS_BASE_URL } from '@/lib/api';

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { addCase, updateCaseStatus, updateCaseMeta } = useCaseStore();
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (!token) return;

    let socket: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      socket = new WebSocket(`${WS_BASE_URL}/ws/dashboard?token=${token}`);

      socket.onopen = () => {
        console.log('Connected to Dashboard WebSocket');
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'CASE_CREATED') {
          addCase(data.case);
        } else if (data.type === 'CASE_STATUS_UPDATED') {
          updateCaseStatus(data.case_id, data.status);
          const meta: Record<string, string> = {};
          if (data.title) meta.title = data.title;
          if (data.summary) meta.summary = data.summary;
          if (Object.keys(meta).length > 0) {
            updateCaseMeta(data.case_id, meta);
          }
        }
      };

      socket.onclose = () => {
        console.log('Disconnected from Dashboard WebSocket. Reconnecting...');
        reconnectTimeout = setTimeout(connect, 3000);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      if (socket) socket.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [token, addCase, updateCaseStatus, updateCaseMeta]);

  return <>{children}</>;
}
