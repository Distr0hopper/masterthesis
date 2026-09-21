import type { PageParams, SplitPageResponse, WithHateoasLinks } from '@/api/types';
import type { ComponentPreviewDto } from '@/api/components/types';

export const StepMatchStatus = {
  SUGGESTED: 'suggested',
  CONFIRMED: 'confirmed',
  UNMATCHED: 'unmatched',
  /** runs inline in the pipeline (ExpressionTool / nested Workflow) - no component to match */
  INLINE: 'inline',
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
  domains: string[];
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
  ADD_FAVORITE: 'ADD_FAVORITE',
  REMOVE_FAVORITE: 'REMOVE_FAVORITE',
  PUBLISH: 'PUBLISH',
  UNPUBLISH: 'UNPUBLISH',
  UPDATE_DESCRIPTION: 'UPDATE_DESCRIPTION',
} as const;
export type WorkflowCommand = (typeof WorkflowCommand)[keyof typeof WorkflowCommand];

export type WorkflowCommandExecuteRequest =
  | {
      command:
        | typeof WorkflowCommand.ADD_FAVORITE
        | typeof WorkflowCommand.REMOVE_FAVORITE
        | typeof WorkflowCommand.PUBLISH
        | typeof WorkflowCommand.UNPUBLISH;
      note?: string;
    }
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
  isFavorite: boolean;
  status: WorkflowStatus;
  source: WorkflowSource;
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
  isFavorite: boolean;
  status: WorkflowStatus;
  source: WorkflowSource;
  draftId: string | null;
  cwlContent: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * The user's decision for one previewed step, keyed by WorkflowStepPreviewDto.stepId.
 * Exactly one branch: reuseComponentId binds the step to an existing component, or
 * name+domains create a new one from that step's CWL.
 */
export interface ComponentConfigDto {
  stepId: string;
  reuseComponentId?: string | null;
  name?: string | null;
  domains?: string[] | null;
  description?: string | null;
}

export interface CreateWorkflowDto {
  name: string;
  domains: string[];
  description?: string | null;
  /** one entry per step - every step must be configured before the workflow can be saved */
  componentConfigs: ComponentConfigDto[];
}

export interface WorkflowListQueryParams extends PageParams<WorkflowListItemDto> {
  domain?: string[];
  search?: string;
  favoritesOnly?: boolean;
}

export type MyWorkflowsResponseDto = SplitPageResponse<WorkflowListItemDto>;

/** Where a previewed component's CWL came from. */
export const ComponentOrigin = {
  /** an inline `run: {class: CommandLineTool}` lifted out of the workflow */
  INLINE: 'inline',
  /** a `run: some-tool.cwl` resolved against the uploaded archive's own files */
  ARCHIVE: 'archive',
} as const;
export type ComponentOrigin = (typeof ComponentOrigin)[keyof typeof ComponentOrigin];

/** An existing component a step could bind to instead of creating a new one. */
export interface ComponentMatchDto {
  componentId: string;
  name: string;
  version: number;
  domains: string[];
  /** fuzzy-match confidence; null for an exact name collision, which isn't a guess */
  score: number | null;
}

/** One workflow step rendered as the Component it would become, for review before saving. */
export interface WorkflowStepPreviewDto extends ComponentPreviewDto {
  stepId: string;
  origin: ComponentOrigin;
  /** the `run:` filename, archive origin only */
  runReference: string | null;
  suggestedName: string;
  /** an existing component already holding suggestedName - the user must rename or reuse it */
  nameConflict: ComponentMatchDto | null;
  /** archive origin only - the catalogue component this step's run: filename matches */
  suggestedMatch: ComponentMatchDto | null;
}

export interface ParseWorkflowResponseDto {
  /** whether the upload was a .zip archive (vs a bare .cwl file) */
  isZip: boolean;
  isSelfContained: boolean;
  workflowName: string | null;
  stepCount: number;
  /** one per resolvable step, inline and archive alike */
  componentPreviews: WorkflowStepPreviewDto[];
  /** steps whose run: is a plain filename - not extracted, the caller must supply these separately */
  externalRefs: string[];
  /** steps whose run: is inline but not class: CommandLineTool (e.g. an inline ExpressionTool) */
  /**
   * Steps whose run: is an inline definition that isn't a CommandLineTool. They stay
   * embedded in the saved pipeline and never become components, so they need no
   * configuration - informational, not blocking.
   */
  inlineOnlySteps: string[];
  /** external refs not found among the zip's own .cwl files - always [] for a bare .cwl upload */
  missingExternalRefs: string[];
}
