import { apiClient } from './client';
import type { AuthResponse, UserResponse } from '@/types/api.types';

export const authApi = {
  register: (email: string, password: string) =>
    apiClient.post<UserResponse>('/auth/register', { email, password }),

  login: (email: string, password: string) =>
    apiClient.post<AuthResponse>('/auth/login', { email, password }),

  me: () =>
    apiClient.get<UserResponse>('/auth/me'),
};
