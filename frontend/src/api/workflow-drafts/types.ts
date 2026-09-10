export interface WorkflowDraftListItemDto {
  id: string;
  name: string;
  nodeCount: number;
  updatedAt: string;
  /** the Workflow this draft is synced to in My Workflows, or null if it was never synced */
  linkedWorkflowId: string | null;
}

export interface WorkflowDraftDetailDto {
  id: string;
  name: string;
  canvasState: string;
  nodeCount: number;
  updatedAt: string;
  createdAt: string;
  linkedWorkflowId: string | null;
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
}
