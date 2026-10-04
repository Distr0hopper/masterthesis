import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toListDisplayModel, toSplitDisplayModel } from '@/api/helpers';
import { useCommandMutation } from '@/api/useCommandMutation';
import type { HateoasLink } from '@/api/types';
import { componentsService } from './service';
import { componentTransformer } from './variants';
import { ComponentCommand } from './types';
import type { ComponentKind, ComponentListQueryParams, MyComponentsQueryParams } from './types';

/** One cache root for both kinds - any mutation of either invalidates `componentKeys.all`. */
export const componentKeys = {
  all: ['components'] as const,
  lists: (params: ComponentListQueryParams) => [...componentKeys.all, 'list', params] as const,
  mine: (params: MyComponentsQueryParams) => [...componentKeys.all, 'mine', params] as const,
  latest: (limit?: number, kind?: ComponentKind) => [...componentKeys.all, 'latest', limit, kind ?? null] as const,
  detail: (id: string) => [...componentKeys.all, 'detail', id] as const,
  versions: (id: string) => [...componentKeys.all, 'versions', id] as const,
  usages: (id: string) => [...componentKeys.all, 'usages', id] as const,
  impact: (href: string) => [...componentKeys.all, 'impact', href] as const,
  domains: () => ['domains'] as const,
  nameAvailability: (name: string, excludeId?: string) =>
    [...componentKeys.all, 'name-availability', name, excludeId ?? null] as const,
};

/**
 * Whether `name` is still free for a new lineage - of either kind, names are one key.
 *
 * Used while configuring an upload so a collision is resolved (rename, or reuse the
 * existing component) before anything is written - rather than surfacing as a 409 after
 * the whole file has been submitted. Callers are expected to debounce `name` themselves.
 */
export const useComponentNameAvailability = (name: string, excludeId?: string) => {
  const trimmed = name.trim();
  return useQuery({
    queryKey: componentKeys.nameAvailability(trimmed, excludeId),
    queryFn: () => componentsService.checkNameAvailability(trimmed, excludeId),
    enabled: trimmed.length > 0,
    staleTime: 30_000,
  });
};

export const useComponents = (params: ComponentListQueryParams) => {
  return useQuery({
    queryKey: componentKeys.lists(params),
    queryFn: () => componentsService.getAll(params),
    select: (response) => toListDisplayModel(response, componentTransformer.toListDisplayModels),
  });
};

/**
 * The component list one page at a time, pages accumulating as `fetchNextPage` is called -
 * for the builder palette, which scrolls rather than pages. `limit` is the page size.
 */
export const useInfiniteComponents = (params: Omit<ComponentListQueryParams, 'offset'> & { limit: number }) => {
  return useInfiniteQuery({
    queryKey: [...componentKeys.all, 'infinite', params] as const,
    queryFn: ({ pageParam }) => componentsService.getAll({ ...params, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.limit;
      return next < last.totalElements ? next : undefined;
    },
    select: (data) => ({
      items: data.pages.flatMap((page) => componentTransformer.toListDisplayModels(page.content)),
      total: data.pages[0]?.totalElements ?? 0,
    }),
    // a changed filter or canvas (rankAgainst) starts a new list - keep the old one shown
    // until it arrives instead of flashing "Loading..."
    placeholderData: keepPreviousData,
  });
};

export const useMyComponents = (params: MyComponentsQueryParams) => {
  return useQuery({
    queryKey: componentKeys.mine(params),
    queryFn: () => componentsService.getMine(params),
    select: (response) => toSplitDisplayModel(response, componentTransformer.toListDisplayModels),
  });
};

export const useLatestComponents = (limit?: number, kind?: ComponentKind) => {
  return useQuery({
    queryKey: componentKeys.latest(limit, kind),
    queryFn: () => componentsService.getLatest(limit, kind),
    select: (dtos) => componentTransformer.toListDisplayModels(dtos),
  });
};

export const useComponent = (id: string) => {
  return useQuery({
    queryKey: componentKeys.detail(id),
    queryFn: () => componentsService.getById(id),
    enabled: !!id,
    select: (dto) => componentTransformer.toDetailDisplayModel(dto),
  });
};

/** The workflows running this component - its parents in the composite. */
export const useComponentUsages = (id: string) => {
  return useQuery({
    queryKey: componentKeys.usages(id),
    queryFn: () => componentsService.getUsages(id),
    enabled: !!id,
  });
};

/** What unpublishing or deleting this version touches - fetched when either dialog opens. */
export const useComponentImpact = (link: HateoasLink | undefined, enabled: boolean) => {
  return useQuery({
    queryKey: componentKeys.impact(link?.href ?? ''),
    queryFn: () => componentsService.getImpact(link!),
    enabled: enabled && !!link,
    // usages change whenever someone edits a workflow - never trust a stale answer here
    staleTime: 0,
  });
};

export const useComponentVersions = (id: string) => {
  return useQuery({
    queryKey: componentKeys.versions(id),
    queryFn: () => componentsService.getVersions(id),
    enabled: !!id,
    select: (dtos) => componentTransformer.toListDisplayModels(dtos),
  });
};

export const useDomains = () => {
  return useQuery({
    queryKey: componentKeys.domains(),
    queryFn: () => componentsService.getDomains(),
    staleTime: 60 * 60 * 1000,
  });
};

export interface DeleteComponentVariables {
  link: HateoasLink;
  /** workflows only - also delete the builder canvas it was synced from */
  deleteLinkedDraft?: boolean;
  /** also unpublish your own public workflows that run this version */
  unpublishParents?: boolean;
}

export const useDeleteComponent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ link, deleteLinkedDraft = false, unpublishParents = false }: DeleteComponentVariables) =>
      componentsService.delete(link, deleteLinkedDraft, unpublishParents),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useDownloadComponent = () => {
  return useMutation({ mutationFn: (id: string) => componentsService.download(id) });
};

export const usePublishComponent = () =>
  useCommandMutation(
    componentKeys.all,
    ({ link, publishComponents }: { link: HateoasLink; publishComponents?: boolean }) =>
      componentsService.executeCommand(link, { command: ComponentCommand.PUBLISH, publishComponents }),
  );

export const useUnpublishComponent = () =>
  useCommandMutation(componentKeys.all, ({ link, unpublishParents }: { link: HateoasLink; unpublishParents: boolean }) =>
    componentsService.executeCommand(link, { command: ComponentCommand.UNPUBLISH, unpublishParents }),
  );

export const useDeprecateComponent = () =>
  useCommandMutation(componentKeys.all, ({ link, deprecationNote }: { link: HateoasLink; deprecationNote: string | null }) =>
    componentsService.executeCommand(link, { command: ComponentCommand.DEPRECATE, deprecationNote }),
  );

export const useUndeprecateComponent = () =>
  useCommandMutation(componentKeys.all, (link: HateoasLink) =>
    componentsService.executeCommand(link, { command: ComponentCommand.UNDEPRECATE }),
  );

export const useUpdateComponentDescription = () =>
  useCommandMutation(componentKeys.all, ({ link, description }: { link: HateoasLink; description: string | null }) =>
    componentsService.executeCommand(link, { command: ComponentCommand.UPDATE_DESCRIPTION, description }),
  );

export const useUpdateComponentDomains = () =>
  useCommandMutation(componentKeys.all, ({ link, domains }: { link: HateoasLink; domains: string[] }) =>
    componentsService.executeCommand(link, { command: ComponentCommand.UPDATE_DOMAIN, domains }),
  );

export const useToggleFavorite = () =>
  useCommandMutation(componentKeys.all, ({ link, isFavorite }: { link: HateoasLink; isFavorite: boolean }) =>
    componentsService.executeCommand(link, {
      command: isFavorite ? ComponentCommand.REMOVE_FAVORITE : ComponentCommand.ADD_FAVORITE,
    }),
  );
