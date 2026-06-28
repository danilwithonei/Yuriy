"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppSidebar } from "@/components/AppSidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { WebSocketProvider } from "@/components/WebSocketProvider";
import { useAuthStore } from "@/store/useAuthStore";

const PUBLIC_ROUTES = ["/login", "/register"];

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { checkAuth, isChecking, isReady, lawyer } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (!isReady) return;
    const isPublic = PUBLIC_ROUTES.includes(pathname);
    if (!lawyer && !isPublic) {
      router.push("/login");
    } else if (lawyer && isPublic) {
      router.push("/dashboard");
    }
  }, [isReady, lawyer, pathname, router]);

  if (isChecking) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#f9f9f9] dark:bg-[#171717]">
        <div className="animate-pulse text-sm text-gray-400">Загрузка...</div>
      </div>
    );
  }

  const isPublic = PUBLIC_ROUTES.includes(pathname);

  if (isPublic) {
    return <>{children}</>;
  }

  if (!lawyer) {
    return null;
  }

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
