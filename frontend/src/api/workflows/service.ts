import { apiClient } from '../client';
import type { HateoasLink, PageResponse } from '@/api/types';
import type {
  CreateWorkflowDto,
  MyWorkflowsQueryParams,
  MyWorkflowsResponseDto,
  ParseWorkflowResponseDto,
  WorkflowDetailDto,
  WorkflowListItemDto,
  WorkflowListQueryParams,
  WorkflowStepDto,
} from './types';

const ENDPOINT = '/workflows';

export const workflowsService = {
  getAll(params: WorkflowListQueryParams): Promise<PageResponse<WorkflowListItemDto>> {
    return apiClient.get(ENDPOINT, {
      params: { domain: params.domain, search: params.search || undefined, limit: params.limit, offset: params.offset },
    });
  },

  getById(id: string): Promise<WorkflowDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  getMine(params: MyWorkflowsQueryParams): Promise<MyWorkflowsResponseDto> {
    return apiClient.get(`${ENDPOINT}/mine`, {
      params: { limit: params.limit, publishedOffset: params.publishedOffset, pendingOffset: params.pendingOffset },
    });
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

  // detection/classification only - the backend never persists anything from this call.
  // Accepts either a .zip or a bare .cwl file; the server figures out which.
  parse(file: File): Promise<ParseWorkflowResponseDto> {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`${ENDPOINT}/parse`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  updateStepComponent(link: HateoasLink, componentId: string | null): Promise<WorkflowStepDto> {
    return apiClient.request(link, { componentId });
  },

  confirmStep(link: HateoasLink): Promise<WorkflowStepDto> {
    return apiClient.request(link, { command: 'CONFIRM' });
  },

  publish(link: HateoasLink): Promise<WorkflowDetailDto> {
    return apiClient.request(link, { command: 'PUBLISH' });
  },

  updateDescription(link: HateoasLink, description: string | null): Promise<WorkflowDetailDto> {
    return apiClient.request(link, { command: 'UPDATE_DESCRIPTION', description });
  },

  delete(link: HateoasLink): Promise<void> {
    return apiClient.request(link);
  },
};
