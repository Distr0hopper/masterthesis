import { create } from 'zustand';
import type { UserResponseDto } from '@/api/auth/types';

interface AuthState {
  token: string | null;
  user: UserResponseDto | null;
  setToken: (token: string) => void;
  setAuth: (token: string, user: UserResponseDto) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  setToken: (token) => set({ token }),
  setAuth: (token, user) => set({ token, user }),
  logout: () => set({ token: null, user: null }),
  isAuthenticated: () => !!get().token,
}));