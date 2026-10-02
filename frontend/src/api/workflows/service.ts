import { apiClient } from '../client';
import type { HateoasLink } from '@/api/types';
import type {
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

  parse(file: File): Promise<ParseWorkflowResponseDto> {
    const formData = new FormData();
    formData.append('file', file);
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
