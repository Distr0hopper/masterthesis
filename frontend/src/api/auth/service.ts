import { apiClient } from '../client';
import type { AuthResponseDto, RequestOtpDto, UserResponseDto, VerifyOtpDto } from './types';

const ENDPOINT = '/auth';

export const authService = {
  requestOtp(data: RequestOtpDto): Promise<void> {
    return apiClient.post(`${ENDPOINT}/otp/request`, data);
  },

  verifyOtp(data: VerifyOtpDto): Promise<AuthResponseDto> {
    return apiClient.post(`${ENDPOINT}/otp/verify`, data);
  },

  me(): Promise<UserResponseDto> {
    return apiClient.get('/users/me');
  },
};