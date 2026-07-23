export interface RegisterDto {
  email: string;
  firstName: string;
  lastName: string;
  password: string;
}

export interface LoginDto {
  email: string;
  password: string;
}

export interface AuthResponseDto {
  access_token: string;
  expires_in: number;
}

export interface UserResponseDto {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  affiliation: string | null;
  createdAt: string;
}