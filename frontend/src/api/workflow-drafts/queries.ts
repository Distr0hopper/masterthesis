import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/auth.store';
import { componentKeys } from '@/api/components/queries';
import { workflowDraftsService } from './service';
import type { WriteWorkflowDraftDto } from './types';

export const draftKeys = {
  all: ['workflow-drafts'] as const,
  lists: () => [...draftKeys.all, 'list'] as const,
  detail: (id: string) => [...draftKeys.all, 'detail', id] as const,
};

export const useWorkflowDrafts = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  return useQuery({
    queryKey: draftKeys.lists(),
    queryFn: () => workflowDraftsService.getAll(),
    enabled: isAuthenticated,
  });
};

export const useWorkflowDraft = (id: string, enabled = true) => {
  return useQuery({
    queryKey: draftKeys.detail(id),
    queryFn: () => workflowDraftsService.getById(id),
    enabled: enabled && !!id,
    staleTime: Infinity,
  });
};

export const useCreateDraft = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dto: WriteWorkflowDraftDto) => workflowDraftsService.create(dto),
    onSuccess: (created) => {
      queryClient.setQueryData(draftKeys.detail(created.id), created);
      queryClient.invalidateQueries({ queryKey: draftKeys.lists() });
    },
  });
};

export const useUpdateDraft = (id: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dto: WriteWorkflowDraftDto) => workflowDraftsService.update(id, dto),
    onSuccess: (updated) => {
      queryClient.setQueryData(draftKeys.detail(id), updated);
      queryClient.invalidateQueries({ queryKey: draftKeys.lists() });
    },
  });
};

export const useExportDraft = () => {
  return useMutation({
    mutationFn: (id: string) => workflowDraftsService.exportZip(id),
  });
};

export const useExportDraftInputs = () => {
  return useMutation({
    mutationFn: (id: string) => workflowDraftsService.exportInputs(id),
  });
};

export const useSyncDraftToMyWorkflows = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workflowDraftsService.syncToMyWorkflows(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: componentKeys.all }),
  });
};

export const useDeleteDraft = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, deleteLinkedWorkflow = false }: { id: string; deleteLinkedWorkflow?: boolean }) =>
      workflowDraftsService.delete(id, deleteLinkedWorkflow),
    onSuccess: (_result, { id, deleteLinkedWorkflow }) => {
      queryClient.removeQueries({ queryKey: draftKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: draftKeys.lists() });
      // the My Workflows lists change when the linked workflow is dropped too
      if (deleteLinkedWorkflow) {
        queryClient.invalidateQueries({ queryKey: componentKeys.all });
      }
    },
  });
};
