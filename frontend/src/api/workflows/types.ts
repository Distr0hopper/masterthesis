export const StepMatchStatus = {
  SUGGESTED: 'suggested',
  CONFIRMED: 'confirmed',
  UNMATCHED: 'unmatched',
} as const;
export type StepMatchStatus = (typeof StepMatchStatus)[keyof typeof StepMatchStatus];

export interface ComponentSummaryDto {
  id: string;
  name: string;
  version: number;
  domain: string;
}

export interface WorkflowStepDto {
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

export interface WorkflowListItemDto {
  id: string;
  name: string;
  description: string | null;
  domains: string[];
  stepCount: number;
  createdAt: string;
}

export interface WorkflowDetailDto {
  id: string;
  name: string;
  description: string | null;
  domains: string[];
  createdBy: WorkflowCreatorDto | null;
  steps: WorkflowStepDto[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateWorkflowDto {
  name: string;
  domains: string[];
  description?: string | null;
}

export interface WorkflowListQueryParams {
  domain?: string;
}
