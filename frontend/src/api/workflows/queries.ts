import { useMutation, useQueryClient } from '@tanstack/react-query';
import { componentKeys } from '@/api/components/queries';
import { useCommandMutation } from '@/api/useCommandMutation';
import type { HateoasLink } from '@/api/types';
import { workflowsService } from './service';
import { WorkflowStepCommand } from './types';
import type { CreateWorkflowDto } from './types';

// workflows live in the shared component cache - every mutation here invalidates componentKeys.all

export const useCreateWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, dto }: { file: File; dto: CreateWorkflowDto }) => workflowsService.create(file, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useParseWorkflow = () => {
  return useMutation({
    mutationFn: (file: File) => workflowsService.parse(file),
  });
};

export const useUpdateWorkflowStepComponent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ link, componentId }: { link: HateoasLink; componentId: string | null }) =>
      workflowsService.updateStepComponent(link, componentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useConfirmWorkflowStep = () =>
  useCommandMutation(componentKeys.all, (link: HateoasLink) =>
    workflowsService.executeStepCommand(link, { command: WorkflowStepCommand.CONFIRM }),
  );
