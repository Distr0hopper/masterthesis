import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { UserResponseDto } from '@/api/users/types';
import { isTokenExpired } from '@/lib/jwt';

interface AuthState {
  token: string | null;
  user: UserResponseDto | null;
  setToken: (token: string) => void;
  setAuth: (token: string, user: UserResponseDto) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setToken: (token) => set({ token }),
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      // an expired token is no login - it would only be rejected (see api/auth/session.ts)
      isAuthenticated: () => {
        const token = get().token;
        return !!token && !isTokenExpired(token);
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
);