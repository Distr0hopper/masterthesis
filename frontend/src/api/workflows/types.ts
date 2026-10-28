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
  /** why the child is deprecated - set only while it is */
  deprecationNote?: string | null;
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

/** Mirrors the backend's WorkflowStepCommandType - POST /workflows/steps/{id}/commands. */
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
 * Exactly one branch: reuseComponentId binds the step to an existing component,
 * newVersionOfId adds its CWL as the next version of one of your tools, or name+domains
 * create a new tool - or nested workflow - from it. A step below a reused nested workflow
 * needs no entry.
 */
export interface ComponentConfigDto {
  stepId: string;
  reuseComponentId?: string | null;
  /** your tool the step's CWL becomes the next version of - keeps its name and domains */
  newVersionOfId?: string | null;
  name?: string | null;
  domains?: string[] | null;
  description?: string | null;
  /** create and new-version branches - hand-written labels for File ports without an ontology format */
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
  /** a deprecated holder of the name can't be reused - a new step can't run it */
  status: ComponentStatus;
}

/** Uploading a new version: what the same step ran in the workflow's newest version. */
export interface PreviousStepComponentDto {
  componentId: string;
  kind: ComponentKind;
  name: string;
  version: number;
  status: ComponentStatus;
  /** the uploaded step's CWL differs from what that component holds */
  cwlChanged: boolean;
  /** the step may become that tool's next version - your own, not packaged from GitHub */
  canAddVersion: boolean;
}

/** An upload as the next version of a workflow - name and domains are its lineage's. */
export interface AddWorkflowVersionDto {
  description?: string | null;
  componentConfigs: ComponentConfigDto[];
}

/**
 * One component the upload needs a decision for - an archive file is one preview however
 * many steps run it. A nested workflow from the archive is followed by its own steps, which
 * point back at it through parentStepId.
 */
export interface WorkflowStepPreviewDto extends ToolPreviewDto {
  /** the config key: the step's path from the top (`inner/generate_graph`), the plain step id at the top level */
  stepId: string;
  /** a tool, or a nested workflow from the archive */
  kind?: ComponentKind;
  /** the nested workflow whose step first runs it - null at the top level */
  parentStepId?: string | null;
  /** the paths of every step running it, stepId first */
  usedBy?: string[];
  origin: ComponentOrigin;
  /** the archive path of the file, archive origin only */
  runReference: string | null;
  suggestedName: string;
  nameConflict: StepComponentMatchDto | null;
  suggestedMatch: StepComponentMatchDto | null;
  /** uploading a new version only - what the same step runs in the workflow's newest version */
  previous?: PreviousStepComponentDto | null;
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
  /** workflow files in the archive the root never runs - left out of the upload */
  unusedWorkflowFiles?: string[];
}
