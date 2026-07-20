export type ComponentDomain = 'moveapps' | 'earth_observation';
export type ComponentSource = 'moveapps' | 'manual';
export type ParameterDirection = 'input' | 'output';

export interface ComponentListItem {
  id: string;
  name: string;
  repoUrl: string | null;
  domain: ComponentDomain;
  source: ComponentSource;
  author: { id: string; email: string } | null;
  createdAt: string;
}

export interface Parameter {
  id: string;
  name: string;
  cwlType: string;
  defaultValue: string | null;
  description: string | null;
  direction: ParameterDirection;
}

export interface ComponentDetail extends ComponentListItem {
  repoCommitSha: string | null;
  cwlContent: string;
  dockerfileContent: string;
  description: string | null;
  parameters: Parameter[];
  updatedAt: string;
}

export interface AuthResponse {
  access_token: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  createdAt: string;
}
