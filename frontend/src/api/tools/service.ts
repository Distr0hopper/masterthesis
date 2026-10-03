import { apiClient } from '../client';
import type { HateoasLink } from '@/api/types';
import type {
  AddVersionDto,
  CreateToolDto,
  PackagePreviewDto,
  PackageToolDto,
  ToolCommandExecuteRequest,
  ToolDetailDto,
  ToolPreviewDto,
} from './types';

const ENDPOINT = '/tools';

/** What only a tool has - listing, reading and the shared commands go through componentsService. */
export const toolsService = {
  getBundleUrl(id: string): string {
    return `${apiClient.baseURL}${ENDPOINT}/${id}/bundle`;
  },

  upload(file: File, dto: CreateToolDto): Promise<ToolDetailDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    formData.append('name', dto.name);
    dto.domains.forEach((domain) => formData.append('domains', domain));
    if (dto.authorName) formData.append('authorName', dto.authorName);
    if (dto.description) formData.append('description', dto.description);
    if (dto.formatLabels?.length) formData.append('formatLabels', JSON.stringify(dto.formatLabels));
    return apiClient.post(ENDPOINT, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  addManualVersion(id: string, file: File, dto: AddVersionDto): Promise<ToolDetailDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    if (dto.repoCommitSha) formData.append('repoCommitSha', dto.repoCommitSha);
    if (dto.description) formData.append('description', dto.description);
    return apiClient.post(`${ENDPOINT}/${id}/versions`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  package(dto: PackageToolDto): Promise<ToolDetailDto> {
    return apiClient.post(`${ENDPOINT}/package`, dto);
  },

  // detection/parsing only - the backend never persists anything from this call
  parse(file: File): Promise<ToolPreviewDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    return apiClient.post(`${ENDPOINT}/parse`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  // packages the repo but persists nothing - the GitHub counterpart of parse()
  packagePreview(repoUrl: string): Promise<PackagePreviewDto> {
    return apiClient.post(`${ENDPOINT}/package/preview`, { repoUrl });
  },

  executeCommand(link: HateoasLink, request: ToolCommandExecuteRequest): Promise<ToolDetailDto> {
    return apiClient.request(link, request);
  },
};
