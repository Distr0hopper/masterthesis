import { apiClient } from '../client';
import type { UpdateUserDto, UserResponseDto } from './types';

const ENDPOINT = '/users';

export const usersService = {
  updateMe(dto: UpdateUserDto): Promise<UserResponseDto> {
    return apiClient.patch(`${ENDPOINT}/me`, dto);
  },
};