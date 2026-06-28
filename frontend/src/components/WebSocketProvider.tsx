"use client";

import React, { useEffect } from "react";

import { WS_BASE_URL } from "@/lib/api";
import { useAuthStore } from "@/store/useAuthStore";
import { useCaseStore } from "@/store/useCaseStore";

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const {
    addCase,
    updateCaseStatus,
    updateCaseMeta,
    removeCase,
    setCasePinned,
  } = useCaseStore();
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (!token) return;

    let socket: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      socket = new WebSocket(`${WS_BASE_URL}/ws/dashboard?token=${token}`);

      socket.onopen = () => {
        console.log("Connected to Dashboard WebSocket");
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "CASE_CREATED") {
          addCase(data.case);
        } else if (data.type === "CASE_STATUS_UPDATED") {
          updateCaseStatus(data.case_id, data.status);
          const meta: Record<string, string> = {};
          if (data.title) meta.title = data.title;
          if (data.summary) meta.summary = data.summary;
          if (Object.keys(meta).length > 0) {
            updateCaseMeta(data.case_id, meta);
          }
        } else if (data.type === "CASE_DELETED") {
          removeCase(data.case_id);
        } else if (data.type === "CASE_PINNED") {
          setCasePinned(data.case_id, data.pinned);
        }
      };

      socket.onclose = () => {
        console.log("Disconnected from Dashboard WebSocket. Reconnecting...");
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
  }, [
    token,
    addCase,
    updateCaseStatus,
    updateCaseMeta,
    removeCase,
    setCasePinned,
  ]);

  return <>{children}</>;
}
