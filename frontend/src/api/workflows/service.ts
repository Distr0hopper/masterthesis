import { apiClient } from '../client';
import type { HateoasLink } from '@/api/types';
import type {
  AddWorkflowVersionDto,
  CreateWorkflowDto,
  ParseWorkflowResponseDto,
  WorkflowDetailDto,
  WorkflowStepCommandExecuteRequest,
  WorkflowStepDto,
} from './types';

const ENDPOINT = '/workflows';

/** What only a workflow has - listing, reading and the shared commands go through componentsService. */
export const workflowsService = {
  create(file: File, dto: CreateWorkflowDto): Promise<WorkflowDetailDto> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', dto.name);
    dto.domains.forEach((domain) => formData.append('domains', domain));
    if (dto.description) formData.append('description', dto.description);
    formData.append('componentConfigs', JSON.stringify(dto.componentConfigs));
    return apiClient.post(ENDPOINT, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  addVersion(id: string, file: File, dto: AddWorkflowVersionDto): Promise<WorkflowDetailDto> {
    const formData = new FormData();
    formData.append('file', file);
    if (dto.description) formData.append('description', dto.description);
    formData.append('componentConfigs', JSON.stringify(dto.componentConfigs));
    return apiClient.post(`${ENDPOINT}/${id}/versions`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  /** parentId: the workflow the upload is to become the next version of - steps then report `previous` */
  parse(file: File, parentId?: string): Promise<ParseWorkflowResponseDto> {
    const formData = new FormData();
    formData.append('file', file);
    if (parentId) formData.append('parentId', parentId);
    return apiClient.post(`${ENDPOINT}/parse`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  /** componentId: a tool, or another workflow to nest - null clears the match */
  updateStepComponent(link: HateoasLink, componentId: string | null): Promise<WorkflowStepDto> {
    return apiClient.request(link, { componentId });
  },

  executeStepCommand(link: HateoasLink, request: WorkflowStepCommandExecuteRequest): Promise<WorkflowStepDto> {
    return apiClient.request(link, request);
  },
};
