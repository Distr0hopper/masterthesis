import { apiClient } from '../client';
import type {
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
};
