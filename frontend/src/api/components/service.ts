import { apiClient } from '../client';
import type { HateoasLink } from '@/api/types';
import type {
  AddVersionDto,
  ComponentDetailDto,
  ComponentDomain,
  ComponentListItemDto,
  CreateComponentDto,
  DomainDto,
  PackageComponentDto,
  UpdateComponentDto,
} from './types';

const ENDPOINT = '/components';

export const componentsService = {
  getAll(domain?: ComponentDomain, excludeMine?: boolean, favoritesOnly?: boolean): Promise<ComponentListItemDto[]> {
    return apiClient.get(ENDPOINT, {
      params: { domain, excludeMine: excludeMine || undefined, favoritesOnly: favoritesOnly || undefined },
    });
  },

  getMine(): Promise<ComponentListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/mine`);
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
    formData.append('domain', dto.domain);
    if (dto.authorName) formData.append('authorName', dto.authorName);
    if (dto.description) formData.append('description', dto.description);
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

  update(link: HateoasLink, dto: UpdateComponentDto): Promise<ComponentDetailDto> {
    return apiClient.request(link, dto);
  },

  delete(link: HateoasLink): Promise<void> {
    return apiClient.request(link);
  },

  getDomains(): Promise<DomainDto[]> {
    return apiClient.get('/domains');
  },

  toggleFavorite(link: HateoasLink, isFavorite: boolean): Promise<void> {
    return apiClient.request(link, { command: isFavorite ? 'REMOVE_FAVORITE' : 'ADD_FAVORITE' });
  },
};