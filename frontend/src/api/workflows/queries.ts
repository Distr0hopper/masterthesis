import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toListDisplayModel, toSplitDisplayModel } from '@/api/helpers';
import { workflowsService } from './service';
import { workflowTransformer } from './transformer';
import { WorkflowCommand, WorkflowStepCommand } from './types';
import type { CreateWorkflowDto, WorkflowListQueryParams } from './types';
import { useCommandMutation } from '@/api/useCommandMutation';
import type { HateoasLink, MineQueryParams } from '@/api/types';

export const workflowKeys = {
  all: ['workflows'] as const,
  lists: (params: WorkflowListQueryParams) => [...workflowKeys.all, 'list', params] as const,
  mine: (params: MineQueryParams) => [...workflowKeys.all, 'mine', params] as const,
  latest: (limit?: number) => [...workflowKeys.all, 'latest', limit] as const,
  detail: (id: string) => [...workflowKeys.all, 'detail', id] as const,
};

export const useWorkflows = (params: WorkflowListQueryParams) => {
  return useQuery({
    queryKey: workflowKeys.lists(params),
    queryFn: () => workflowsService.getAll(params),
    select: (response) => toListDisplayModel(response, workflowTransformer.toListDisplayModels),
  });
};

export const useMyWorkflows = (params: MineQueryParams) => {
  return useQuery({
    queryKey: workflowKeys.mine(params),
    queryFn: () => workflowsService.getMine(params),
    select: (response) => toSplitDisplayModel(response, workflowTransformer.toListDisplayModels),
  });
};

export const useLatestWorkflows = (limit?: number) => {
  return useQuery({
    queryKey: workflowKeys.latest(limit),
    queryFn: () => workflowsService.getLatest(limit),
    select: (dtos) => workflowTransformer.toListDisplayModels(dtos),
  });
};

export const useWorkflow = (id: string) => {
  return useQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: () => workflowsService.getById(id),
    enabled: !!id,
    select: (dto) => workflowTransformer.toDetailDisplayModel(dto),
  });
};

export const useCreateWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, dto }: { file: File; dto: CreateWorkflowDto }) => workflowsService.create(file, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};

export const useUpdateWorkflowStepComponent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ link, componentId }: { link: HateoasLink; componentId: string | null }) =>
      workflowsService.updateStepComponent(link, componentId),
    onSuccess: () => {
      // a step change can un-confirm the workflow and hide it from the browse list again,
      // so invalidate broadly rather than just this workflow's detail view
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};

export const useConfirmWorkflowStep = () =>
  useCommandMutation(workflowKeys.all, (link: HateoasLink) =>
    workflowsService.executeStepCommand(link, { command: WorkflowStepCommand.CONFIRM }),
  );

export const usePublishWorkflow = () =>
  useCommandMutation(workflowKeys.all, (link: HateoasLink) =>
    workflowsService.executeCommand(link, { command: WorkflowCommand.PUBLISH }),
  );

export const useUnpublishWorkflow = () =>
  useCommandMutation(workflowKeys.all, (link: HateoasLink) =>
    workflowsService.executeCommand(link, { command: WorkflowCommand.UNPUBLISH }),
  );

export const useToggleWorkflowFavorite = () =>
  useCommandMutation(workflowKeys.all, ({ link, isFavorite }: { link: HateoasLink; isFavorite: boolean }) =>
    workflowsService.executeCommand(link, {
      command: isFavorite ? WorkflowCommand.REMOVE_FAVORITE : WorkflowCommand.ADD_FAVORITE,
    }),
  );

export const useUpdateWorkflowDescription = () =>
  useCommandMutation(workflowKeys.all, ({ link, description }: { link: HateoasLink; description: string | null }) =>
    workflowsService.executeCommand(link, { command: WorkflowCommand.UPDATE_DESCRIPTION, description }),
  );

export const useDownloadWorkflow = () => {
  return useMutation({
    mutationFn: (id: string) => workflowsService.download(id),
  });
};

export const useParseWorkflow = () => {
  return useMutation({
    mutationFn: (file: File) => workflowsService.parse(file),
  });
};

export const useDeleteWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (link: HateoasLink) => workflowsService.delete(link),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};
