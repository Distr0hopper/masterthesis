import { useMutation, useQueryClient } from '@tanstack/react-query';
import { componentKeys } from '@/api/components/queries';
import { useCommandMutation } from '@/api/useCommandMutation';
import type { FormatLabelDto } from '@/api/components/types';
import type { HateoasLink } from '@/api/types';
import { toolsService } from './service';
import { ToolCommand } from './types';
import type { AddVersionDto, CreateToolDto, PackageToolDto } from './types';

// tools live in the shared component cache - every mutation here invalidates componentKeys.all

export const useParseTool = () => {
  return useMutation({ mutationFn: (file: File) => toolsService.parse(file) });
};

export const usePackagePreview = () => {
  return useMutation({ mutationFn: (repoUrl: string) => toolsService.packagePreview(repoUrl) });
};

export const useUploadTool = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, dto }: { file: File; dto: CreateToolDto }) => toolsService.upload(file, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useAddManualVersion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, file, dto }: { id: string; file: File; dto: AddVersionDto }) =>
      toolsService.addManualVersion(id, file, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const usePackageTool = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dto: PackageToolDto) => toolsService.package(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

export const useUpdateToolFormatLabels = () =>
  useCommandMutation(
    componentKeys.all,
    ({ link, formatLabels }: { link: HateoasLink; formatLabels: FormatLabelDto[] }) =>
      toolsService.executeCommand(link, { command: ToolCommand.UPDATE_FORMAT_LABELS, formatLabels }),
  );
