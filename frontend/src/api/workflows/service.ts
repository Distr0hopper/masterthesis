import { apiClient } from '../client';
import type { CreateWorkflowDto, WorkflowDetailDto, WorkflowListItemDto, WorkflowStepDto } from './types';

const ENDPOINT = '/workflows';

export const workflowsService = {
  getAll(domain?: string): Promise<WorkflowListItemDto[]> {
    return apiClient.get(ENDPOINT, { params: { domain } });
  },

  getById(id: string): Promise<WorkflowDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  getDownloadUrl(id: string): string {
    return `${apiClient.baseURL}${ENDPOINT}/${id}/download`;
  },

  upload(file: File, dto: CreateWorkflowDto): Promise<WorkflowDetailDto> {
    const formData = new FormData();
    formData.append('zipFile', file);
    formData.append('name', dto.name);
    dto.domains.forEach((domain) => formData.append('domains', domain));
    if (dto.description) formData.append('description', dto.description);
    return apiClient.post(ENDPOINT, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  updateStepComponent(stepId: string, componentId: string | null): Promise<WorkflowStepDto> {
    return apiClient.patch(`${ENDPOINT}/steps/${stepId}`, { componentId });
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`${ENDPOINT}/${id}`);
  },
};
