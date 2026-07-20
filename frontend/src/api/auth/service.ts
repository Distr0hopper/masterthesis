import { apiClient } from '../client';
import type { AuthResponseDto, LoginDto, RegisterDto, UserResponseDto } from './types';

const ENDPOINT = '/auth';

export const authService = {
  register(data: RegisterDto): Promise<UserResponseDto> {
    return apiClient.post(`${ENDPOINT}/register`, data).then((res) => res.data);
  },

  login(data: LoginDto): Promise<AuthResponseDto> {
    return apiClient.post(`${ENDPOINT}/login`, data).then((res) => res.data);
  },

  me(): Promise<UserResponseDto> {
    return apiClient.get(`${ENDPOINT}/me`).then((res) => res.data);
  },
};