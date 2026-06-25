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
}

interface CaseState {
  cases: Case[];
  activeCaseId: string | null;
  loading: boolean;
  
  setCases: (cases: Case[]) => void;
  addCase: (newCase: Case) => void;
  updateCaseStatus: (caseId: string, status: Case['status']) => void;
  setActiveCaseId: (id: string | null) => void;
  fetchCases: () => Promise<void>;
  createCase: (type: 'intake' | 'direct') => Promise<string>;
}

export const useCaseStore = create<CaseState>((set) => ({
  cases: [],
  activeCaseId: null,
  loading: false,

  setCases: (cases) => set({ cases }),
  
  addCase: (newCase) => set((state) => ({ 
    cases: [newCase, ...state.cases.filter(c => c.id !== newCase.id)] 
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

  setActiveCaseId: (id) => set({ activeCaseId: id }),

  fetchCases: async () => {
    set({ loading: true });
    try {
      const response = await api.get('/cases');
      set({ cases: response.data, loading: false });
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
    };
    set((state) => ({
      cases: [newCase, ...state.cases],
    }));
    return case_id;
  },
}));
