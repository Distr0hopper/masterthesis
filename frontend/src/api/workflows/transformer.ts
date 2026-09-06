import type { WorkflowDetailDto, WorkflowListItemDto, WorkflowStepDto } from './types';
import { StepMatchStatus, WorkflowSource, WorkflowStatus } from './types';
import type { UpdateWorkflowDescriptionFormData, UploadWorkflowFormData } from './schema';
import { getDomainLabel } from '@/api/components';
import { formatDate, getCreatorDisplay } from '@/api/transformer';
import type { WithHateoasLinks } from '@/api/types';

const MATCH_STATUS_LABELS: Record<StepMatchStatus, string> = {
  [StepMatchStatus.SUGGESTED]: 'Suggested match — please confirm',
  [StepMatchStatus.CONFIRMED]: 'Confirmed',
  [StepMatchStatus.UNMATCHED]: 'Not matched',
};

const WORKFLOW_SOURCE_LABELS: Record<WorkflowSource, string> = {
  [WorkflowSource.WORKFLOW_BUILDER]: 'Built in Workflow Builder',
  [WorkflowSource.MANUAL_UPLOAD]: 'Uploaded archive',
};

const WORKFLOW_STATUS_LABELS: Record<WorkflowStatus, string> = {
  [WorkflowStatus.PENDING_VALIDATION]: 'Pending validation',
  [WorkflowStatus.VALIDATED]: 'Validated',
};

export interface WorkflowStepDisplayModel extends WithHateoasLinks {
  id: string;
  stepId: string;
  runReference: string;
  stepOrder: number;
  componentId: string | null;
  componentName: string | null;
  componentVersion: number | null;
  matchStatus: StepMatchStatus;
  matchStatusDisplay: string;
  matchScore: number | null;
}

export interface WorkflowDisplayModel extends WithHateoasLinks {
  id: string;
  name: string;
  description: string | null;
  domains: string[];
  domainsDisplay: string[];
  stepCount: number;
  status: WorkflowStatus;
  statusDisplay: string;
  source: WorkflowSource;
  sourceDisplay: string;
  /** the builder draft this came from, when it is still available */
  draftId: string | null;
  createdAt: Date;
  createdAtDisplay: string;
}

export interface WorkflowDetailDisplayModel extends WorkflowDisplayModel {
  createdById: string | null;
  createdByDisplay: string;
  steps: WorkflowStepDisplayModel[];
  cwlContent: string;
  updatedAt: Date;
  updatedAtDisplay: string;
}

export const workflowTransformer = {
  getInitialUploadFormValues(): Omit<UploadWorkflowFormData, 'zipFile'> {
    return { name: '', domains: [], description: '' };
  },

  getInitialUpdateDescriptionFormValues(workflow: WorkflowDetailDisplayModel): UpdateWorkflowDescriptionFormData {
    return { description: workflow.description ?? '' };
  },

  toStepDisplayModel(dto: WorkflowStepDto): WorkflowStepDisplayModel {
    // a manually-touched selection always has matchScore === null (backend clears it on
    // any PATCH), so this distinguishes "algorithm guessed this" from "you picked this"
    const isManualPick = dto.matchStatus === StepMatchStatus.SUGGESTED && dto.matchScore === null;
    return {
      id: dto.id,
      stepId: dto.stepId,
      runReference: dto.runReference,
      stepOrder: dto.stepOrder,
      componentId: dto.component?.id ?? null,
      componentName: dto.component?.name ?? null,
      componentVersion: dto.component?.version ?? null,
      matchStatus: dto.matchStatus,
      matchStatusDisplay: isManualPick ? 'Selected — please confirm' : MATCH_STATUS_LABELS[dto.matchStatus],
      matchScore: dto.matchScore,
      _links: dto._links,
    };
  },

  toDisplayModel(dto: WorkflowListItemDto): WorkflowDisplayModel {
    const createdAt = new Date(dto.createdAt);
    return {
      id: dto.id,
      name: dto.name,
      description: dto.description,
      domains: dto.domains,
      domainsDisplay: dto.domains.map(getDomainLabel),
      stepCount: dto.stepCount,
      status: dto.status,
      statusDisplay: WORKFLOW_STATUS_LABELS[dto.status],
      source: dto.source,
      sourceDisplay: WORKFLOW_SOURCE_LABELS[dto.source],
      draftId: dto.draftId,
      createdAt,
      createdAtDisplay: formatDate(createdAt),
      _links: dto._links,
    };
  },

  toListDisplayModels(dtos: WorkflowListItemDto[]): WorkflowDisplayModel[] {
    // self-reference by name, not `this` - toListDisplayModel() passes this method
    // around as a bare function reference, which would drop a `this` binding
    return dtos.map((dto) => workflowTransformer.toDisplayModel(dto));
  },

  toDetailDisplayModel(dto: WorkflowDetailDto): WorkflowDetailDisplayModel {
    const updatedAt = new Date(dto.updatedAt);
    return {
      ...this.toDisplayModel({ ...dto, stepCount: dto.steps.length }),
      createdById: dto.createdBy?.id ?? null,
      createdByDisplay: getCreatorDisplay(dto.createdBy),
      steps: dto.steps.map(this.toStepDisplayModel),
      cwlContent: dto.cwlContent,
      updatedAt,
      updatedAtDisplay: formatDate(updatedAt),
    };
  },
};
