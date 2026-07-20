import { apiClient } from '../client';
import type { AuthResponseDto, LoginDto, RegisterDto, UserResponseDto } from './types';

const ENDPOINT = '/auth';

export const authService = {
  register(data: RegisterDto): Promise<UserResponseDto> {
    return apiClient.post(`${ENDPOINT}/register`, data);
  },

  login(data: LoginDto): Promise<AuthResponseDto> {
    return apiClient.post(`${ENDPOINT}/login`, data);
  },

  me(): Promise<UserResponseDto> {
    return apiClient.get(`${ENDPOINT}/me`);
  },
};