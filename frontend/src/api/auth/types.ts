export interface RequestOtpDto {
  email: string;
}

export interface VerifyOtpDto {
  email: string;
  code: string;
}

export interface AuthResponseDto {
  accessToken: string;
  expiresIn: number;
}

export interface UserResponseDto {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  affiliation: string | null;
  createdAt: string;
}