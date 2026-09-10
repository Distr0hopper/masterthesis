export interface WorkflowDraftListItemDto {
  id: string;
  name: string;
  nodeCount: number;
  updatedAt: string;
}

export interface WorkflowDraftDetailDto {
  id: string;
  name: string;
  canvasState: string;
  nodeCount: number;
  updatedAt: string;
  createdAt: string;
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
