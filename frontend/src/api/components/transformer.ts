import type { CSSProperties } from 'react';
import type {
  ComponentCreatorDto,
  ComponentDetailDto,
  ComponentListItemDto,
  CreateComponentDto,
  DomainDto,
  PackageComponentDto,
  ParameterDto,
  UpdateComponentDto,
} from './types';
import { ComponentSource, ParameterDirection } from './types';
import type {
  PackageComponentFormData,
  UpdateComponentFormData,
  UploadComponentFormData,
} from './schema';
import { formatDate, getCreatorDisplay } from '@/api/transformer';

const SOURCE_LABELS: Record<ComponentSource, string> = {
  [ComponentSource.AUTOMATED_PACKAGING]: 'Packaged from GitHub',
  [ComponentSource.MANUAL_UPLOAD]: 'Manual upload',
};

const DIRECTION_LABELS: Record<ParameterDirection, string> = {
  [ParameterDirection.INPUT]: 'Input',
  [ParameterDirection.OUTPUT]: 'Output',
};

export interface ComponentDisplayModel {
  id: string;
  name: string;
  description: string | null;
  authorDisplay: string;
  repoUrl: string | null;
  version: number;
  domain: string;
  domainDisplay: string;
  createdAt: Date;
  createdAtDisplay: string;
  isFavorite: boolean;
}

export interface ParameterDisplayModel {
  id: string;
  name: string;
  cwlType: string;
  defaultValue: string | null;
  description: string | null;
  format: string | null;
  formatLabel: string | null;
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
  getInitialUploadFormValues(): Omit<UploadComponentFormData, 'cwlFile'> {
    return { name: '', domain: '', authorName: '', description: '' };
  },

  getInitialPackageFormValues(): PackageComponentFormData {
    return { repoUrl: '', domain: '', description: '' };
  },

  formToCreateDto(form: UploadComponentFormData): CreateComponentDto {
    return {
      name: form.name,
      domain: form.domain,
      authorName: form.authorName || undefined,
      description: form.description || null,
    };
  },

  formToPackageDto(form: PackageComponentFormData): PackageComponentDto {
    return {
      repoUrl: form.repoUrl,
      domain: form.domain,
      description: form.description || null,
    };
  },

  formToUpdateDto(form: Partial<UpdateComponentFormData>): UpdateComponentDto {
    const dto: UpdateComponentDto = {};
    if (form.description !== undefined) dto.description = form.description;
    if (form.domain !== undefined) dto.domain = form.domain;
    return dto;
  },

  getInitialUpdateFormValues(component: ComponentDisplayModel): UpdateComponentFormData {
    return { domain: component.domain, description: component.description ?? '' };
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
      domain: dto.domain,
      domainDisplay: getDomainLabel(dto.domain),
      createdAt,
      createdAtDisplay: formatDate(createdAt),
      isFavorite: dto.isFavorite,
    };
  },

  toListDisplayModels(dtos: ComponentListItemDto[]): ComponentDisplayModel[] {
    return dtos.map((dto) => this.toDisplayModel(dto));
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
      updatedAt,
      updatedAtDisplay: formatDate(updatedAt),
      parameters,
      inputs: parameters.filter((p) => p.direction === ParameterDirection.INPUT),
      outputs: parameters.filter((p) => p.direction === ParameterDirection.OUTPUT),
    };
  },
};