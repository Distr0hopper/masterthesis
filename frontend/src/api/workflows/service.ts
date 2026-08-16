import { apiClient } from '../client';
import type { HateoasLink } from '@/api/types';
import type { CreateWorkflowDto, WorkflowDetailDto, WorkflowListItemDto, WorkflowStepDto } from './types';

const ENDPOINT = '/workflows';

export const workflowsService = {
  getAll(domain?: string): Promise<WorkflowListItemDto[]> {
    return apiClient.get(ENDPOINT, { params: { domain } });
  },

  getById(id: string): Promise<WorkflowDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  getMine(): Promise<WorkflowListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/mine`);
  },

  getLatest(limit?: number): Promise<WorkflowListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/latest`, { params: { limit } });
  },

  download(id: string): Promise<{ blob: Blob; filename: string }> {
    return apiClient.getBlob(`${ENDPOINT}/${id}/download`, 'workflow.zip');
  },

  upload(file: File, dto: CreateWorkflowDto): Promise<WorkflowDetailDto> {
    const formData = new FormData();
    formData.append('zipFile', file);
    formData.append('name', dto.name);
    dto.domains.forEach((domain) => formData.append('domains', domain));
    if (dto.description) formData.append('description', dto.description);
    return apiClient.post(ENDPOINT, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  updateStepComponent(link: HateoasLink, componentId: string | null): Promise<WorkflowStepDto> {
    return apiClient.request(link, { componentId });
  },

  confirmStep(link: HateoasLink): Promise<WorkflowStepDto> {
    return apiClient.request(link);
  },

  publish(link: HateoasLink): Promise<WorkflowDetailDto> {
    return apiClient.request(link);
  },

  delete(link: HateoasLink): Promise<void> {
    return apiClient.request(link);
  },
};
