export interface RequestOtpDto {
  email: string;
}

export interface RequestOtpResponseDto {
  cooldownSeconds: number;
}

export interface VerifyOtpDto {
  email: string;
  code: string;
}

export interface AuthResponseDto {
  accessToken: string;
  expiresIn: number;
}