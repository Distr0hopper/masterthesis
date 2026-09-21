import type { PageParams, SplitPageResponse, WithHateoasLinks } from '@/api/types';

export type ComponentDomain = string;

export interface DomainDto {
  id: string;
  color: string;
}

export const ComponentSource = {
  AUTOMATED_PACKAGING: 'automated_packaging',
  MANUAL_UPLOAD: 'manual_upload',
} as const;
export type ComponentSource = (typeof ComponentSource)[keyof typeof ComponentSource];

export const ComponentStatus = {
  DRAFT: 'draft',
  PUBLISHED: 'published',
} as const;
export type ComponentStatus = (typeof ComponentStatus)[keyof typeof ComponentStatus];

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

/** The component currently holding a name, returned when that name is taken. */
export interface ExistingComponentDto {
  id: string;
  name: string;
  version: number;
  domains: ComponentDomain[];
  status: ComponentStatus;
}

/** Whether a component name can still be claimed for a new lineage. */
export interface NameAvailabilityDto {
  name: string;
  available: boolean;
  /** the latest version of the lineage already holding this name, if any */
  existing: ExistingComponentDto | null;
}

/**
 * A component read out of a CWL document without persisting it - what
 * POST /components/parse returns. Also the shared base of the workflow flow's
 * WorkflowStepPreviewDto, which adds the step the CWL came from.
 */
export interface ComponentPreviewDto {
  description: string | null;
  cwlContent: string;
  cwlType: string | null;
  dockerfileContent: string | null;
  dockerPullReference: string | null;
  parameters: PreviewParameterDto[];
}

/** A previewed component port - never persisted, so `id` is synthetic. */
export interface PreviewParameterDto {
  id: string;
  name: string;
  cwlType: string;
  defaultValue: string | null;
  description: string | null;
  format: string | null;
  formatLabel: string | null;
  direction: ParameterDirection;
}

export const ComponentCommand = {
  ADD_FAVORITE: 'ADD_FAVORITE',
  REMOVE_FAVORITE: 'REMOVE_FAVORITE',
  REPACKAGE: 'REPACKAGE',
  PUBLISH: 'PUBLISH',
  UNPUBLISH: 'UNPUBLISH',
  UPDATE_DESCRIPTION: 'UPDATE_DESCRIPTION',
  UPDATE_DOMAIN: 'UPDATE_DOMAIN',
} as const;
export type ComponentCommand = (typeof ComponentCommand)[keyof typeof ComponentCommand];

export type ComponentCommandExecuteRequest =
  | {
      command:
        | typeof ComponentCommand.ADD_FAVORITE
        | typeof ComponentCommand.REMOVE_FAVORITE
        | typeof ComponentCommand.REPACKAGE
        | typeof ComponentCommand.PUBLISH
        | typeof ComponentCommand.UNPUBLISH;
      note?: string;
    }
  | { command: typeof ComponentCommand.UPDATE_DESCRIPTION; note?: string; description: string | null }
  | { command: typeof ComponentCommand.UPDATE_DOMAIN; note?: string; domains: ComponentDomain[] };

export interface ComponentListItemDto extends WithHateoasLinks {
  id: string;
  name: string;
  description: string | null;
  authorName: string | null;
  repoUrl: string | null;
  version: number;
  domains: ComponentDomain[];
  status: ComponentStatus;
  createdAt: string;
  isFavorite: boolean;
  /** only present when the request passed `includeParameters: true` - null otherwise */
  parameters: ParameterDto[] | null;
}

export interface ComponentCreatorDto {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
}

export interface ComponentDetailDto extends WithHateoasLinks {
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
  cwlType: string | null;
  dockerfileContent: string | null;
  dockerPullReference: string | null;
  domains: ComponentDomain[];
  source: ComponentSource;
  status: ComponentStatus;
  parameters: ParameterDto[];
  createdAt: string;
  updatedAt: string;
  isFavorite: boolean;
}

export interface CreateComponentDto {
  name: string;
  domains: string[];
  authorName?: string;
  repoUrl?: string;
  repoCommitSha?: string;
  description?: string | null;
}

export interface PackageComponentDto {
  repoUrl: string;
  domains: string[];
  description?: string | null;
}

export interface AddVersionDto {
  repoCommitSha?: string;
  description?: string;
}

export interface ComponentListQueryParams extends PageParams<ComponentListItemDto> {
  domain?: ComponentDomain;
  excludeMine?: boolean;
  favoritesOnly?: boolean;
  search?: string;
  /** opt into the per-item parameter list; only the workflow builder needs it */
  includeParameters?: boolean;
}
export type MyComponentsResponseDto = SplitPageResponse<ComponentListItemDto>;
