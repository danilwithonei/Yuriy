'use client';

import { useCallback,useEffect, useRef, useState } from 'react';

import { WS_BASE_URL } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';

export interface ChatMessage {
  role: 'client' | 'ai_intake' | 'ai_case' | 'lawyer';
  content: string;
  timestamp?: string;
}

export function useCaseChat(caseId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [caseDeleted, setCaseDeleted] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const streamBufRef = useRef<string>('');

  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (!token) return;

    const socket = new WebSocket(`${WS_BASE_URL}/ws/cases/${caseId}/chat?token=${token}`);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
      setCaseDeleted(false);
      console.log(`Connected to Case ${caseId} WebSocket`);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'AI_THINKING') {
        setIsThinking(true);
        streamBufRef.current = '';
        setStreamingContent('');
        setError(null);
      } else if (data.type === 'AI_TOKEN') {
        streamBufRef.current += data.token;
        setStreamingContent(streamBufRef.current);
        setError(null);
      } else if (data.type === 'AI_RESPONSE') {
        setIsThinking(false);
        streamBufRef.current = '';
        setStreamingContent('');
        setMessages((prev) => [...prev, { role: 'ai_case', content: data.content, timestamp: new Date().toISOString() }]);
        setError(null);
      } else if (data.type === 'AI_ERROR') {
        setIsThinking(false);
        streamBufRef.current = '';
        setStreamingContent('');
        setError(data.error || 'Unknown error');
      }
    };

    socket.onclose = (event) => {
      setIsConnected(false);
      setIsThinking(false);
      streamBufRef.current = '';
      setStreamingContent('');
      if (event.code === 4004) {
        setCaseDeleted(true);
        setError('Дело удалено');
      } else {
        setError('Connection lost');
      }
      console.log(`Disconnected from Case ${caseId} WebSocket, code=${event.code}`);
    };

    return () => {
      setCaseDeleted(false);
      socket.close();
    };
  }, [caseId, token]);

  const sendMessage = useCallback((content: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ message: content }));
      setMessages((prev) => [...prev, { role: 'lawyer', content, timestamp: new Date().toISOString() }]);
      setError(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { messages, setMessages, isConnected, isThinking, streamingContent, error, caseDeleted, sendMessage, clearError };
}
