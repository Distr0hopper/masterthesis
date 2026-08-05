import { useMutation, useQueryClient } from '@tanstack/react-query';
import { usersService } from './service';
import type { UpdateUserDto } from './types';
import { authKeys } from '@/api/auth';
import { useAuthStore } from '@/store/auth.store';

export const useUpdateProfile = () => {
  const queryClient = useQueryClient();
  const token = useAuthStore((state) => state.token);
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: (dto: UpdateUserDto) => usersService.updateMe(dto),
    onSuccess: (user) => {
      if (token) setAuth(token, user);
      queryClient.invalidateQueries({ queryKey: authKeys.me() });
    },
  });
};