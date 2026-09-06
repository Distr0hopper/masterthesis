export interface WorkflowDraftListItemDto {
  id: string;
  name: string;
  nodeCount: number;
  updatedAt: string;
}

export interface WorkflowDraftDetailDto {
  id: string;
  name: string;
  /** raw JSON string holding the React Flow canvas - parse before use */
  canvasState: string;
  nodeCount: number;
  updatedAt: string;
  createdAt: string;
}

/** Create and update share a body: the editor always sends its complete canvas. */
export interface WriteWorkflowDraftDto {
  name: string;
  canvasState: string;
  nodeCount: number;
}

export interface PublishedWorkflowDto {
  workflowId: string;
  name: string;
  stepCount: number;
}
