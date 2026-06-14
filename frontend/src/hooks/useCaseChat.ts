'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export interface ChatMessage {
  role: 'client' | 'ai_intake' | 'ai_case' | 'lawyer';
  content: string;
}

export function useCaseChat(caseId: number) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(`${WS_URL}/ws/cases/${caseId}/chat`);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log(`Connected to Case ${caseId} WebSocket`);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'AI_THINKING') {
        setIsThinking(true);
      } else if (data.type === 'AI_RESPONSE') {
        setIsThinking(false);
        setMessages((prev) => [...prev, { role: 'ai_case', content: data.content }]);
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      setIsThinking(false);
      console.log(`Disconnected from Case ${caseId} WebSocket`);
    };

    return () => {
      socket.close();
    };
  }, [caseId]);

  const sendMessage = useCallback((content: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ message: content }));
      setMessages((prev) => [...prev, { role: 'lawyer', content }]);
    }
  }, []);

  return { messages, setMessages, isConnected, isThinking, sendMessage };
}
