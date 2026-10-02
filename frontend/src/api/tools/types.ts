import type {
  ComponentDetailBaseDto,
  ComponentKind,
  ComponentListItemBaseDto,
  ExistingComponentDto,
  FormatLabelDto,
  PreviewParameterDto,
} from '@/api/components/types';

/** What only a tool - the leaf of the composite - has on top of the shared list row. */
export interface ToolListItemDto extends ComponentListItemBaseDto {
  kind: typeof ComponentKind.TOOL;
  repoUrl: string | null;
}

export interface ToolDetailDto extends ComponentDetailBaseDto {
  kind: typeof ComponentKind.TOOL;
  /** the CWL class - CommandLineTool or ExpressionTool */
  cwlType: string | null;
  dockerfileContent: string | null;
  dockerPullReference: string | null;
}

/**
 * A tool read out of a CWL document without persisting it - what POST /tools/parse
 * returns. Also the shared base of the workflow flow's WorkflowStepPreviewDto, which adds
 * the step the CWL came from.
 */
export interface ToolPreviewDto {
  description: string | null;
  cwlContent: string;
  cwlType: string | null;
  dockerfileContent: string | null;
  dockerPullReference: string | null;
  ontologyUrl: string | null;
  parameters: PreviewParameterDto[];
}

/**
 * A GitHub repo packaged without persisting it - what POST /tools/package/preview returns,
 * so the generated tool can be reviewed before it is created.
 */
export interface PackagePreviewDto extends ToolPreviewDto {
  repoName: string;
  repoUrl: string;
  commitSha: string;
  author: string | null;
  /** latest version already packaged from this repo - creating adds a new version to it */
  existing: ExistingComponentDto | null;
  /** the repo's current commit is already packaged as `existing` */
  alreadyPackaged: boolean;
}

/** The commands only a tool understands - POST /tools/{id}/commands. */
export const ToolCommand = {
  REPACKAGE: 'REPACKAGE',
  UPDATE_FORMAT_LABELS: 'UPDATE_FORMAT_LABELS',
} as const;
export type ToolCommand = (typeof ToolCommand)[keyof typeof ToolCommand];

export type ToolCommandExecuteRequest =
  | { command: typeof ToolCommand.REPACKAGE; note?: string }
  | { command: typeof ToolCommand.UPDATE_FORMAT_LABELS; note?: string; formatLabels: FormatLabelDto[] };

export interface CreateToolDto {
  name: string;
  domains: string[];
  authorName?: string;
  repoUrl?: string;
  repoCommitSha?: string;
  description?: string | null;
  formatLabels?: FormatLabelDto[];
}

export interface PackageToolDto {
  repoUrl: string;
  domains: string[];
  description?: string | null;
  /** name for a new tool - ignored when the repo is already packaged */
  name?: string | null;
  formatLabels?: FormatLabelDto[];
  /** commit the reviewed preview came from - the backend rejects (409) if the repo moved on */
  expectedCommitSha?: string | null;
}

export interface AddVersionDto {
  repoCommitSha?: string;
  description?: string;
}
