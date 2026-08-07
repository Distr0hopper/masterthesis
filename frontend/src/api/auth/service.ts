import { apiClient } from '../client';
import type { AuthResponseDto, RequestOtpDto, RequestOtpResponseDto, VerifyOtpDto } from './types';
import type { UserResponseDto } from '@/api/users/types';

const ENDPOINT = '/auth';

export const authService = {
  requestOtp(data: RequestOtpDto): Promise<RequestOtpResponseDto> {
    return apiClient.post(`${ENDPOINT}/otp/request`, data);
  },

  verifyOtp(data: VerifyOtpDto): Promise<AuthResponseDto> {
    return apiClient.post(`${ENDPOINT}/otp/verify`, data);
  },

  me(): Promise<UserResponseDto> {
    return apiClient.get('/users/me');
  },
};