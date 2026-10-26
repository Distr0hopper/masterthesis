import type { ComponentStatus } from '@/api/components';

/** The newest version Save synced into My Components - the next Save works on it. */
export interface LinkedWorkflowDto {
  id: string;
  version: number;
  status: ComponentStatus;
  /** a version of its lineage is public, so the name is fixed - a renamed canvas would be refused on Save */
  nameLocked: boolean;
}

export interface WorkflowDraftListItemDto {
  id: string;
  name: string;
  nodeCount: number;
  updatedAt: string;
  linkedWorkflow: LinkedWorkflowDto | null;
}

export interface WorkflowDraftDetailDto {
  id: string;
  name: string;
  canvasState: string;
  nodeCount: number;
  updatedAt: string;
  createdAt: string;
  linkedWorkflow: LinkedWorkflowDto | null;
  /** componentIds on the canvas whose component has since been deleted */
  missingComponentIds: string[];
}

export interface WriteWorkflowDraftDto {
  name: string;
  canvasState: string;
  nodeCount: number;
}

export interface SyncedWorkflowDto {
  workflowId: string;
  name: string;
  stepCount: number;
  version: number;
  status: ComponentStatus;
}
