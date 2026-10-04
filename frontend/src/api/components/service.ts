import { apiClient } from '../client';
import type { HateoasLink, PageResponse } from '@/api/types';
import type {
  ComponentCommandExecuteRequest,
  ComponentImpactDto,
  ComponentDetailDto,
  ComponentKind,
  ComponentListItemDto,
  ComponentListQueryParams,
  ComponentUsageDto,
  DomainDto,
  MyComponentsQueryParams,
  MyComponentsResponseDto,
  NameAvailabilityDto,
} from './types';

const ENDPOINT = '/components';

/** Everything that works the same for a tool and a workflow - the composite's uniform API. */
export const componentsService = {
  getAll(params: ComponentListQueryParams): Promise<PageResponse<ComponentListItemDto>> {
    return apiClient.get(ENDPOINT, {
      params: {
        kind: params.kind,
        domain: params.domain?.length ? params.domain : undefined,
        excludeMine: params.excludeMine || undefined,
        favoritesOnly: params.favoritesOnly || undefined,
        search: params.search || undefined,
        includeParameters: params.includeParameters || undefined,
        rankAgainst: params.rankAgainst?.length ? params.rankAgainst : undefined,
        favoritesFirst: params.favoritesFirst || undefined,
        limit: params.limit,
        offset: params.offset,
      },
    });
  },

  getMine(params: MyComponentsQueryParams): Promise<MyComponentsResponseDto> {
    return apiClient.get(`${ENDPOINT}/mine`, {
      params: {
        kind: params.kind,
        limit: params.limit,
        publishedOffset: params.publishedOffset,
        unpublishedOffset: params.unpublishedOffset,
      },
    });
  },

  getLatest(limit?: number, kind?: ComponentKind): Promise<ComponentListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/latest`, { params: { limit, kind } });
  },

  getById(id: string): Promise<ComponentDetailDto> {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  getVersions(id: string): Promise<ComponentListItemDto[]> {
    return apiClient.get(`${ENDPOINT}/${id}/versions`);
  },

  /** The workflows running this component - a tool, or a nested workflow. */
  getUsages(id: string): Promise<ComponentUsageDto[]> {
    return apiClient.get(`${ENDPOINT}/${id}/usages`);
  },

  getDownloadUrl(id: string): string {
    return `${apiClient.baseURL}${ENDPOINT}/${id}/download`;
  },

  // getBlob, not a plain link: a draft is only downloadable with the Authorization header
  download(id: string): Promise<{ blob: Blob; filename: string }> {
    return apiClient.getBlob(`${ENDPOINT}/${id}/download`, 'component');
  },

  getImpact(link: HateoasLink): Promise<ComponentImpactDto> {
    return apiClient.request(link);
  },

  /**
   * deleteLinkedDraft: workflows only - also delete the builder canvas it was synced from.
   * unpublishParents: also unpublish your own public workflows that run this version.
   */
  delete(link: HateoasLink, deleteLinkedDraft = false, unpublishParents = false): Promise<void> {
    const params = {
      ...(deleteLinkedDraft ? { deleteLinkedDraft: true } : {}),
      ...(unpublishParents ? { unpublishParents: true } : {}),
    };
    return apiClient.request(link, undefined, { params: Object.keys(params).length ? params : undefined });
  },

  /** excludeId: a component trivially holds its own name - leave its lineage out of the check */
  checkNameAvailability(name: string, excludeId?: string): Promise<NameAvailabilityDto> {
    return apiClient.get(`${ENDPOINT}/name-availability`, { params: { name, excludeId } });
  },

  getDomains(): Promise<DomainDto[]> {
    return apiClient.get('/domains');
  },

  executeCommand(link: HateoasLink, request: ComponentCommandExecuteRequest): Promise<ComponentDetailDto> {
    return apiClient.request(link, request);
  },
};
