import { useQuery } from '@tanstack/react-query';
import { statsService } from './service';

export const useStats = () => {
  return useQuery({
    queryKey: ['stats'] as const,
    queryFn: () => statsService.getStats(),
  });
};
