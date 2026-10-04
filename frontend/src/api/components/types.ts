import type { MineQueryParams, PageParams, SplitPageResponse, WithHateoasLinks } from '@/api/types';
import type { ToolDetailDto, ToolListItemDto } from '@/api/tools/types';
import type { WorkflowDetailDto, WorkflowListItemDto } from '@/api/workflows/types';

/**
 * Which child of the composite a component is - CWL's Process subclasses, narrowed to the
 * two this repository models. A tool is a leaf (CommandLineTool / ExpressionTool), a
 * workflow is a composite whose steps run other components.
 */
export const ComponentKind = {
  TOOL: 'tool',
  WORKFLOW: 'workflow',
} as const;
export type ComponentKind = (typeof ComponentKind)[keyof typeof ComponentKind];

export type ComponentDomain = string;

export interface DomainDto {
  id: string;
  color: string;
  description: string | null;
}

export const ComponentSource = {
  AUTOMATED_PACKAGING: 'automated_packaging',
  MANUAL_UPLOAD: 'manual_upload',
  /** workflows only - generated from a builder canvas */
  WORKFLOW_BUILDER: 'workflow_builder',
} as const;
export type ComponentSource = (typeof ComponentSource)[keyof typeof ComponentSource];

export const ComponentStatus = {
  DRAFT: 'draft',
  PUBLISHED: 'published',
} as const;
export type ComponentStatus = (typeof ComponentStatus)[keyof typeof ComponentStatus];

export const FormatLabelSource = {
  /** resolved from the component's ontology by the format service */
  ONTOLOGY: 'ontology',
  /** written by hand for a port no ontology covers (e.g. "RDS") - display only */
  MANUAL: 'manual',
  /** an ontology format whose label could not be resolved (yet) */
  UNRESOLVED: 'unresolved',
} as const;
export type FormatLabelSource = (typeof FormatLabelSource)[keyof typeof FormatLabelSource];

export type ConnectionStatus = 'compatible' | 'incompatible' | 'unverified';

/** A palette candidate's best fit on the builder canvas, as ranked by the backend. */
export interface ComponentMatchDto {
  score: number;
  status: Exclude<ConnectionStatus, 'incompatible'> | null;
  componentId: string | null;
  componentName: string | null;
}

export const ParameterDirection = {
  INPUT: 'input',
  OUTPUT: 'output',
} as const;
export type ParameterDirection = (typeof ParameterDirection)[keyof typeof ParameterDirection];

/** One port of a component - a tool's input/output, or a workflow's own. */
export interface ParameterDto {
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
}

/** A previewed port - never persisted, so `id` is synthetic. */
export interface PreviewParameterDto {
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
}

/**
 * A hand-written label for a File port whose format no ontology covers (e.g. "RDS"), so the
 * builder can show it on the port. Display only - it never verifies a connection.
 */
export interface FormatLabelDto {
  name: string;
  direction: ParameterDirection;
  label: string | null;
}

export interface ComponentCreatorDto {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
}

/** The component currently holding a name, returned when that name is taken. */
export interface ExistingComponentDto {
  id: string;
  kind: ComponentKind;
  name: string;
  version: number;
  domains: ComponentDomain[];
  status: ComponentStatus;
  createdAt: string;
  /** only ever true for a tool lineage you own - a workflow's versions come from the builder */
  canAddVersion: boolean;
}

/** Whether a name can still be claimed for a new lineage - of either kind, names are one key. */
export interface NameAvailabilityDto {
  name: string;
  available: boolean;
  existing: ExistingComponentDto | null;
}

/** A workflow version running some version(s) of a component - "Used in these workflows". */
export interface ComponentUsageDto {
  id: string;
  name: string;
  version: number;
  /** draft only ever shows up for the viewer's own workflows */
  status: ComponentStatus;
  /** which versions of the component its steps use, ascending */
  componentVersions: number[];
}

/** A public workflow running a component at some depth. `status` says which public status it has. */
export interface ComponentAncestorDto {
  id: string;
  name: string;
  version: number;
  status: ComponentStatus;
  createdBy: ComponentCreatorDto | null;
}

/** What unpublishing or deleting one exact component version touches - read by both dialogs beforehand. */
export interface ComponentImpactDto {
  /** the caller's public workflows running it at any depth - they become drafts along with it */
  ownPublicAncestors: ComponentAncestorDto[];
  /** other users' public workflows running it at any depth - non-empty means unpublish and delete are blocked */
  foreignPublicAncestors: ComponentAncestorDto[];
  /** workflows the caller may see whose steps use exactly this version; componentVersions is always just this one */
  workflows: ComponentUsageDto[];
  /** other users' draft workflows - private, so only counted */
  hiddenWorkflowCount: number;
  /** the deleter's own builder drafts with this version on the canvas */
  drafts: { id: string; name: string }[];
  /** other users' builder drafts - private, so only counted */
  otherDraftCount: number;
}

/** What every list row carries, whatever the kind - see ToolListItemDto / WorkflowListItemDto. */
export interface ComponentListItemBaseDto extends WithHateoasLinks {
  kind: ComponentKind;
  id: string;
  name: string;
  description: string | null;
  authorName: string | null;
  createdBy: ComponentCreatorDto | null;
  version: number;
  domains: ComponentDomain[];
  status: ComponentStatus;
  createdAt: string;
  isFavorite: boolean;
  parameters: ParameterDto[] | null;
  match?: ComponentMatchDto | null;
}

/** What every detail view carries, whatever the kind - see ToolDetailDto / WorkflowDetailDto. */
export interface ComponentDetailBaseDto extends WithHateoasLinks {
  kind: ComponentKind;
  id: string;
  name: string;
  authorName: string | null;
  createdBy: ComponentCreatorDto | null;
  description: string | null;
  repoUrl: string | null;
  repoCommitSha: string | null;
  doi: string | null;
  version: number;
  cwlContent: string;
  ontologyUrl: string | null;
  domains: ComponentDomain[];
  source: ComponentSource;
  status: ComponentStatus;
  parameters: ParameterDto[];
  createdAt: string;
  updatedAt: string;
  isFavorite: boolean;
}

/** A row of a list serving both kinds - narrow it on `kind`. */
export type ComponentListItemDto = ToolListItemDto | WorkflowListItemDto;
/** A detail view of either kind - narrow it on `kind`. */
export type ComponentDetailDto = ToolDetailDto | WorkflowDetailDto;

/** The commands every component understands - POST /components/{id}/commands. */
export const ComponentCommand = {
  ADD_FAVORITE: 'ADD_FAVORITE',
  REMOVE_FAVORITE: 'REMOVE_FAVORITE',
  PUBLISH: 'PUBLISH',
  UNPUBLISH: 'UNPUBLISH',
  UPDATE_DESCRIPTION: 'UPDATE_DESCRIPTION',
  UPDATE_DOMAIN: 'UPDATE_DOMAIN',
} as const;
export type ComponentCommand = (typeof ComponentCommand)[keyof typeof ComponentCommand];

export type ComponentCommandExecuteRequest =
  | {
      command: typeof ComponentCommand.ADD_FAVORITE | typeof ComponentCommand.REMOVE_FAVORITE;
      note?: string;
    }
  | {
      command: typeof ComponentCommand.UNPUBLISH;
      note?: string;
      /** also unpublish your own public workflows that run it, at any depth */
      unpublishParents?: boolean;
    }
  | {
      command: typeof ComponentCommand.PUBLISH;
      note?: string;
      /** workflows only: also publish the draft components it runs, at any depth */
      publishComponents?: boolean;
    }
  | { command: typeof ComponentCommand.UPDATE_DESCRIPTION; note?: string; description: string | null }
  | { command: typeof ComponentCommand.UPDATE_DOMAIN; note?: string; domains: ComponentDomain[] };

export interface ComponentListQueryParams extends PageParams<ComponentListItemDto> {
  /** omitted lists both kinds */
  kind?: ComponentKind;
  domain?: ComponentDomain[];
  excludeMine?: boolean;
  favoritesOnly?: boolean;
  search?: string;
  includeParameters?: boolean;
  rankAgainst?: string[];
  favoritesFirst?: boolean;
}

export interface MyComponentsQueryParams extends MineQueryParams {
  kind?: ComponentKind;
}

export type MyComponentsResponseDto = SplitPageResponse<ComponentListItemDto>;
