import { apiClient } from '../client';
import type { CompatibilityResponseDto, FormatPairDto } from './types';

export const compatibilityService = {
  check(pairs: FormatPairDto[]): Promise<CompatibilityResponseDto> {
    return apiClient.post('/compatibility', { pairs });
  },
};
