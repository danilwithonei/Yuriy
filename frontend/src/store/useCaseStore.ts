import { create } from 'zustand';
import axios from 'axios';

export interface Case {
  id: number;
  client_id: number;
  status: 'open' | 'researching' | 'ready';
  case_type: 'intake' | 'direct';
  created_at: string;
  case_file?: string;
}

interface CaseState {
  cases: Case[];
  activeCaseId: number | null;
  loading: boolean;
  
  setCases: (cases: Case[]) => void;
  addCase: (newCase: Case) => void;
  updateCaseStatus: (caseId: number, status: Case['status']) => void;
  setActiveCaseId: (id: number | null) => void;
  fetchCases: () => Promise<void>;
  createCase: (type: 'intake' | 'direct') => Promise<number>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

  setActiveCaseId: (id) => set({ activeCaseId: id }),

  fetchCases: async () => {
    set({ loading: true });
    try {
      const response = await axios.get(`${API_URL}/cases`);
      set({ cases: response.data, loading: false });
    } catch (error) {
      console.error('Failed to fetch cases:', error);
      set({ loading: false });
    }
  },

  createCase: async (type) => {
    const response = await axios.post(`${API_URL}/cases`, { type });
    const { case_id, case_type } = response.data;
    const newCase: Case = {
      id: case_id,
      client_id: 0,
      status: 'open',
      case_type: case_type || type,
      created_at: new Date().toISOString(),
    };
    set((state) => ({
      cases: [newCase, ...state.cases],
    }));
    return case_id;
  },
}));
