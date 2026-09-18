import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toListDisplayModel, toSplitDisplayModel } from '@/api/helpers';
import { componentsService } from './service';
import { componentTransformer } from './transformer';
import { ComponentCommand } from './types';
import type {
  AddVersionDto,
  ComponentListQueryParams,
  CreateComponentDto,
  PackageComponentDto,
  UpdateComponentDto,
} from './types';
import { useCommandMutation } from '@/api/useCommandMutation';
import type { HateoasLink, MineQueryParams } from '@/api/types';

export const componentKeys = {
  all: ['components'] as const,
  lists: (params: ComponentListQueryParams) => [...componentKeys.all, 'list', params] as const,
  mine: (params: MineQueryParams) => [...componentKeys.all, 'mine', params] as const,
  latest: (limit?: number) => [...componentKeys.all, 'latest', limit] as const,
  detail: (id: string) => [...componentKeys.all, 'detail', id] as const,
  versions: (id: string) => [...componentKeys.all, 'versions', id] as const,
  domains: () => ['domains'] as const,
};

export const useComponents = (params: ComponentListQueryParams) => {
  return useQuery({
    queryKey: componentKeys.lists(params),
    queryFn: () => componentsService.getAll(params),
    select: (response) => toListDisplayModel(response, componentTransformer.toListDisplayModels),
  });
};

export const useMyComponents = (params: MineQueryParams) => {
  return useQuery({
    queryKey: componentKeys.mine(params),
    queryFn: () => componentsService.getMine(params),
    select: (response) => toSplitDisplayModel(response, componentTransformer.toListDisplayModels),
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


export const usePublishComponent = () =>
  useCommandMutation(componentKeys.all, (link: HateoasLink) =>
    componentsService.executeCommand(link, { command: ComponentCommand.PUBLISH }),
  );

export const useToggleFavorite = () =>
  useCommandMutation(componentKeys.all, ({ link, isFavorite }: { link: HateoasLink; isFavorite: boolean }) =>
    componentsService.executeCommand(link, {
      command: isFavorite ? ComponentCommand.REMOVE_FAVORITE : ComponentCommand.ADD_FAVORITE,
    }),
  );