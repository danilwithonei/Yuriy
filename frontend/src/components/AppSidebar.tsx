"use client";

import {
  Bot,
  FileText,
  LogOut,
  MoreHorizontal,
  Pin,
  SquarePen,
  Trash2,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import ReactDOM from "react-dom";

import { NewChatModal } from "@/components/NewChatModal";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useAuthStore } from "@/store/useAuthStore";
import { useCaseStore } from "@/store/useCaseStore";

interface CaseMenuProps {
  caseId: string;
  pinned: boolean;
  onClose: () => void;
  triggerRect: DOMRect;
}

function CaseMenu({ caseId, pinned, onClose, triggerRect }: CaseMenuProps) {
  const { togglePin, deleteCase } = useCaseStore();
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const handlePin = async () => {
    await togglePin(caseId);
    onClose();
  };

  const handleDelete = () => {
    deleteCase(caseId);
    onClose();
  };

  return (
    <div
      ref={menuRef}
      style={{
        position: "fixed",
        top: triggerRect.bottom + 4,
        left: triggerRect.right,
        transform: "translateX(-100%)",
      }}
      className="z-50 w-44 rounded-lg border bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-[#212121]"
    >
      <span
        onClick={handlePin}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer"
      >
        <Pin className="h-4 w-4" />
        {pinned ? "Открепить" : "Закрепить"}
      </span>
      <span
        onClick={handleDelete}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950 cursor-pointer"
      >
        <Trash2 className="h-4 w-4" />
        Удалить
      </span>
    </div>
  );
}

export function AppSidebar() {
  const { cases, fetchCases, loading } = useCaseStore();
  const { lawyer, logout } = useAuthStore();
  const router = useRouter();
  const params = useParams();
  const activeCaseId = params.id ? (params.id as string) : null;
  const [newChatOpen, setNewChatOpen] = React.useState(false);
  const [openMenuCaseId, setOpenMenuCaseId] = React.useState<string | null>(
    null,
  );
  const [menuTriggerRect, setMenuTriggerRect] = React.useState<DOMRect | null>(
    null,
  );

  const closeMenu = React.useCallback(() => {
    setOpenMenuCaseId(null);
    setMenuTriggerRect(null);
  }, []);

  React.useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const sortedCases = [...cases].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const getCaseIcon = (case_type: string) => {
    return case_type === "direct" ? Bot : FileText;
  };

  const getCaseAccent = (case_type: string) => {
    return case_type === "direct" ? "text-blue-500" : "text-amber-500";
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ready":
        return "bg-emerald-500";
      case "researching":
        return "bg-blue-500 animate-pulse";
      case "open":
        return "bg-amber-500";
      default:
        return "bg-gray-300";
    }
  };

  return (
    <>
      <NewChatModal open={newChatOpen} onOpenChange={setNewChatOpen} />
      <Sidebar className="border-r-0 bg-[#f9f9f9] dark:bg-[#171717]">
        <SidebarHeader className="p-3">
          <div className="flex items-center justify-between px-2 py-2">
            <div className="font-semibold text-sm tracking-wide">Yuriy AI</div>
            <button
              onClick={() => setNewChatOpen(true)}
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
                  <div className="px-4 py-2 text-xs text-gray-400">
                    Загрузка...
                  </div>
                ) : (
                  sortedCases.map((c) => {
                    const CaseIcon = getCaseIcon(c.case_type);
                    const accent = getCaseAccent(c.case_type);
                    const isActive = activeCaseId === c.id;
                    return (
                      <SidebarMenuItem key={c.id} className="relative">
                        <div className="flex items-center mx-2">
                          <SidebarMenuButton
                            isActive={isActive}
                            onClick={() => router.push(`/cases/${c.id}`)}
                            className={`py-2 px-3 h-auto rounded-lg transition-colors flex-1 ${
                              isActive
                                ? "bg-white dark:bg-[#212121] shadow-sm font-medium text-black dark:text-white"
                                : "text-gray-600 dark:text-gray-400 hover:bg-gray-200/50 dark:hover:bg-gray-800/50 hover:text-black dark:hover:text-white"
                            }`}
                          >
                            <div className="flex items-center gap-3 w-full">
                              <div className="relative">
                                <CaseIcon
                                  className={`h-4 w-4 shrink-0 ${accent}`}
                                />
                                {c.pinned && (
                                  <Pin className="absolute -top-1.5 -right-1.5 h-2.5 w-2.5 text-gray-400" />
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="truncate text-sm">
                                  {c.title ||
                                    (c.case_type === "direct"
                                      ? "Чат"
                                      : "Дело") +
                                      " №" +
                                      c.id.slice(0, 8)}
                                </div>
                                {c.summary && (
                                  <div className="truncate text-[11px] text-gray-400 mt-0.5">
                                    {c.summary}
                                  </div>
                                )}
                              </div>
                              <div
                                className={`h-2 w-2 rounded-full shrink-0 ${getStatusColor(c.status)}`}
                                title={`Статус: ${c.status}`}
                              />
                              <span
                                onClick={(e) => {
                                  e.stopPropagation();
                                  e.preventDefault();
                                  const rect =
                                    e.currentTarget.getBoundingClientRect();
                                  if (openMenuCaseId === c.id) {
                                    setOpenMenuCaseId(null);
                                    setMenuTriggerRect(null);
                                  } else {
                                    setOpenMenuCaseId(c.id);
                                    setMenuTriggerRect(rect);
                                  }
                                }}
                                className="flex items-center justify-center p-1.5 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-md transition-colors cursor-pointer shrink-0"
                                title="Действия"
                              >
                                <MoreHorizontal className="h-4 w-4 text-gray-400" />
                              </span>
                            </div>
                          </SidebarMenuButton>
                        </div>
                      </SidebarMenuItem>
                    );
                  })
                )}
                {!loading && cases.length === 0 && (
                  <div className="px-4 py-2 text-xs text-gray-400">
                    Нет активных дел
                  </div>
                )}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="p-3 border-t dark:border-gray-800">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase shrink-0">
              {lawyer?.name?.charAt(0) || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{lawyer?.name}</div>
              <div className="text-[11px] text-gray-400 truncate">
                {lawyer?.email}
              </div>
            </div>
            <button
              onClick={logout}
              className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-md transition-colors shrink-0"
              title="Выйти"
            >
              <LogOut className="h-4 w-4 text-gray-500" />
            </button>
          </div>
        </SidebarFooter>
      </Sidebar>
      {(() => {
        const openCase = openMenuCaseId
          ? cases.find((c) => c.id === openMenuCaseId)
          : null;
        if (openCase && menuTriggerRect) {
          return ReactDOM.createPortal(
            <CaseMenu
              caseId={openCase.id}
              pinned={!!openCase.pinned}
              onClose={closeMenu}
              triggerRect={menuTriggerRect}
            />,
            document.body,
          );
        }
        return null;
      })()}
    </>
  );
}
