import type { LoginDto, RegisterDto, UserResponseDto } from './types';
import type { LoginFormData, RegisterFormData } from './schema';

export interface UserDisplayModel {
  id: string;
  email: string;
  fullName: string | null;
  affiliation: string | null;
  createdAt: Date;
}

export const authTransformer = {
  getInitialLoginFormValues(): LoginFormData {
    return { email: '', password: '' };
  },

  getInitialRegisterFormValues(): RegisterFormData {
    return { email: '', firstName: '', lastName: '', password: '', confirmPassword: '' };
  },

  formToLoginDto(form: LoginFormData): LoginDto {
    return { email: form.email, password: form.password };
  },

  formToRegisterDto(form: RegisterFormData): RegisterDto {
    return {
      email: form.email,
      firstName: form.firstName,
      lastName: form.lastName,
      password: form.password,
    };
  },

  dtoToDisplayModel(dto: UserResponseDto): UserDisplayModel {
    return {
      id: dto.id,
      email: dto.email,
      fullName: dto.firstName && dto.lastName ? `${dto.firstName} ${dto.lastName}` : null,
      affiliation: dto.affiliation,
      createdAt: new Date(dto.createdAt),
    };
  },
};