import type {
  ComponentDetailDto,
  ComponentListItemDto,
  CreateComponentDto,
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
  authorDisplay: string;
  repoUrl: string | null;
  version: number;
  domain: string;
  source: ComponentSource;
  sourceDisplay: string;
  createdAt: Date;
}

export interface ParameterDisplayModel {
  id: string;
  name: string;
  cwlType: string;
  defaultValue: string | null;
  description: string | null;
  direction: ParameterDirection;
  directionDisplay: string;
}

export interface ComponentDetailDisplayModel extends ComponentDisplayModel {
  description: string | null;
  repoCommitSha: string | null;
  doi: string | null;
  cwlContent: string;
  parameters: ParameterDisplayModel[];
}

function getAuthorDisplay(dto: ComponentListItemDto | ComponentDetailDto): string {
  if ('createdBy' in dto && dto.createdBy) {
    const { firstName, lastName, email } = dto.createdBy;
    return firstName && lastName ? `${firstName} ${lastName}` : email;
  }
  return dto.authorName ?? 'Unknown';
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

  toParameterDisplayModel(parameter: ParameterDto): ParameterDisplayModel {
    return {
      ...parameter,
      directionDisplay: DIRECTION_LABELS[parameter.direction],
    };
  },

  toDisplayModel(dto: ComponentListItemDto): ComponentDisplayModel {
    return {
      id: dto.id,
      name: dto.name,
      authorDisplay: getAuthorDisplay(dto),
      repoUrl: dto.repoUrl,
      version: dto.version,
      domain: dto.domain,
      source: dto.source,
      sourceDisplay: SOURCE_LABELS[dto.source],
      createdAt: new Date(dto.createdAt),
    };
  },

  toListDisplayModels(dtos: ComponentListItemDto[]): ComponentDisplayModel[] {
    return dtos.map((dto) => this.toDisplayModel(dto));
  },

  toDetailDisplayModel(dto: ComponentDetailDto): ComponentDetailDisplayModel {
    return {
      ...this.toDisplayModel(dto),
      description: dto.description,
      repoCommitSha: dto.repoCommitSha,
      doi: dto.doi,
      cwlContent: dto.cwlContent,
      parameters: dto.parameters.map(this.toParameterDisplayModel),
    };
  },
};