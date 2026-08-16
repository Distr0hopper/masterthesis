import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { componentsService } from './service';
import { componentTransformer } from './transformer';
import type { AddVersionDto, ComponentDomain, CreateComponentDto, PackageComponentDto, UpdateComponentDto } from './types';
import type { HateoasLink } from '@/api/types';

export const componentKeys = {
  all: ['components'] as const,
  lists: (domain?: ComponentDomain, excludeMine?: boolean, favoritesOnly?: boolean) =>
    [...componentKeys.all, 'list', domain, excludeMine, favoritesOnly] as const,
  mine: () => [...componentKeys.all, 'mine'] as const,
  latest: (limit?: number) => [...componentKeys.all, 'latest', limit] as const,
  detail: (id: string) => [...componentKeys.all, 'detail', id] as const,
  versions: (id: string) => [...componentKeys.all, 'versions', id] as const,
  domains: () => ['domains'] as const,
};

export const useComponents = (domain?: ComponentDomain, excludeMine?: boolean, favoritesOnly?: boolean) => {
  return useQuery({
    queryKey: componentKeys.lists(domain, excludeMine, favoritesOnly),
    queryFn: () => componentsService.getAll(domain, excludeMine, favoritesOnly),
    select: (dtos) => componentTransformer.toListDisplayModels(dtos),
  });
};

export const useMyComponents = () => {
  return useQuery({
    queryKey: componentKeys.mine(),
    queryFn: () => componentsService.getMine(),
    select: (dtos) => componentTransformer.toListDisplayModels(dtos),
  });
};

export const useLatestComponents = (limit?: number) => {
  return useQuery({
    queryKey: componentKeys.latest(limit),
    queryFn: () => componentsService.getLatest(limit),
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

export const useUploadComponent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, dto }: { file: File; dto: CreateComponentDto }) =>
      componentsService.upload(file, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useAddManualVersion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, file, dto }: { id: string; file: File; dto: AddVersionDto }) =>
      componentsService.addManualVersion(id, file, dto),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
      queryClient.invalidateQueries({ queryKey: componentKeys.versions(variables.id) });
    },
  });
};

export const usePackageComponent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dto: PackageComponentDto) => componentsService.package(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useAddPackagedVersion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => componentsService.addPackagedVersion(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
      queryClient.invalidateQueries({ queryKey: componentKeys.versions(id) });
    },
  });
};

export const useUpdateComponent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ link, dto }: { link: HateoasLink; dto: UpdateComponentDto }) =>
      componentsService.update(link, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useDeleteComponent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (link: HateoasLink) => componentsService.delete(link),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useToggleFavorite = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (link: HateoasLink) => componentsService.toggleFavorite(link),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};