import type { CSSProperties } from 'react';
import type {
  ComponentCreatorDto,
  ComponentDetailBaseDto,
  ComponentKind,
  ComponentListItemBaseDto,
  ComponentMatchDto,
  DomainDto,
  FormatLabelSource,
  ParameterDto,
} from './types';
import { ComponentSource, ComponentStatus, ParameterDirection } from './types';
import { formatDate, getCreatorDisplay } from '@/api/transformer';
import type { WithHateoasLinks } from '@/api/types';

// The shared half of every display model. Kind-specific transformers (api/tools,
// api/workflows) build on these helpers; api/components/variants dispatches between them.

export const SOURCE_LABELS: Record<ComponentSource, string> = {
  [ComponentSource.AUTOMATED_PACKAGING]: 'Packaged from GitHub',
  [ComponentSource.MANUAL_UPLOAD]: 'Manual upload',
  [ComponentSource.WORKFLOW_BUILDER]: 'Built in Workflow Builder',
};

export const STATUS_LABELS: Record<ComponentStatus, string> = {
  [ComponentStatus.DRAFT]: 'Draft',
  [ComponentStatus.PUBLISHED]: 'Published',
  [ComponentStatus.DEPRECATED]: 'Deprecated',
};

export const KIND_LABELS: Record<ComponentKind, string> = {
  tool: 'Tool',
  workflow: 'Workflow',
};

const DIRECTION_LABELS: Record<ParameterDirection, string> = {
  [ParameterDirection.INPUT]: 'Input',
  [ParameterDirection.OUTPUT]: 'Output',
};

/** What every list display model carries, whatever the kind. */
export interface ComponentDisplayModelBase extends WithHateoasLinks {
  kind: ComponentKind;
  kindDisplay: string;
  id: string;
  name: string;
  description: string | null;
  authorDisplay: string;
  version: number;
  domains: string[];
  domainsDisplay: string[];
  status: ComponentStatus;
  statusDisplay: string;
  /** why the version is deprecated - null unless it is */
  deprecationNote: string | null;
  createdAt: Date;
  createdAtDisplay: string;
  isFavorite: boolean;
  /** the component's ports - a workflow's are its own inputs/outputs */
  parameters: ParameterDisplayModel[];
  match: ComponentMatchDto | null;
}

/** What every detail display model carries on top, whatever the kind. */
export interface ComponentDetailFields {
  source: ComponentSource;
  sourceDisplay: string;
  repoUrl: string | null;
  repoCommitSha: string | null;
  repoCommitShaShort: string | null;
  doi: string | null;
  cwlContent: string;
  updatedAt: Date;
  updatedAtDisplay: string;
  inputs: ParameterDisplayModel[];
  outputs: ParameterDisplayModel[];
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
  formatLabelSource: FormatLabelSource | null;
  acceptsManualFormatLabel: boolean;
  direction: ParameterDirection;
  directionDisplay: string;
}

/**
 * Who a component is credited to: its author name (free text - e.g. the MoveApps author a
 * packaged app declares), else the user who uploaded it, else "Unknown".
 */
export function getAuthorDisplay(authorName: string | null, createdBy: ComponentCreatorDto | null): string {
  const author = authorName?.trim();
  if (author) return author;
  return getCreatorDisplay(createdBy);
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

export function toParameterDisplayModel(parameter: ParameterDto): ParameterDisplayModel {
  return {
    ...parameter,
    directionDisplay: DIRECTION_LABELS[parameter.direction],
  };
}

export function splitPorts(parameters: ParameterDisplayModel[]): Pick<ComponentDetailFields, 'inputs' | 'outputs'> {
  return {
    inputs: parameters.filter((p) => p.direction === ParameterDirection.INPUT),
    outputs: parameters.filter((p) => p.direction === ParameterDirection.OUTPUT),
  };
}

/** The base list display fields of any component DTO. */
export function toDisplayModelBase(dto: ComponentListItemBaseDto): ComponentDisplayModelBase {
  const createdAt = new Date(dto.createdAt);
  return {
    kind: dto.kind,
    kindDisplay: KIND_LABELS[dto.kind],
    id: dto.id,
    name: dto.name,
    description: dto.description,
    authorDisplay: getAuthorDisplay(dto.authorName, dto.createdBy),
    version: dto.version,
    domains: dto.domains,
    domainsDisplay: dto.domains.map(getDomainLabel),
    status: dto.status,
    statusDisplay: STATUS_LABELS[dto.status],
    deprecationNote: dto.deprecationNote ?? null,
    createdAt,
    createdAtDisplay: formatDate(createdAt),
    isFavorite: dto.isFavorite,
    parameters: dto.parameters?.map(toParameterDisplayModel) ?? [],
    match: dto.match ?? null,
    _links: dto._links,
  };
}

/** The detail fields shared by both kinds. */
export function toDetailFields(dto: ComponentDetailBaseDto): ComponentDetailFields & { parameters: ParameterDisplayModel[] } {
  const updatedAt = new Date(dto.updatedAt);
  const parameters = dto.parameters.map(toParameterDisplayModel);
  return {
    source: dto.source,
    sourceDisplay: SOURCE_LABELS[dto.source],
    repoUrl: dto.repoUrl,
    repoCommitSha: dto.repoCommitSha,
    repoCommitShaShort: dto.repoCommitSha ? dto.repoCommitSha.slice(0, 8) : null,
    doi: dto.doi,
    cwlContent: dto.cwlContent,
    updatedAt,
    updatedAtDisplay: formatDate(updatedAt),
    parameters,
    ...splitPorts(parameters),
  };
}
