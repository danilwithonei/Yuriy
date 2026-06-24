'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export interface ChatMessage {
  role: 'client' | 'ai_intake' | 'ai_case' | 'lawyer';
  content: string;
  timestamp?: string;
}

export function useCaseChat(caseId: number) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(`${WS_URL}/ws/cases/${caseId}/chat`);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
      console.log(`Connected to Case ${caseId} WebSocket`);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'AI_THINKING') {
        setIsThinking(true);
        setError(null);
      } else if (data.type === 'AI_RESPONSE') {
        setIsThinking(false);
        setError(null);
        setMessages((prev) => [...prev, { role: 'ai_case', content: data.content, timestamp: new Date().toISOString() }]);
      } else if (data.type === 'AI_ERROR') {
        setIsThinking(false);
        setError(data.error || 'Unknown error');
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      setIsThinking(false);
      setError('Connection lost');
      console.log(`Disconnected from Case ${caseId} WebSocket`);
    };

    return () => {
      socket.close();
    };
  }, [caseId]);

  const sendMessage = useCallback((content: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ message: content }));
      setMessages((prev) => [...prev, { role: 'lawyer', content, timestamp: new Date().toISOString() }]);
      setError(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { messages, setMessages, isConnected, isThinking, error, sendMessage, clearError };
}
