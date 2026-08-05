import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authService } from './service';
import type { RequestOtpDto, VerifyOtpDto } from './types';
import { useAuthStore } from '@/store/auth.store';

export const authKeys = {
  all: ['auth'] as const,
  me: () => [...authKeys.all, 'me'] as const,
};

export const useMe = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  return useQuery({
    queryKey: authKeys.me(),
    queryFn: () => authService.me(),
    enabled: isAuthenticated,
  });
};

export const useRequestOtp = () => {
  return useMutation({
    mutationFn: (data: RequestOtpDto) => authService.requestOtp(data),
  });
};

export const useVerifyOtp = () => {
  const queryClient = useQueryClient();
  const setToken = useAuthStore((state) => state.setToken);
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (data: VerifyOtpDto) => {
      const auth = await authService.verifyOtp(data);
      // token must be in the store before /users/me so the request interceptor attaches it
      setToken(auth.accessToken);
      const user = await authService.me();
      setAuth(auth.accessToken, user);
      return user;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: authKeys.all });
    },
  });
};