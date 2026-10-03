import type { ComponentKind, ComponentSource } from '@/api/components/types';
import {
  toDetailFields,
  toDisplayModelBase,
  type ComponentDetailFields,
  type ComponentDisplayModelBase,
} from '@/api/components/transformer';
import type { WithHateoasLinks } from '@/api/types';
import type { ComponentSummaryDto, WorkflowDetailDto, WorkflowListItemDto, WorkflowStepDto } from './types';
import { StepMatchStatus } from './types';
import { SOURCE_LABELS } from '@/api/components/transformer';

const MATCH_STATUS_LABELS: Record<StepMatchStatus, string> = {
  [StepMatchStatus.SUGGESTED]: 'Suggested match — please confirm',
  [StepMatchStatus.CONFIRMED]: 'Confirmed',
  [StepMatchStatus.UNMATCHED]: 'Not matched',
  [StepMatchStatus.INLINE]: 'Runs inline',
};

export interface WorkflowStepDisplayModel extends WithHateoasLinks {
  id: string;
  stepId: string;
  runReference: string;
  stepOrder: number;
  componentId: string | null;
  componentName: string | null;
  componentVersion: number | null;
  component: ComponentSummaryDto | null;
  matchStatus: StepMatchStatus;
  matchStatusDisplay: string;
  matchScore: number | null;
}

/** A workflow - the composite - as the UI shows it in a list. */
export interface WorkflowDisplayModel extends ComponentDisplayModelBase {
  kind: typeof ComponentKind.WORKFLOW;
  stepCount: number;
  source: ComponentSource;
  sourceDisplay: string;
  /** the builder draft this came from, when it is still available */
  draftId: string | null;
}

export interface WorkflowDetailDisplayModel extends WorkflowDisplayModel, ComponentDetailFields {
  steps: WorkflowStepDisplayModel[];
}

export const workflowTransformer = {
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
      component: dto.component ?? null,
      matchStatus: dto.matchStatus,
      matchStatusDisplay: isManualPick ? 'Selected — please confirm' : MATCH_STATUS_LABELS[dto.matchStatus],
      matchScore: dto.matchScore,
      _links: dto._links,
    };
  },

  toDisplayModel(dto: WorkflowListItemDto): WorkflowDisplayModel {
    return {
      ...toDisplayModelBase(dto),
      kind: dto.kind,
      stepCount: dto.stepCount,
      source: dto.source,
      sourceDisplay: SOURCE_LABELS[dto.source],
      draftId: dto.draftId,
    };
  },

  toDetailDisplayModel(dto: WorkflowDetailDto): WorkflowDetailDisplayModel {
    return {
      ...toDisplayModelBase(dto),
      ...toDetailFields(dto),
      kind: dto.kind,
      stepCount: dto.steps.length,
      draftId: dto.draftId,
      steps: dto.steps.map(workflowTransformer.toStepDisplayModel),
    };
  },
};
