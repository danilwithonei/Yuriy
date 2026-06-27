import { create } from 'zustand';
import api from '@/lib/api';

export interface Case {
  id: string;
  client_id: number;
  lawyer_id?: number | null;
  status: 'open' | 'researching' | 'ready';
  case_type: 'intake' | 'direct';
  created_at: string;
  case_file?: string;
  title?: string;
  summary?: string;
  pinned?: boolean;
}

interface CaseState {
  cases: Case[];
  activeCaseId: string | null;
  loading: boolean;

  setCases: (cases: Case[]) => void;
  addCase: (newCase: Case) => void;
  removeCase: (caseId: string) => void;
  updateCaseStatus: (caseId: string, status: Case['status']) => void;
  updateCaseMeta: (caseId: string, meta: Partial<Case>) => void;
  setCasePinned: (caseId: string, pinned: boolean) => void;
  setActiveCaseId: (id: string | null) => void;
  fetchCases: () => Promise<void>;
  createCase: (type: 'intake' | 'direct') => Promise<string>;
  deleteCase: (id: string) => Promise<void>;
  togglePin: (id: string) => Promise<void>;
}

export const useCaseStore = create<CaseState>((set, get) => ({
  cases: [],
  activeCaseId: null,
  loading: false,

  setCases: (cases) => set({ cases }),

  addCase: (newCase) => set((state) => ({
    cases: [newCase, ...state.cases.filter(c => c.id !== newCase.id)]
  })),

  removeCase: (caseId) => set((state) => ({
    cases: state.cases.filter((c) => c.id !== caseId),
  })),

  updateCaseStatus: (caseId, status) => set((state) => ({
    cases: state.cases.map((c) =>
      c.id === caseId ? { ...c, status } : c
    )
  })),

  updateCaseMeta: (caseId, meta) => set((state) => ({
    cases: state.cases.map((c) =>
      c.id === caseId ? { ...c, ...meta } : c
    )
  })),

  setCasePinned: (caseId, pinned) => set((state) => ({
    cases: state.cases.map((c) =>
      c.id === caseId ? { ...c, pinned } : c
    ),
  })),

  setActiveCaseId: (id) => set({ activeCaseId: id }),

  fetchCases: async () => {
    set({ loading: true });
    try {
      const response = await api.get('/cases');
      const cases: Case[] = response.data;
      const sorted = [...cases].sort((a, b) => {
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      set({ cases: sorted, loading: false });
    } catch (error) {
      console.error('Failed to fetch cases:', error);
      set({ loading: false });
    }
  },

  createCase: async (type) => {
    const response = await api.post('/cases', { type });
    const { case_id, case_type, lawyer_id } = response.data;
    const newCase: Case = {
      id: case_id,
      client_id: 0,
      lawyer_id,
      status: 'open',
      case_type: case_type || type,
      created_at: new Date().toISOString(),
      title: type === 'direct' ? 'Чат' : undefined,
      pinned: false,
    };
    set((state) => ({
      cases: [newCase, ...state.cases],
    }));
    return case_id;
  },

  deleteCase: async (id: string) => {
    try {
      await api.delete(`/cases/${id}`);
      set((state) => ({
        cases: state.cases.filter((c) => c.id !== id),
      }));
    } catch (e) {
      console.error('deleteCase error:', e);
    }
  },

  togglePin: async (id: string) => {
    const current = get().cases.find((c) => c.id === id);
    const nextPinned = !current?.pinned;
    await api.patch(`/cases/${id}/pin`, { pinned: nextPinned });
    set((state) => ({
      cases: state.cases.map((c) =>
        c.id === id ? { ...c, pinned: nextPinned } : c
      ),
    }));
  },
}));
