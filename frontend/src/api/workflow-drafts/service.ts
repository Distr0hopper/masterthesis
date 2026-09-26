import { apiClient } from '../client';
import type {
  SyncedWorkflowDto,
  WorkflowDraftDetailDto,
  WorkflowDraftListItemDto,
  WriteWorkflowDraftDto,
} from './types';

const ENDPOINT = '/workflow-drafts';

export const workflowDraftsService = {
  getAll(): Promise<WorkflowDraftListItemDto[]> {
    return apiClient.get(ENDPOINT);
  },

  getById(id: string): Promise<WorkflowDraftDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  create(dto: WriteWorkflowDraftDto): Promise<WorkflowDraftDetailDto> {
    return apiClient.post(ENDPOINT, dto);
  },

  // PUT, not PATCH - full replacement semantics
  update(id: string, dto: WriteWorkflowDraftDto): Promise<WorkflowDraftDetailDto> {
    return apiClient.put(`${ENDPOINT}/${id}`, dto);
  },

  // deleteLinkedWorkflow: also drop the Workflow this draft was synced to in My Workflows
  delete(id: string, deleteLinkedWorkflow = false): Promise<void> {
    const query = deleteLinkedWorkflow ? '?deleteLinkedWorkflow=true' : '';
    return apiClient.delete(`${ENDPOINT}/${id}${query}`);
  },

  // getBlob, not a window.location navigation: the endpoint needs the Authorization
  // header, and this keeps the JWT out of the URL (and so out of history and access logs)
  exportZip(id: string): Promise<{ blob: Blob; filename: string }> {
    return apiClient.getBlob(`${ENDPOINT}/${id}/export`, 'workflow.zip');
  },

  /** The job file (inputs.yaml) matching the workflow exportZip produces. */
  exportInputs(id: string): Promise<{ blob: Blob; filename: string }> {
    return apiClient.getBlob(`${ENDPOINT}/${id}/export/inputs`, 'inputs.yaml');
  },

  // materialises the canvas as a Workflow row in My Workflows (idempotent per draft).
  syncToMyWorkflows(id: string): Promise<SyncedWorkflowDto> {
    return apiClient.post(`${ENDPOINT}/${id}/sync`);
  },
};
