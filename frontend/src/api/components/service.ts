import { apiClient } from '../client';
import type {
  AddVersionDto,
  ComponentDetailDto,
  ComponentDomain,
  ComponentListItemDto,
  CreateComponentDto,
  PackageComponentDto,
  UpdateComponentDto,
} from './types';

const ENDPOINT = '/components';

export const componentsService = {
  getAll(domain?: ComponentDomain): Promise<ComponentListItemDto[]> {
    return apiClient
      .get(ENDPOINT, { params: domain ? { domain } : undefined })
      .then((res) => res.data);
  },

  getById(id: string): Promise<ComponentDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`).then((res) => res.data);
  },

  getVersions(id: string): Promise<ComponentListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/${id}/versions`).then((res) => res.data);
  },

  getDownloadUrl(id: string): string {
    return `${apiClient.defaults.baseURL}${ENDPOINT}/${id}/download`;
  },

  getBundleUrl(id: string): string {
    return `${apiClient.defaults.baseURL}${ENDPOINT}/${id}/bundle`;
  },

  upload(file: File, dto: CreateComponentDto): Promise<ComponentDetailDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    formData.append('name', dto.name);
    formData.append('domain', dto.domain);
    if (dto.authorName) formData.append('authorName', dto.authorName);
    if (dto.description) formData.append('description', dto.description);
    return apiClient
      .post(ENDPOINT, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((res) => res.data);
  },

  addManualVersion(id: string, file: File, dto: AddVersionDto): Promise<ComponentDetailDto> {
    const formData = new FormData();
    formData.append('cwlFile', file);
    if (dto.repoCommitSha) formData.append('repoCommitSha', dto.repoCommitSha);
    if (dto.description) formData.append('description', dto.description);
    return apiClient
      .post(`${ENDPOINT}/${id}/versions`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((res) => res.data);
  },

  package(dto: PackageComponentDto): Promise<ComponentDetailDto> {
    return apiClient.post(`${ENDPOINT}/package`, dto).then((res) => res.data);
  },

  addPackagedVersion(id: string): Promise<ComponentDetailDto> {
    return apiClient.post(`${ENDPOINT}/${id}/versions/package`).then((res) => res.data);
  },

  update(id: string, dto: UpdateComponentDto): Promise<ComponentDetailDto> {
    return apiClient.patch(`${ENDPOINT}/${id}`, dto).then((res) => res.data);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`${ENDPOINT}/${id}`).then((res) => res.data);
  },

  getDomains(): Promise<string[]> {
    return apiClient.get('/domains').then((res) => res.data);
  },
};