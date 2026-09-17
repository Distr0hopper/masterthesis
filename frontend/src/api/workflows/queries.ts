import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toListDisplayModel } from '@/api/helpers';
import { workflowsService } from './service';
import { workflowTransformer } from './transformer';
import type { CreateWorkflowDto, MyWorkflowsQueryParams, WorkflowListQueryParams } from './types';
import type { HateoasLink } from '@/api/types';

export const workflowKeys = {
  all: ['workflows'] as const,
  lists: (params: WorkflowListQueryParams) => [...workflowKeys.all, 'list', params] as const,
  mine: (params: MyWorkflowsQueryParams) => [...workflowKeys.all, 'mine', params] as const,
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

export const useMyWorkflows = (params: MyWorkflowsQueryParams) => {
  return useQuery({
    queryKey: workflowKeys.mine(params),
    queryFn: () => workflowsService.getMine(params),
    select: (response) => ({
      published: toListDisplayModel(response.published, workflowTransformer.toListDisplayModels),
      pending: toListDisplayModel(response.pending, workflowTransformer.toListDisplayModels),
    }),
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

export const useUploadWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, dto }: { file: File; dto: CreateWorkflowDto }) => workflowsService.upload(file, dto),
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

export const useConfirmWorkflowStep = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (link: HateoasLink) => workflowsService.confirmStep(link),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};

export const usePublishWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (link: HateoasLink) => workflowsService.publish(link),
    onSuccess: () => {
      // publishing makes the workflow appear in the public browse list
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};

export const useUpdateWorkflowDescription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ link, description }: { link: HateoasLink; description: string | null }) =>
      workflowsService.updateDescription(link, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};

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
