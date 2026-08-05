import type { RequestOtpDto, VerifyOtpDto } from './types';
import type { RequestOtpFormData, VerifyOtpFormData } from './schema';
import type { UserResponseDto } from '@/api/users/types';

export interface UserDisplayModel {
  id: string;
  email: string;
  fullName: string | null;
  affiliation: string | null;
  createdAt: Date;
}

export const authTransformer = {
  getInitialRequestOtpFormValues(): RequestOtpFormData {
    return { email: '' };
  },

  getInitialVerifyOtpFormValues(): VerifyOtpFormData {
    return { code: '' };
  },

  formToRequestOtpDto(form: RequestOtpFormData): RequestOtpDto {
    return { email: form.email };
  },

  formToVerifyOtpDto(email: string, form: VerifyOtpFormData): VerifyOtpDto {
    return { email, code: form.code };
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