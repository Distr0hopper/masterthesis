import { apiClient } from '../client';
import type { HateoasLink, MineQueryParams, PageResponse } from '@/api/types';
import type {
  CreateWorkflowDto,
  MyWorkflowsResponseDto,
  ParseWorkflowResponseDto,
  WorkflowDetailDto,
  WorkflowListItemDto,
  WorkflowListQueryParams,
  WorkflowCommandExecuteRequest,
  WorkflowStepCommandExecuteRequest,
  WorkflowStepDto,
} from './types';

const ENDPOINT = '/workflows';

export const workflowsService = {
  getAll(params: WorkflowListQueryParams): Promise<PageResponse<WorkflowListItemDto>> {
    return apiClient.get(ENDPOINT, {
      params: {
        domain: params.domain?.length ? params.domain : undefined,
        search: params.search || undefined,
        favoritesOnly: params.favoritesOnly || undefined,
        limit: params.limit,
        offset: params.offset,
      },
    });
  },

  getById(id: string): Promise<WorkflowDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  getMine(params: MineQueryParams): Promise<MyWorkflowsResponseDto> {
    return apiClient.get(`${ENDPOINT}/mine`, {
      params: {
        limit: params.limit,
        publishedOffset: params.publishedOffset,
        unpublishedOffset: params.unpublishedOffset,
      },
    });
  },

  getLatest(limit?: number): Promise<WorkflowListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/latest`, { params: { limit } });
  },

  download(id: string): Promise<{ blob: Blob; filename: string }> {
    return apiClient.getBlob(`${ENDPOINT}/${id}/download`, 'workflow.zip');
  },

  create(file: File, dto: CreateWorkflowDto): Promise<WorkflowDetailDto> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', dto.name);
    dto.domains.forEach((domain) => formData.append('domains', domain));
    if (dto.description) formData.append('description', dto.description);
    // one form field carrying the whole JSON array - matches the backend's Json[...] field
    formData.append('componentConfigs', JSON.stringify(dto.componentConfigs));
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

  executeCommand(link: HateoasLink, request: WorkflowCommandExecuteRequest): Promise<WorkflowDetailDto> {
    return apiClient.request(link, request);
  },

  executeStepCommand(link: HateoasLink, request: WorkflowStepCommandExecuteRequest): Promise<WorkflowStepDto> {
    return apiClient.request(link, request);
  },

  delete(link: HateoasLink): Promise<void> {
    return apiClient.request(link);
  },
};
