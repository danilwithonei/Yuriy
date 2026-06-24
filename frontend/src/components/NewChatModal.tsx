'use client';

import * as React from 'react';
import { Dialog as DialogPrimitive } from '@base-ui/react/dialog';
import { useRouter } from 'next/navigation';
import { FileText, Bot, XIcon, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useCaseStore } from '@/store/useCaseStore';

interface NewChatModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NewChatModal({ open, onOpenChange }: NewChatModalProps) {
  const router = useRouter();
  const { createCase } = useCaseStore();
  const [creating, setCreating] = React.useState<string | null>(null);

  const handleCreate = async (type: 'intake' | 'direct') => {
    setCreating(type);
    try {
      const caseId = await createCase(type);
      onOpenChange(false);
      router.push(`/cases/${caseId}`);
    } catch (err) {
      console.error('Failed to create case:', err);
    } finally {
      setCreating(null);
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Backdrop
          className="fixed inset-0 z-50 bg-black/10 transition-opacity duration-150 data-ending-style:opacity-0 data-starting-style:opacity-0 supports-backdrop-filter:backdrop-blur-xs"
        />
        <DialogPrimitive.Popup
          className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-[520px] max-w-[90vw] bg-white dark:bg-[#171717] rounded-2xl shadow-2xl border dark:border-gray-800 p-6 transition-all duration-200 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0"
        >
          <div className="flex items-center justify-between mb-6">
            <DialogPrimitive.Title className="font-semibold text-sm tracking-wide">
              Новый чат
            </DialogPrimitive.Title>
            <DialogPrimitive.Close
              render={
                <Button variant="ghost" size="icon-sm" />
              }
            >
              <XIcon className="h-4 w-4" />
            </DialogPrimitive.Close>
          </div>

          <DialogPrimitive.Description className="text-xs text-gray-500 dark:text-gray-400 mb-5">
            Выберите режим работы
          </DialogPrimitive.Description>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => handleCreate('intake')}
              disabled={creating !== null}
              className={cn(
                "flex flex-col items-center justify-center gap-3 p-8 rounded-2xl border-2 border-dashed dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50 transition-all",
                "hover:border-amber-400 dark:hover:border-amber-500 hover:bg-amber-50/50 dark:hover:bg-amber-900/10",
                "disabled:opacity-50 disabled:pointer-events-none",
                creating === 'intake' && "animate-pulse"
              )}
            >
              {creating === 'intake' ? (
                <Loader2 className="h-8 w-8 text-amber-500 animate-spin" />
              ) : (
                <FileText className="h-8 w-8 text-amber-500" />
              )}
              <div className="text-center">
                <div className="font-medium text-sm mb-1">Приём (Intake)</div>
                <div className="text-[11px] text-gray-400 leading-relaxed">
                  Пройти опрос клиента<br />через ИИ-приёмщика
                </div>
              </div>
            </button>

            <button
              onClick={() => handleCreate('direct')}
              disabled={creating !== null}
              className={cn(
                "flex flex-col items-center justify-center gap-3 p-8 rounded-2xl border-2 border-dashed dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50 transition-all",
                "hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-900/10",
                "disabled:opacity-50 disabled:pointer-events-none",
                creating === 'direct' && "animate-pulse"
              )}
            >
              {creating === 'direct' ? (
                <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
              ) : (
                <Bot className="h-8 w-8 text-blue-500" />
              )}
              <div className="text-center">
                <div className="font-medium text-sm mb-1">Ассистент</div>
                <div className="text-[11px] text-gray-400 leading-relaxed">
                  Прямой чат с ИИ<br />+ веб-поиск
                </div>
              </div>
            </button>
          </div>
        </DialogPrimitive.Popup>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
