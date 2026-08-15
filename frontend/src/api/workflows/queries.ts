import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { workflowsService } from './service';
import type { CreateWorkflowDto } from './types';

export const workflowKeys = {
  all: ['workflows'] as const,
  lists: (domain?: string) => [...workflowKeys.all, 'list', domain] as const,
  detail: (id: string) => [...workflowKeys.all, 'detail', id] as const,
};

export const useWorkflows = (domain?: string) => {
  return useQuery({
    queryKey: workflowKeys.lists(domain),
    queryFn: () => workflowsService.getAll(domain),
  });
};

export const useWorkflow = (id: string) => {
  return useQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: () => workflowsService.getById(id),
    enabled: !!id,
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
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(variables.workflowId) });
    },
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
