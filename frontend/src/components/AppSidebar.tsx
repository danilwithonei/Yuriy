'use client';

import * as React from 'react';
import { useCaseStore } from '@/store/useCaseStore';
import { useRouter, useParams } from 'next/navigation';
import { FileText, Plus, SquarePen } from 'lucide-react';

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';

export function AppSidebar() {
  const { cases, fetchCases, loading } = useCaseStore();
  const router = useRouter();
  const params = useParams();
  const activeCaseId = params.id ? parseInt(params.id as string) : null;

  React.useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const sortedCases = [...cases].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'bg-emerald-500';
      case 'researching': return 'bg-blue-500 animate-pulse';
      case 'open': return 'bg-amber-500';
      default: return 'bg-gray-300';
    }
  };

  return (
    <Sidebar className="border-r-0 bg-[#f9f9f9] dark:bg-[#171717]">
      <SidebarHeader className="p-3">
        <div className="flex items-center justify-between px-2 py-2">
          <div className="font-semibold text-sm tracking-wide">Yuriy AI</div>
          <button 
            onClick={() => router.push('/dashboard')}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-md transition-colors"
            title="Новый чат"
          >
            <SquarePen className="h-4 w-4 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <div className="px-3 pb-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
            История дел
          </div>
          <SidebarGroupContent>
            <SidebarMenu>
              {loading && cases.length === 0 ? (
                <div className="px-4 py-2 text-xs text-gray-400">Загрузка...</div>
              ) : (
                sortedCases.map((c) => (
                  <SidebarMenuItem key={c.id}>
                    <SidebarMenuButton
                      isActive={activeCaseId === c.id}
                      onClick={() => router.push(`/cases/${c.id}`)}
                      className={`py-2 px-3 h-auto mx-2 rounded-lg transition-colors ${
                        activeCaseId === c.id 
                          ? 'bg-white dark:bg-[#212121] shadow-sm font-medium text-black dark:text-white' 
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-200/50 dark:hover:bg-gray-800/50 hover:text-black dark:hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-3 w-full">
                        <FileText className="h-4 w-4 opacity-50 shrink-0" />
                        <div className="flex-1 truncate text-sm">
                          Дело №{c.id}
                        </div>
                        <div 
                          className={`h-2 w-2 rounded-full shrink-0 ${getStatusColor(c.status)}`} 
                          title={`Статус: ${c.status}`}
                        />
                      </div>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))
              )}
              {!loading && cases.length === 0 && (
                <div className="px-4 py-2 text-xs text-gray-400">Нет активных дел</div>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
