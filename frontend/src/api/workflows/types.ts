import type {
  ComponentDetailBaseDto,
  ComponentKind,
  ComponentListItemBaseDto,
  ComponentSource,
  ComponentStatus,
  FormatLabelDto,
} from '@/api/components/types';
import type { WithHateoasLinks } from '@/api/types';
import type { ToolPreviewDto } from '@/api/tools/types';

export const StepMatchStatus = {
  SUGGESTED: 'suggested',
  CONFIRMED: 'confirmed',
  UNMATCHED: 'unmatched',
  INLINE: 'inline',
} as const;
export type StepMatchStatus = (typeof StepMatchStatus)[keyof typeof StepMatchStatus];

/** The child a step runs - a tool, or a nested workflow. */
export interface ComponentSummaryDto {
  id: string;
  kind: ComponentKind;
  name: string;
  version: number;
  domains: string[];
  status: ComponentStatus;
  canPublish: boolean;
}

/** One step of a workflow - the edge of the composite, from the workflow to the child it runs. */
export interface WorkflowStepDto extends WithHateoasLinks {
  id: string;
  stepId: string;
  runReference: string;
  stepOrder: number;
  component: ComponentSummaryDto | null;
  matchStatus: StepMatchStatus;
  matchScore: number | null;
}

/** What only a workflow - the composite - has on top of the shared list row. */
export interface WorkflowListItemDto extends ComponentListItemBaseDto {
  kind: typeof ComponentKind.WORKFLOW;
  stepCount: number;
  source: ComponentSource;
  /** set only for source=workflow_builder, and cleared if that draft is deleted */
  draftId: string | null;
}

export interface WorkflowDetailDto extends ComponentDetailBaseDto {
  kind: typeof ComponentKind.WORKFLOW;
  steps: WorkflowStepDto[];
  draftId: string | null;
}

/** Mirrors the backend's WorkflowStepCommandTypesApiV1 - POST /workflows/steps/{id}/commands. */
export const WorkflowStepCommand = {
  CONFIRM: 'CONFIRM',
} as const;
export type WorkflowStepCommand = (typeof WorkflowStepCommand)[keyof typeof WorkflowStepCommand];

export interface WorkflowStepCommandExecuteRequest {
  command: WorkflowStepCommand;
  note?: string;
}

/**
 * The user's decision for one previewed step, keyed by WorkflowStepPreviewDto.stepId.
 * Exactly one branch: reuseComponentId binds the step to an existing component, or
 * name+domains create a new tool from that step's CWL.
 */
export interface ComponentConfigDto {
  stepId: string;
  reuseComponentId?: string | null;
  name?: string | null;
  domains?: string[] | null;
  description?: string | null;
  /** create branch only - hand-written labels for File ports without an ontology format */
  formatLabels?: FormatLabelDto[];
}

export interface CreateWorkflowDto {
  name: string;
  domains: string[];
  description?: string | null;
  componentConfigs: ComponentConfigDto[];
}

/** Where a previewed step's CWL came from. */
export const ComponentOrigin = {
  /** an inline `run: {class: CommandLineTool}` lifted out of the workflow */
  INLINE: 'inline',
  /** a `run: some-tool.cwl` resolved against the uploaded archive's own files */
  ARCHIVE: 'archive',
} as const;
export type ComponentOrigin = (typeof ComponentOrigin)[keyof typeof ComponentOrigin];

/** An existing component a previewed step could bind to instead of creating a new tool. */
export interface StepComponentMatchDto {
  componentId: string;
  /** a name conflict may be held by a workflow; a suggested match is always a tool */
  kind: ComponentKind;
  name: string;
  version: number;
  domains: string[];
  score: number | null;
}

export interface WorkflowStepPreviewDto extends ToolPreviewDto {
  stepId: string;
  origin: ComponentOrigin;
  runReference: string | null;
  suggestedName: string;
  nameConflict: StepComponentMatchDto | null;
  suggestedMatch: StepComponentMatchDto | null;
}

export interface ParseWorkflowResponseDto {
  isZip: boolean;
  isSelfContained: boolean;
  workflowName: string | null;
  description: string | null;
  stepCount: number;
  componentPreviews: WorkflowStepPreviewDto[];
  externalRefs: string[];
  inlineOnlySteps: string[];
  missingExternalRefs: string[];
  auxiliaryFiles: string[];
  missingImports: string[];
}
