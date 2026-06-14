'use client';

import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/AppSidebar';
import { WebSocketProvider } from '@/components/WebSocketProvider';

export function LayoutShell({ children }: { children: React.ReactNode }) {
  return (
    <WebSocketProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="bg-white dark:bg-[#171717]">
          <header className="flex h-14 shrink-0 items-center gap-2 px-4 sticky top-0 bg-white/80 dark:bg-[#171717]/80 backdrop-blur-md z-20">
            <SidebarTrigger className="-ml-1" />
          </header>
          <main className="flex flex-1 flex-col overflow-hidden relative">
            {children}
          </main>
        </SidebarInset>
      </SidebarProvider>
    </WebSocketProvider>
  );
}
