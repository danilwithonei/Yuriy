import { create } from "zustand";

import api from "@/lib/api";

interface Lawyer {
  id: number;
  email: string;
  name: string;
}

interface AuthState {
  lawyer: Lawyer | null;
  token: string | null;
  isChecking: boolean;
  isReady: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  lawyer: null,
  token: null,
  isChecking: true,
  isReady: false,

  checkAuth: async () => {
    set({ isChecking: true });
    const token = localStorage.getItem("token");
    if (!token) {
      set({ isChecking: false, isReady: true });
      return;
    }
    try {
      const res = await api.get("/auth/me");
      set({ lawyer: res.data, token, isChecking: false, isReady: true });
    } catch {
      localStorage.removeItem("token");
      set({ isChecking: false, isReady: true });
    }
  },

  login: async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    const { token, lawyer } = res.data;
    localStorage.setItem("token", token);
    set({ token, lawyer });
  },

  register: async (email, name, password) => {
    const res = await api.post("/auth/register", { email, name, password });
    const { token, lawyer } = res.data;
    localStorage.setItem("token", token);
    set({ token, lawyer });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ lawyer: null, token: null });
    window.location.href = "/login";
  },
}));
