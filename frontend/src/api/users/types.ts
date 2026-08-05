export interface UserResponseDto {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  affiliation: string | null;
  createdAt: string;
}

export interface UpdateUserDto {
  firstName?: string;
  lastName?: string;
  affiliation?: string;
}