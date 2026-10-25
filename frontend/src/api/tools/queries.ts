import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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

export const useDownloadToolBundle = () => {
  return useMutation({ mutationFn: (id: string) => toolsService.downloadBundle(id) });
};

export const toolKeys = {
  packagePreviews: ['tools', 'package-preview'] as const,
  packagePreview: (repoUrl: string) => [...toolKeys.packagePreviews, repoUrl] as const,
};

/**
 * A GitHub repo packaged for review, without persisting it - loaded while `repoUrl` is set.
 * A query rather than a mutation: it reads, so mounting twice (StrictMode, back navigation)
 * shares one request instead of losing its result.
 */
export const usePackagePreview = (repoUrl: string | null) => {
  return useQuery({
    queryKey: toolKeys.packagePreview(repoUrl ?? ''),
    queryFn: () => toolsService.packagePreview(repoUrl!),
    enabled: !!repoUrl,
    // packaging takes seconds and fails for reasons a retry doesn't fix (no appspec.json, ...)
    retry: false,
    // only ever re-read on purpose ("Fetch again") or when the wizard is opened again
    staleTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
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
      // the repo is packaged now - a cached preview would still offer it as new
      queryClient.removeQueries({ queryKey: toolKeys.packagePreviews });
    },
  });
};

export const useUpdateToolFormatLabels = () =>
  useCommandMutation(
    componentKeys.all,
    ({ link, formatLabels }: { link: HateoasLink; formatLabels: FormatLabelDto[] }) =>
      toolsService.executeCommand(link, { command: ToolCommand.UPDATE_FORMAT_LABELS, formatLabels }),
  );
