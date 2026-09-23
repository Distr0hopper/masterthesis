import type { CSSProperties } from 'react';
import type {
  ComponentCreatorDto,
  ComponentDetailDto,
  ComponentListItemDto,
  ComponentPreviewDto,
  DomainDto,
  PackageComponentDto,
  ParameterDto,
} from './types';
import { ComponentSource, ComponentStatus, ParameterDirection } from './types';
import type {
  PackageComponentFormData,
  UpdateComponentFormData,
} from './schema';
import { formatDate, getCreatorDisplay } from '@/api/transformer';
import type { WithHateoasLinks } from '@/api/types';
import { buildDockerPullUrl } from '@/lib/dockerImage';

const SOURCE_LABELS: Record<ComponentSource, string> = {
  [ComponentSource.AUTOMATED_PACKAGING]: 'Packaged from GitHub',
  [ComponentSource.MANUAL_UPLOAD]: 'Manual upload',
};

const COMPONENT_STATUS_LABELS: Record<ComponentStatus, string> = {
  [ComponentStatus.DRAFT]: 'Draft',
  [ComponentStatus.PUBLISHED]: 'Published',
};

const DIRECTION_LABELS: Record<ParameterDirection, string> = {
  [ParameterDirection.INPUT]: 'Input',
  [ParameterDirection.OUTPUT]: 'Output',
};

export interface ComponentDisplayModel extends WithHateoasLinks {
  id: string;
  name: string;
  description: string | null;
  authorDisplay: string;
  repoUrl: string | null;
  version: number;
  domains: string[];
  domainsDisplay: string[];
  status: ComponentStatus;
  statusDisplay: string;
  createdAt: Date;
  createdAtDisplay: string;
  isFavorite: boolean;
  /** empty unless the list request opted in via `includeParameters` (always populated on detail) */
  parameters: ParameterDisplayModel[];
}

export interface ParameterDisplayModel {
  id: string;
  name: string;
  cwlType: string;
  defaultValue: string | null;
  description: string | null;
  format: string | null;
  formatLabel: string | null;
  ontologyUrl: string | null;
  direction: ParameterDirection;
  directionDisplay: string;
}

export interface ComponentDetailDisplayModel extends ComponentDisplayModel {
  source: ComponentSource;
  sourceDisplay: string;
  repoCommitSha: string | null;
  repoCommitShaShort: string | null;
  doi: string | null;
  cwlContent: string;
  cwlType: string | null;
  dockerfileContent: string | null;
  dockerPullReference: string | null;
  dockerPullUrl: string | null;
  updatedAt: Date;
  updatedAtDisplay: string;
  parameters: ParameterDisplayModel[];
  inputs: ParameterDisplayModel[];
  outputs: ParameterDisplayModel[];
}

function getAuthorDisplay(authorName: string | null, createdBy?: ComponentCreatorDto | null): string {
  return createdBy ? getCreatorDisplay(createdBy) : (authorName ?? 'Unknown');
}

export function getDomainLabel(domain: string): string {
  return domain
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function getDomainBadgeStyle(domainId: string, domains: DomainDto[]): CSSProperties | undefined {
  const color = domains.find((d) => d.id === domainId)?.color;
  if (!color) return undefined;
  // color + alpha suffix for a light tinted background, matching the border/text color
  return { borderColor: color, color, backgroundColor: `${color}1A` };
}

export const componentTransformer = {
  getInitialPackageFormValues(): PackageComponentFormData {
    return { repoUrl: '', domains: [], description: '' };
  },

  formToPackageDto(form: PackageComponentFormData): PackageComponentDto {
    return {
      repoUrl: form.repoUrl,
      domains: form.domains,
      description: form.description || null,
    };
  },

  getInitialUpdateFormValues(component: ComponentDisplayModel): UpdateComponentFormData {
    return { domains: component.domains, description: component.description ?? '' };
  },

  toParameterDisplayModel(parameter: ParameterDto): ParameterDisplayModel {
    return {
      ...parameter,
      directionDisplay: DIRECTION_LABELS[parameter.direction],
    };
  },

  toDisplayModel(dto: ComponentListItemDto): ComponentDisplayModel {
    const createdAt = new Date(dto.createdAt);
    return {
      id: dto.id,
      name: dto.name,
      description: dto.description,
      authorDisplay: getAuthorDisplay(dto.authorName),
      repoUrl: dto.repoUrl,
      version: dto.version,
      domains: dto.domains,
      domainsDisplay: dto.domains.map(getDomainLabel),
      status: dto.status,
      statusDisplay: COMPONENT_STATUS_LABELS[dto.status],
      createdAt,
      createdAtDisplay: formatDate(createdAt),
      isFavorite: dto.isFavorite,
      parameters: dto.parameters?.map(componentTransformer.toParameterDisplayModel) ?? [],
      _links: dto._links,
    };
  },

  toListDisplayModels(dtos: ComponentListItemDto[]): ComponentDisplayModel[] {
    // self-reference by name, not `this` - toListDisplayModel() passes this method
    // around as a bare function reference, which would drop a `this` binding
    return dtos.map((dto) => componentTransformer.toDisplayModel(dto));
  },

  /**
   * A detail display model for a component that does NOT exist yet, so the same
   * read-only ComponentTabs used on the detail page can preview a workflow upload's
   * steps before anything is saved.
   *
   * The identity fields are placeholders: `id` is empty (ComponentTabs must be rendered
   * with `isPreview` so it never builds a server download URL from it), `version` is 1
   * and `status` is DRAFT because that is what creating this component would produce.
   */
  toPreviewDisplayModel(
    preview: ComponentPreviewDto,
    overrides: { name?: string; domains?: string[]; description?: string | null } = {},
  ): ComponentDetailDisplayModel {
    const now = new Date();
    const name = overrides.name?.trim() || 'Component';
    const domains = overrides.domains ?? [];
    const description = overrides.description?.trim() || preview.description;
    const parameters = preview.parameters.map(componentTransformer.toParameterDisplayModel);
    return {
      id: '',
      name,
      description,
      authorDisplay: 'You',
      repoUrl: null,
      version: 1,
      domains,
      domainsDisplay: domains.map(getDomainLabel),
      status: ComponentStatus.DRAFT,
      statusDisplay: COMPONENT_STATUS_LABELS[ComponentStatus.DRAFT],
      createdAt: now,
      createdAtDisplay: formatDate(now),
      isFavorite: false,
      source: ComponentSource.MANUAL_UPLOAD,
      sourceDisplay: SOURCE_LABELS[ComponentSource.MANUAL_UPLOAD],
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
      inputs: parameters.filter((p) => p.direction === ParameterDirection.INPUT),
      outputs: parameters.filter((p) => p.direction === ParameterDirection.OUTPUT),
    };
  },

  toDetailDisplayModel(dto: ComponentDetailDto): ComponentDetailDisplayModel {
    const updatedAt = new Date(dto.updatedAt);
    const parameters = dto.parameters.map(this.toParameterDisplayModel);
    return {
      ...this.toDisplayModel(dto),
      authorDisplay: getAuthorDisplay(dto.authorName, dto.createdBy),
      source: dto.source,
      sourceDisplay: SOURCE_LABELS[dto.source],
      repoCommitSha: dto.repoCommitSha,
      repoCommitShaShort: dto.repoCommitSha ? dto.repoCommitSha.slice(0, 8) : null,
      doi: dto.doi,
      cwlContent: dto.cwlContent,
      cwlType: dto.cwlType,
      dockerfileContent: dto.dockerfileContent,
      dockerPullReference: dto.dockerPullReference,
      dockerPullUrl: dto.dockerPullReference ? buildDockerPullUrl(dto.dockerPullReference) : null,
      updatedAt,
      updatedAtDisplay: formatDate(updatedAt),
      parameters,
      inputs: parameters.filter((p) => p.direction === ParameterDirection.INPUT),
      outputs: parameters.filter((p) => p.direction === ParameterDirection.OUTPUT),
    };
  },
};