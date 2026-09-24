import { apiClient } from '../client';
import type { CompatibilityResponseDto, ConnectionDto } from './types';

export const compatibilityService = {
  check(connections: ConnectionDto[]): Promise<CompatibilityResponseDto> {
    return apiClient.post('/compatibility', { connections });
  },
};
