import { apiClient } from './client';
import type { ComponentDetail, ComponentDomain, ComponentListItem } from '@/types/api.types';

export const componentsApi = {
  list: (domain?: ComponentDomain) =>
    apiClient.get<ComponentListItem[]>('/components', {
      params: domain ? { domain } : undefined,
    }),

  getById: (id: string) =>
    apiClient.get<ComponentDetail>(`/components/${id}`),

  package: (repoUrl: string, domain: ComponentDomain) =>
    apiClient.post<ComponentDetail>('/components/package', { repoUrl, domain }),

  upload: (file: File, name: string, domain: ComponentDomain) => {
    const formData = new FormData();
    formData.append('cwlFile', file);
    formData.append('name', name);
    formData.append('domain', domain);
    return apiClient.post<ComponentDetail>('/components', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (id: string) =>
    apiClient.delete(`/components/${id}`),
};
