import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/auth.store';
import { workflowKeys } from '@/api/workflows';
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
    // the endpoint is owner-scoped and 401s for anonymous visitors
    enabled: isAuthenticated,
  });
};

export const useWorkflowDraft = (id: string, enabled = true) => {
  return useQuery({
    queryKey: draftKeys.detail(id),
    queryFn: () => workflowDraftsService.getById(id),
    enabled: enabled && !!id,
    // a draft only changes when the user hits Save, and a background refetch would
    // otherwise reset the canvas out from under unsaved edits
    staleTime: Infinity,
  });
};

export const useCreateDraft = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dto: WriteWorkflowDraftDto) => workflowDraftsService.create(dto),
    onSuccess: (created) => {
      // seed the detail cache so the post-save redirect to /builder/:id does not refetch
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
  // downloading has no server-side effect, so nothing to invalidate
  return useMutation({
    mutationFn: (id: string) => workflowDraftsService.exportZip(id),
  });
};

export const usePublishDraft = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workflowDraftsService.publish(id),
    // a new Workflow now exists, so any cached workflow list is stale
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workflowKeys.all }),
  });
};

export const useDeleteDraft = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workflowDraftsService.delete(id),
    onSuccess: (_result, id) => {
      queryClient.removeQueries({ queryKey: draftKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: draftKeys.lists() });
    },
  });
};
