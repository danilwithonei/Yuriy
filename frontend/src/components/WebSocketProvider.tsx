'use client';

import React, { useEffect } from 'react';
import { useCaseStore } from '@/store/useCaseStore';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { addCase, updateCaseStatus } = useCaseStore();

  useEffect(() => {
    let socket: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      socket = new WebSocket(`${WS_URL}/ws/dashboard`);

      socket.onopen = () => {
        console.log('Connected to Dashboard WebSocket');
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WS Dashboard Message:', data);

        if (data.type === 'CASE_CREATED') {
          addCase(data.case);
        } else if (data.type === 'CASE_STATUS_UPDATED') {
          updateCaseStatus(data.case_id, data.status);
        }
      };

      socket.onclose = () => {
        console.log('Disconnected from Dashboard WebSocket. Reconnecting...');
        reconnectTimeout = setTimeout(connect, 3000);
      };

      socket.onerror = (error) => {
        console.error('WebSocket Error:', error);
        socket.close();
      };
    };

    connect();

    return () => {
      if (socket) socket.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [addCase, updateCaseStatus]);

  return <>{children}</>;
}
