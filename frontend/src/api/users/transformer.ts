import type { UpdateProfileFormData } from './schema';
import type { UpdateUserDto, UserResponseDto } from './types';

export const usersTransformer = {
  getInitialUpdateProfileFormValues(user: UserResponseDto | null): UpdateProfileFormData {
    return {
      firstName: user?.firstName ?? '',
      lastName: user?.lastName ?? '',
      affiliation: user?.affiliation ?? '',
    };
  },

  formToUpdateUserDto(form: UpdateProfileFormData): UpdateUserDto {
    return {
      firstName: form.firstName,
      lastName: form.lastName,
      affiliation: form.affiliation || undefined,
    };
  },
};