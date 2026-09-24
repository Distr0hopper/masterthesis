import { apiClient } from '../client';
import type { HateoasLink, MineQueryParams, PageResponse } from '@/api/types';
import type {
  AddVersionDto,
  ComponentCommandExecuteRequest,
  ComponentDetailDto,
  ComponentListItemDto,
  ComponentListQueryParams,
  ComponentPreviewDto,
  CreateComponentDto,
  DomainDto,
  MyComponentsResponseDto,
  NameAvailabilityDto,
  PackageComponentDto,
} from './types';

const ENDPOINT = '/components';

export const componentsService = {
  getAll(params: ComponentListQueryParams): Promise<PageResponse<ComponentListItemDto>> {
    return apiClient.get(ENDPOINT, {
      params: {
        domain: params.domain?.length ? params.domain : undefined,
        excludeMine: params.excludeMine || undefined,
        favoritesOnly: params.favoritesOnly || undefined,
        search: params.search || undefined,
        includeParameters: params.includeParameters || undefined,
        rankAgainst: params.rankAgainst?.length ? params.rankAgainst : undefined,
        limit: params.limit,
        offset: params.offset,
      },
    });
  },

  getMine(params: MineQueryParams): Promise<MyComponentsResponseDto> {
    return apiClient.get(`${ENDPOINT}/mine`, {
      params: {
        limit: params.limit,
        publishedOffset: params.publishedOffset,
        unpublishedOffset: params.unpublishedOffset,
      },
    });
  },

  getLatest(limit?: number): Promise<ComponentListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/latest`, { params: { limit } });
  },

  getById(id: string): Promise<ComponentDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  getVersions(id: string): Promise<ComponentListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/${id}/versions`);
  },

  getDownloadUrl(id: string): string {
    return `${apiClient.baseURL}${ENDPOINT}/${id}/download`;
  },

  getBundleUrl(id: string): string {
    return `${apiClient.baseURL}${ENDPOINT}/${id}/bundle`;
  },

  upload(file: File, dto: CreateComponentDto): Promise<ComponentDetailDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    formData.append('name', dto.name);
    dto.domains.forEach((domain) => formData.append('domains', domain));
    if (dto.authorName) formData.append('authorName', dto.authorName);
    if (dto.description) formData.append('description', dto.description);
    if (dto.formatLabels?.length) formData.append('formatLabels', JSON.stringify(dto.formatLabels));
    return apiClient.post(ENDPOINT, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  addManualVersion(id: string, file: File, dto: AddVersionDto): Promise<ComponentDetailDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    if (dto.repoCommitSha) formData.append('repoCommitSha', dto.repoCommitSha);
    if (dto.description) formData.append('description', dto.description);
    return apiClient.post(`${ENDPOINT}/${id}/versions`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  package(dto: PackageComponentDto): Promise<ComponentDetailDto> {
    return apiClient.post(`${ENDPOINT}/package`, dto);
  },

  delete(link: HateoasLink): Promise<void> {
    return apiClient.request(link);
  },

  // detection/parsing only - the backend never persists anything from this call
  parse(file: File): Promise<ComponentPreviewDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    return apiClient.post(`${ENDPOINT}/parse`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  checkNameAvailability(name: string): Promise<NameAvailabilityDto> {
    return apiClient.get(`${ENDPOINT}/name-availability`, { params: { name } });
  },

  getDomains(): Promise<DomainDto[]> {
    return apiClient.get('/domains');
  },

  executeCommand(link: HateoasLink, request: ComponentCommandExecuteRequest): Promise<ComponentDetailDto> {
    return apiClient.request(link, request);
  },
};