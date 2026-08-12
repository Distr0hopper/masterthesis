import { apiClient } from '../client';
import type { StatsDto } from './types';

export const statsService = {
  getStats(): Promise<StatsDto> {
    return apiClient.get('/stats');
  },
};
