import type { WorkflowDetailDto, WorkflowListItemDto, WorkflowStepDto } from './types';
import { StepMatchStatus, WorkflowStatus } from './types';
import type { UploadWorkflowFormData } from './schema';
import { getDomainLabel } from '@/api/components';
import { formatDate, getCreatorDisplay } from '@/api/transformer';

const MATCH_STATUS_LABELS: Record<StepMatchStatus, string> = {
  [StepMatchStatus.SUGGESTED]: 'Suggested match — please confirm',
  [StepMatchStatus.CONFIRMED]: 'Confirmed',
  [StepMatchStatus.UNMATCHED]: 'Not matched',
};

const WORKFLOW_STATUS_LABELS: Record<WorkflowStatus, string> = {
  [WorkflowStatus.PENDING_VALIDATION]: 'Pending validation',
  [WorkflowStatus.VALIDATED]: 'Validated',
};

export interface WorkflowStepDisplayModel {
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

export interface WorkflowDisplayModel {
  id: string;
  name: string;
  description: string | null;
  domains: string[];
  domainsDisplay: string[];
  stepCount: number;
  status: WorkflowStatus;
  statusDisplay: string;
  createdAt: Date;
  createdAtDisplay: string;
}

export interface WorkflowDetailDisplayModel extends WorkflowDisplayModel {
  createdById: string | null;
  createdByDisplay: string;
  steps: WorkflowStepDisplayModel[];
  updatedAt: Date;
  updatedAtDisplay: string;
}

export const workflowTransformer = {
  getInitialUploadFormValues(): Omit<UploadWorkflowFormData, 'zipFile'> {
    return { name: '', domains: [], description: '' };
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
      createdAt,
      createdAtDisplay: formatDate(createdAt),
    };
  },

  toListDisplayModels(dtos: WorkflowListItemDto[]): WorkflowDisplayModel[] {
    return dtos.map((dto) => this.toDisplayModel(dto));
  },

  toDetailDisplayModel(dto: WorkflowDetailDto): WorkflowDetailDisplayModel {
    const updatedAt = new Date(dto.updatedAt);
    return {
      ...this.toDisplayModel({ ...dto, stepCount: dto.steps.length }),
      createdById: dto.createdBy?.id ?? null,
      createdByDisplay: getCreatorDisplay(dto.createdBy),
      steps: dto.steps.map(this.toStepDisplayModel),
      updatedAt,
      updatedAtDisplay: formatDate(updatedAt),
    };
  },
};
