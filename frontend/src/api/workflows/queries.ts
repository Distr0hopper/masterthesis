import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { workflowsService } from './service';
import { workflowTransformer } from './transformer';
import type { CreateWorkflowDto } from './types';

export const workflowKeys = {
  all: ['workflows'] as const,
  lists: (domain?: string) => [...workflowKeys.all, 'list', domain] as const,
  mine: () => [...workflowKeys.all, 'mine'] as const,
  latest: (limit?: number) => [...workflowKeys.all, 'latest', limit] as const,
  detail: (id: string) => [...workflowKeys.all, 'detail', id] as const,
};

export const useWorkflows = (domain?: string) => {
  return useQuery({
    queryKey: workflowKeys.lists(domain),
    queryFn: () => workflowsService.getAll(domain),
    select: (dtos) => workflowTransformer.toListDisplayModels(dtos),
  });
};

export const useMyWorkflows = () => {
  return useQuery({
    queryKey: workflowKeys.mine(),
    queryFn: () => workflowsService.getMine(),
    select: (dtos) => workflowTransformer.toListDisplayModels(dtos),
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
    mutationFn: ({ stepId, componentId }: { stepId: string; componentId: string | null; workflowId: string }) =>
      workflowsService.updateStepComponent(stepId, componentId),
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
    mutationFn: ({ stepId }: { stepId: string; workflowId: string }) => workflowsService.confirmStep(stepId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};

export const usePublishWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workflowsService.publish(id),
    onSuccess: () => {
      // publishing makes the workflow appear in the public browse list
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};

export const useDownloadWorkflow = () => {
  return useMutation({
    mutationFn: (id: string) => workflowsService.download(id),
  });
};

export const useDeleteWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workflowsService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
};
