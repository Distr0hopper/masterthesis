import { apiClient } from '../client';
import type {
  PublishedWorkflowDto,
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

  delete(id: string): Promise<void> {
    return apiClient.delete(`${ENDPOINT}/${id}`);
  },

  // getBlob, not a window.location navigation: the endpoint needs the Authorization
  // header, and this keeps the JWT out of the URL (and so out of history and access logs)
  exportZip(id: string): Promise<{ blob: Blob; filename: string }> {
    return apiClient.getBlob(`${ENDPOINT}/${id}/export`, 'workflow.zip');
  },

  // separate from export: this is the call that creates a Workflow row
  publish(id: string): Promise<PublishedWorkflowDto> {
    return apiClient.post(`${ENDPOINT}/${id}/publish`);
  },
};
