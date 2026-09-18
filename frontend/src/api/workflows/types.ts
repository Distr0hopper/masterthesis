import type { PageParams, SplitPageResponse, WithHateoasLinks } from '@/api/types';

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

/** Mirrors the backend's WorkflowCommandTypesApiV1 - the commands POST /workflows/{id}/commands accepts. */
export const WorkflowCommand = {
  PUBLISH: 'PUBLISH',
  UNPUBLISH: 'UNPUBLISH',
  UPDATE_DESCRIPTION: 'UPDATE_DESCRIPTION',
} as const;
export type WorkflowCommand = (typeof WorkflowCommand)[keyof typeof WorkflowCommand];

export type WorkflowCommandExecuteRequest =
  | { command: typeof WorkflowCommand.PUBLISH | typeof WorkflowCommand.UNPUBLISH; note?: string }
  | { command: typeof WorkflowCommand.UPDATE_DESCRIPTION; note?: string; description: string | null };

/** Mirrors the backend's WorkflowStepCommandTypesApiV1 - POST /workflows/steps/{id}/commands. */
export const WorkflowStepCommand = {
  CONFIRM: 'CONFIRM',
} as const;
export type WorkflowStepCommand = (typeof WorkflowStepCommand)[keyof typeof WorkflowStepCommand];

export interface WorkflowStepCommandExecuteRequest {
  command: WorkflowStepCommand;
  note?: string;
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

/** One user-edited extracted-component name, keyed by ExtractedComponentDto.stepId. */
export interface ComponentOverrideDto {
  stepId: string;
  name: string;
}

export interface CreateWorkflowDto {
  name: string;
  domains: string[];
  description?: string | null;
  /** domain for every extracted inline component in this upload - required only if the
   * upload actually has inline steps to extract. */
  componentDomain?: string | null;
  componentOverrides?: ComponentOverrideDto[];
}

export interface WorkflowListQueryParams extends PageParams<WorkflowListItemDto> {
  domain?: string;
  search?: string;
}

export type MyWorkflowsResponseDto = SplitPageResponse<WorkflowListItemDto>;

/** One inline CommandLineTool found in a self-contained/mixed upload. */
export interface ExtractedComponentDto {
  stepId: string;
  suggestedName: string;
  cwlContent: string;
  description: string | null;
  inputCount: number;
  outputCount: number;
}

export interface ParseWorkflowResponseDto {
  /** whether the upload was a .zip archive (vs a bare .cwl file) */
  isZip: boolean;
  isSelfContained: boolean;
  workflowName: string | null;
  stepCount: number;
  extractedComponents: ExtractedComponentDto[];
  /** steps whose run: is a plain filename - not extracted, the caller must supply these separately */
  externalRefs: string[];
  /** steps whose run: is inline but not class: CommandLineTool (e.g. an inline ExpressionTool) */
  unsupportedInlineSteps: string[];
  /** external refs not found among the zip's own .cwl files - always [] for a bare .cwl upload */
  missingExternalRefs: string[];
}
