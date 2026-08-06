export type ComponentDomain = string;

export const ComponentSource = {
  AUTOMATED_PACKAGING: 'automated_packaging',
  MANUAL_UPLOAD: 'manual_upload',
} as const;
export type ComponentSource = (typeof ComponentSource)[keyof typeof ComponentSource];

export const ParameterDirection = {
  INPUT: 'input',
  OUTPUT: 'output',
} as const;
export type ParameterDirection = (typeof ParameterDirection)[keyof typeof ParameterDirection];

export interface ParameterDto {
  id: string;
  name: string;
  cwlType: string;
  defaultValue: string | null;
  description: string | null;
  format: string | null;
  formatLabel: string | null;
  direction: ParameterDirection;
}

export interface ComponentListItemDto {
  id: string;
  name: string;
  authorName: string | null;
  repoUrl: string | null;
  repoCommitSha: string | null;
  version: number;
  domain: ComponentDomain;
  source: ComponentSource;
  createdAt: string;
}

export interface ComponentCreatorDto {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
}

export interface ComponentDetailDto {
  id: string;
  name: string;
  authorName: string | null;
  createdBy: ComponentCreatorDto | null;
  description: string | null;
  repoUrl: string | null;
  repoCommitSha: string | null;
  doi: string | null;
  version: number;
  cwlContent: string;
  domain: ComponentDomain;
  source: ComponentSource;
  parameters: ParameterDto[];
  createdAt: string;
}

export interface CreateComponentDto {
  name: string;
  domain: string;
  authorName?: string;
  repoUrl?: string;
  repoCommitSha?: string;
  description?: string | null;
}

export interface UpdateComponentDto {
  description?: string | null;
  domain?: string;
}

export interface PackageComponentDto {
  repoUrl: string;
  domain: string;
  description?: string | null;
}

export interface AddVersionDto {
  repoCommitSha?: string;
  description?: string;
}

export interface ComponentListQueryParams {
  domain?: ComponentDomain;
}