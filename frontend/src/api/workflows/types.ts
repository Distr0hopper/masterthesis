import type { PageParams, PageResponse, WithHateoasLinks } from '@/api/types';

export const StepMatchStatus = {
  SUGGESTED: 'suggested',
  CONFIRMED: 'confirmed',
  UNMATCHED: 'unmatched',
} as const;
export type StepMatchStatus = (typeof StepMatchStatus)[keyof typeof StepMatchStatus];

export const WorkflowSource = {
  WORKFLOW_BUILDER: 'workflow_builder',
  MANUAL_UPLOAD: 'manual_upload',
} as const;
export type WorkflowSource = (typeof WorkflowSource)[keyof typeof WorkflowSource];

export const WorkflowStatus = {
  PENDING_VALIDATION: 'pending_validation',
  VALIDATED: 'validated',
} as const;
export type WorkflowStatus = (typeof WorkflowStatus)[keyof typeof WorkflowStatus];

export interface ComponentSummaryDto {
  id: string;
  name: string;
  version: number;
  domain: string;
}

export interface WorkflowStepDto extends WithHateoasLinks {
  id: string;
  stepId: string;
  runReference: string;
  stepOrder: number;
  component: ComponentSummaryDto | null;
  matchStatus: StepMatchStatus;
  matchScore: number | null;
}

export interface WorkflowCreatorDto {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
}

export interface WorkflowListItemDto extends WithHateoasLinks {
  id: string;
  name: string;
  description: string | null;
  domains: string[];
  stepCount: number;
  status: WorkflowStatus;
  source: WorkflowSource;
  /** set only for source=workflow_builder, and cleared if that draft is deleted */
  draftId: string | null;
  createdAt: string;
}

export interface WorkflowDetailDto extends WithHateoasLinks {
  id: string;
  name: string;
  description: string | null;
  domains: string[];
  createdBy: WorkflowCreatorDto | null;
  steps: WorkflowStepDto[];
  status: WorkflowStatus;
  source: WorkflowSource;
  /** set only for source=workflow_builder, and cleared if that draft is deleted */
  draftId: string | null;
  cwlContent: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateWorkflowDto {
  name: string;
  domains: string[];
  description?: string | null;
}

export interface WorkflowListQueryParams extends PageParams<WorkflowListItemDto> {
  domain?: string;
  search?: string;
}

export interface MyWorkflowsResponseDto {
  published: PageResponse<WorkflowListItemDto>;
  pending: PageResponse<WorkflowListItemDto>;
}

export interface MyWorkflowsQueryParams {
  limit?: number;
  publishedOffset?: number;
  pendingOffset?: number;
}
