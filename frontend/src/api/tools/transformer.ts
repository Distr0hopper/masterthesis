import type { ComponentKind } from '@/api/components/types';
import { ComponentSource, ComponentStatus } from '@/api/components/types';
import {
  KIND_LABELS,
  SOURCE_LABELS,
  STATUS_LABELS,
  getDomainLabel,
  splitPorts,
  toDetailFields,
  toDisplayModelBase,
  toParameterDisplayModel,
  type ComponentDetailFields,
  type ComponentDisplayModelBase,
} from '@/api/components/transformer';
import { formatDate } from '@/api/transformer';
import { buildDockerPullUrl } from '@/lib/dockerImage';
import type { ToolDetailDto, ToolListItemDto, ToolPreviewDto } from './types';

/** A tool - the leaf of the composite - as the UI shows it in a list. */
export interface ToolDisplayModel extends ComponentDisplayModelBase {
  kind: typeof ComponentKind.TOOL;
  repoUrl: string | null;
}

export interface ToolDetailDisplayModel extends ToolDisplayModel, ComponentDetailFields {
  cwlType: string | null;
  dockerfileContent: string | null;
  dockerPullReference: string | null;
  dockerPullUrl: string | null;
}

export const toolTransformer = {
  toDisplayModel(dto: ToolListItemDto): ToolDisplayModel {
    return { ...toDisplayModelBase(dto), kind: dto.kind, repoUrl: dto.repoUrl };
  },

  toDetailDisplayModel(dto: ToolDetailDto): ToolDetailDisplayModel {
    return {
      ...toDisplayModelBase(dto),
      ...toDetailFields(dto),
      kind: dto.kind,
      cwlType: dto.cwlType,
      dockerfileContent: dto.dockerfileContent,
      dockerPullReference: dto.dockerPullReference,
      dockerPullUrl: dto.dockerPullReference ? buildDockerPullUrl(dto.dockerPullReference) : null,
    };
  },

  /**
   * A detail display model for a tool that does NOT exist yet, so the same read-only
   * ToolTabs used on the detail page can preview an upload before anything is saved.
   *
   * The identity fields are placeholders: `id` is empty (ToolTabs must be rendered with
   * `isPreview` so it never builds a server download URL from it), `version` is 1 and
   * `status` is DRAFT because that is what creating this tool would produce.
   */
  toPreviewDisplayModel(
    preview: ToolPreviewDto,
    overrides: {
      name?: string;
      domains?: string[];
      description?: string | null;
      source?: ComponentSource;
      repoUrl?: string | null;
      version?: number;
    } = {},
  ): ToolDetailDisplayModel {
    const now = new Date();
    const name = overrides.name?.trim() || 'Tool';
    const domains = overrides.domains ?? [];
    const description = overrides.description?.trim() || preview.description;
    const parameters = preview.parameters.map(toParameterDisplayModel);
    const source = overrides.source ?? ComponentSource.MANUAL_UPLOAD;
    return {
      kind: 'tool',
      kindDisplay: KIND_LABELS.tool,
      id: '',
      name,
      description,
      authorDisplay: 'You',
      repoUrl: overrides.repoUrl ?? null,
      version: overrides.version ?? 1,
      domains,
      domainsDisplay: domains.map(getDomainLabel),
      status: ComponentStatus.DRAFT,
      statusDisplay: STATUS_LABELS[ComponentStatus.DRAFT],
      createdAt: now,
      createdAtDisplay: formatDate(now),
      isFavorite: false,
      match: null,
      source,
      sourceDisplay: SOURCE_LABELS[source],
      repoCommitSha: null,
      repoCommitShaShort: null,
      doi: null,
      cwlContent: preview.cwlContent,
      cwlType: preview.cwlType,
      dockerfileContent: preview.dockerfileContent,
      dockerPullReference: preview.dockerPullReference,
      dockerPullUrl: preview.dockerPullReference ? buildDockerPullUrl(preview.dockerPullReference) : null,
      updatedAt: now,
      updatedAtDisplay: formatDate(now),
      parameters,
      ...splitPorts(parameters),
    };
  },
};
