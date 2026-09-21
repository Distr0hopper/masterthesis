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
  nameAvailability: (name: string) => [...componentKeys.all, 'name-availability', name] as const,
};

/**
 * Whether `name` is still free for a new component lineage.
 *
 * Used while configuring an upload so a collision is resolved (rename, or reuse the
 * existing component) before anything is written - rather than surfacing as a 409 after
 * the whole file has been submitted. Callers are expected to debounce `name` themselves.
 */
export const useParseComponent = () => {
  return useMutation({ mutationFn: (file: File) => componentsService.parse(file) });
};

export const useComponentNameAvailability = (name: string) => {
  const trimmed = name.trim();
  return useQuery({
    queryKey: componentKeys.nameAvailability(trimmed),
    queryFn: () => componentsService.checkNameAvailability(trimmed),
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

export const useUnpublishComponent = () =>
  useCommandMutation(componentKeys.all, (link: HateoasLink) =>
    componentsService.executeCommand(link, { command: ComponentCommand.UNPUBLISH }),
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