"use client";

import { Bot, FileText, Loader2, Send, UserCircle } from "lucide-react";
import React, { RefObject } from "react";

import { API_URL } from "@/lib/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CaseData } from "@/types/case";

function formatTime(ts?: string): string {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  const hh = d.getHours().toString().padStart(2, "0");
  const mm = d.getMinutes().toString().padStart(2, "0");
  if (d.toDateString() === now.toDateString()) return `${hh}:${mm}`;
  const dd = d.getDate().toString().padStart(2, "0");
  const mo = (d.getMonth() + 1).toString().padStart(2, "0");
  return `${dd}.${mo} ${hh}:${mm}`;
}

interface IntakeChatProps {
  data: CaseData;
  setData: React.Dispatch<React.SetStateAction<CaseData | null>>;
  caseId: string;
  intakeInput: string;
  setIntakeInput: React.Dispatch<React.SetStateAction<string>>;
  isIntakeSending: boolean;
  setIntakeReady: React.Dispatch<React.SetStateAction<boolean>>;
  intakeReady: boolean;
  setIntakeError: React.Dispatch<React.SetStateAction<string | null>>;
  streamingIntakeContent: string;
  setStreamingIntakeContent: React.Dispatch<React.SetStateAction<string>>;
  setIsIntakeSending: React.Dispatch<React.SetStateAction<boolean>>;
  handleIntakeConfirm: () => Promise<void>;
  scrollRef?: RefObject<HTMLDivElement | null>;
}

export default function IntakeChat({
  data,
  setData,
  caseId,
  intakeInput,
  setIntakeInput,
  isIntakeSending,
  setIntakeReady,
  intakeReady,
  setIntakeError,
  streamingIntakeContent,
  setStreamingIntakeContent,
  setIsIntakeSending,
  handleIntakeConfirm,
  scrollRef,
}: IntakeChatProps) {
  const intakeMessages = data.messages.filter(
    (m) => m.sender_role === "client" || m.sender_role === "ai_intake",
  );
  const status = data.case.status;

  const handleIntakeSend = async () => {
    if (!intakeInput.trim() || isIntakeSending) return;
    const msg = intakeInput;
    setIntakeInput("");
    setIsIntakeSending(true);
    setIntakeError(null);
    setStreamingIntakeContent("");
    const clientTs = new Date().toISOString();
    setData((prev) =>
      prev
        ? {
            ...prev,
            messages: [
              ...prev.messages,
              { sender_role: "client", content: msg, timestamp: clientTs },
            ],
          }
        : prev,
    );
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/cases/${caseId}/intake/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: msg }),
      });
      if (!response.ok) {
        let errMsg = "Ошибка отправки";
        try {
          errMsg = (await response.json()).detail;
        } catch {}
        throw new Error(errMsg);
      }
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let d;
          try {
            d = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          if (d.token) {
            fullContent += d.token;
            setStreamingIntakeContent(fullContent);
          } else if (d.response) {
            fullContent = d.response;
            setStreamingIntakeContent(fullContent);
          } else if (d.is_ready !== undefined) {
            setIntakeReady(d.is_ready);
          } else if (d.done) {
            if (d.is_ready !== undefined) setIntakeReady(d.is_ready);
          } else if (d.error) {
            throw new Error(d.error);
          }
        }
      }
      setStreamingIntakeContent("");
      setData((prev) =>
        prev
          ? {
              ...prev,
              messages: [
                ...prev.messages,
                {
                  sender_role: "ai_intake",
                  content: fullContent,
                  timestamp: new Date().toISOString(),
                },
              ],
            }
          : prev,
      );
    } catch (e: any) {
      const errMsg = e?.message || "Ошибка отправки";
      setIntakeError(errMsg);
      setStreamingIntakeContent("");
    } finally {
      setIsIntakeSending(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {status === "researching" ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Идёт исследование...
              </span>
            </div>
            <p className="text-xs text-gray-400 max-w-xs">
              ИИ изучает законы по вашему делу и формирует досье. Это может
              занять до минуты.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto scroll-smooth no-scrollbar"
          >
            <div className="max-w-5xl mx-auto py-10 px-6 space-y-6">
              {intakeMessages.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-center space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <Avatar className="h-12 w-12 border shadow-sm">
                    <AvatarFallback className="bg-amber-50 text-amber-600">
                      <FileText className="h-6 w-6" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <h3 className="font-medium text-sm">Приём данных</h3>
                    <p className="text-xs text-gray-400 max-w-sm">
                      Опишите ситуацию от лица клиента. ИИ будет задавать
                      уточняющие вопросы.
                    </p>
                  </div>
                </div>
              )}

              {intakeMessages.map((m, i) => (
                <div
                  key={i}
                  className="flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300"
                >
                  <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
                    {m.sender_role === "client" ? (
                      <AvatarFallback className="bg-gray-100 text-gray-600">
                        <UserCircle className="h-4 w-4" />
                      </AvatarFallback>
                    ) : (
                      <AvatarFallback className="bg-amber-50 text-amber-600">
                        <Bot className="h-4 w-4" />
                      </AvatarFallback>
                    )}
                  </Avatar>
                  <div className="flex-1 space-y-1.5 overflow-hidden">
                    <div className="font-semibold text-sm flex items-center gap-2">
                      {m.sender_role === "client"
                        ? "Вы (от лица клиента)"
                        : "ИИ-Приёмщик"}
                      {m.timestamp && (
                        <span className="text-[10px] text-gray-400 font-normal">
                          {formatTime(m.timestamp)}
                        </span>
                      )}
                    </div>
                    <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200 prose prose-neutral dark:prose-invert max-w-none">
                      {m.content}
                    </div>
                  </div>
                </div>
              ))}

              {isIntakeSending && (
                <div className="flex gap-4 group animate-in fade-in duration-500">
                  <Avatar className="h-8 w-8 shrink-0 border shadow-sm">
                    <AvatarFallback className="bg-amber-50 text-amber-600">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-2 overflow-hidden">
                    <div className="font-semibold text-sm">ИИ-Приёмщик</div>
                    {streamingIntakeContent ? (
                      <div className="text-[15px] leading-relaxed text-gray-800 dark:text-gray-200">
                        {streamingIntakeContent}
                        <span className="inline-block w-1.5 h-4 bg-amber-500 ml-0.5 animate-pulse" />
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 py-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-bounce [animation-delay:-0.3s]" />
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-bounce [animation-delay:-0.15s]" />
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-bounce" />
                        <span className="text-xs text-gray-400 ml-2 font-medium">
                          Анализирует...
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {intakeReady && (
                <div className="flex justify-center pt-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <Button
                    onClick={handleIntakeConfirm}
                    className="h-11 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-lg"
                  >
                    Подтвердить отправку
                  </Button>
                </div>
              )}

              <div className="h-8" />
            </div>
          </div>

          <div className="px-6 pb-4 bg-gradient-to-t from-white via-white/80 to-transparent dark:from-[#171717] dark:via-[#171717]/80">
            <div className="max-w-5xl mx-auto">
              <div className="relative flex items-center bg-white dark:bg-[#212121] border dark:border-gray-800 shadow-2xl rounded-2xl overflow-hidden p-1.5 focus-within:ring-2 focus-within:ring-amber-500/20 transition-all">
                <Input
                  value={intakeInput}
                  onChange={(e) => setIntakeInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleIntakeSend()}
                  placeholder="Опишите ситуацию от лица клиента..."
                  className="border-0 focus-visible:ring-0 bg-transparent h-12 py-3 px-4 text-[15px]"
                  disabled={isIntakeSending || intakeReady}
                />
                <Button
                  size="icon"
                  onClick={handleIntakeSend}
                  disabled={
                    isIntakeSending || intakeReady || !intakeInput.trim()
                  }
                  className="h-10 w-10 rounded-xl bg-amber-600 hover:bg-amber-700 text-white shadow-sm"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
