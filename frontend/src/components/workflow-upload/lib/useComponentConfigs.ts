import { useCallback, useMemo, useState } from 'react';
import type { ComponentConfigDto, WorkflowStepPreviewDto } from '@/api/workflows';
import {
  ComponentKind,
  ComponentStatus,
  toFormatLabelDtos,
  type ExistingComponentDto,
  type FormatLabelDraft,
} from '@/api/components';

/**
 * - create: a new tool from the step's CWL
 * - reuse: bind an existing component, nothing created
 * - version: the step's CWL as the next version of the tool it ran before (uploading a new
 *   workflow version only - the target is the step's `previous`)
 */
export type ConfigMode = 'create' | 'reuse' | 'version';

export interface ComponentConfigState {
  mode: ConfigMode;
  name: string;
  domains: string[];
  description: string;
  /** 'create' and 'version' modes - hand-written labels for File ports without an ontology format */
  formatLabels: FormatLabelDraft;
  /** set in 'reuse' mode - the catalogue component this step binds to */
  reuseComponentId: string | null;
  reuseKind: ComponentKind | null;
  reuseName: string | null;
  reuseVersion: number | null;
}

/**
 * A step's name collision, as last reported by a card. `takenBy` is null when the name is
 * held by a component the user may not see (someone else's draft) - still taken.
 */
export interface NameConflict {
  takenBy: ExistingComponentDto | null;
}

export type NameConflicts = Record<string, NameConflict | null>;

/**
 * Uploading a new workflow version: start each step from what it ran before - its tool's
 * next version when the CWL changed and that tool is yours to version, the same component
 * when nothing changed. Null when the previous version gives no sensible default: the step
 * is new, changed but someone else's tool, or ran a now deprecated version.
 */
function fromPrevious(preview: WorkflowStepPreviewDto): Partial<ComponentConfigState> | null {
  const previous = preview.previous;
  if (!previous) return null;
  if (previous.cwlChanged) return previous.canAddVersion ? { mode: 'version' } : null;
  if (previous.status === ComponentStatus.DEPRECATED) return null;
  return {
    mode: 'reuse',
    reuseComponentId: previous.componentId,
    reuseKind: previous.kind,
    reuseName: previous.name,
    reuseVersion: previous.version,
  };
}

/** Whether a preview is a nested workflow from the archive rather than a tool. */
export function isNestedWorkflow(preview: WorkflowStepPreviewDto): boolean {
  return preview.kind === ComponentKind.WORKFLOW;
}

/**
 * The previews that still need a decision: everything below a nested workflow that reuses
 * an existing one comes along with it - unless it also runs somewhere else. Mirrors the
 * backend's UploadPlan.active_units.
 */
export function activePreviews(
  previews: WorkflowStepPreviewDto[],
  configs: Record<string, ComponentConfigState>,
): WorkflowStepPreviewDto[] {
  const previewOf = new Map<string, string>();
  for (const preview of previews) {
    for (const path of preview.usedBy ?? [preview.stepId]) previewOf.set(path, preview.stepId);
  }
  const isReused = (path: string) => configs[previewOf.get(path) ?? '']?.mode === 'reuse';
  // a step path is `outer/inner/step` - each prefix is the nested workflow step above it
  const runs = (path: string) => {
    const parts = path.split('/');
    return parts.slice(1).every((_, i) => !isReused(parts.slice(0, i + 1).join('/')));
  };
  return previews.filter((preview) => (preview.usedBy ?? [preview.stepId]).some(runs));
}

/** Where a freshly previewed step's configuration starts. */
export function initialConfigState(preview: WorkflowStepPreviewDto): ComponentConfigState {
  const base = defaultState(preview);
  return { ...base, ...fromPrevious(preview) };
}

/** What one step's configuration is sent as - see ComponentConfigDto. */
export function toConfigDto(preview: WorkflowStepPreviewDto, config: ComponentConfigState): ComponentConfigDto {
  if (config.mode === 'reuse') {
    return { stepId: preview.stepId, reuseComponentId: config.reuseComponentId };
  }
  if (config.mode === 'version') {
    return {
      stepId: preview.stepId,
      newVersionOfId: preview.previous!.componentId,
      description: config.description.trim() || null,
      // only the labels written here - the tool's own carry over by themselves, and a
      // blank entry would clear them
      formatLabels: toFormatLabelDtos(preview.parameters, config.formatLabels).filter((label) => label.label),
    };
  }
  return {
    stepId: preview.stepId,
    name: config.name.trim(),
    domains: config.domains,
    description: config.description.trim() || null,
    formatLabels: toFormatLabelDtos(preview.parameters, config.formatLabels),
  };
}

function defaultState(preview: WorkflowStepPreviewDto): ComponentConfigState {
  // the description starts as the step's CWL doc: field, editable like any other input
  // an archive step whose run: filename matches a catalogue component defaults to reusing
  // it - re-importing a component the repository already holds is almost never intended
  if (preview.suggestedMatch) {
    const { componentId, kind, name, version } = preview.suggestedMatch;
    return {
      mode: 'reuse',
      name: preview.suggestedName,
      domains: [],
      description: preview.description ?? '',
      formatLabels: {},
      reuseComponentId: componentId,
      reuseKind: kind,
      reuseName: name,
      reuseVersion: version,
    };
  }
  return {
    mode: 'create',
    name: preview.suggestedName,
    domains: [],
    description: preview.description ?? '',
    formatLabels: {},
    reuseComponentId: null,
    reuseKind: null,
    reuseName: null,
    reuseVersion: null,
  };
}

/**
 * Why each step can't be saved yet, by step id - every step must resolve to either an
 * existing component or a fully-specified new one; the backend rejects anything less.
 * `previews` are the ones still needing a decision (see activePreviews).
 */
export function validateConfigs(
  previews: WorkflowStepPreviewDto[],
  configs: Record<string, ComponentConfigState>,
  nameConflicts: NameConflicts,
): Record<string, string> {
  const result: Record<string, string> = {};
  const nameCounts = new Map<string, number>();
  for (const preview of previews) {
    const config = configs[preview.stepId];
    if (!config || config.mode !== 'create') continue;
    const name = config.name.trim();
    if (name) nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1);
  }

  for (const preview of previews) {
    const config = configs[preview.stepId];
    if (!config) {
      result[preview.stepId] = 'This step is not configured yet.';
      continue;
    }
    if (config.mode === 'reuse') {
      if (!config.reuseComponentId) result[preview.stepId] = 'Pick a component to reuse.';
      continue;
    }
    if (config.mode === 'version') {
      if (isNestedWorkflow(preview) || !preview.previous?.canAddVersion) {
        result[preview.stepId] = 'This step has no tool to add a version to.';
      }
      continue;
    }
    const name = config.name.trim();
    if (!name) {
      result[preview.stepId] = 'Name is required.';
    } else if ((nameCounts.get(name) ?? 0) > 1) {
      result[preview.stepId] = 'Another step in this upload already uses this name.';
    } else if (nameConflicts[preview.stepId]) {
      const { takenBy } = nameConflicts[preview.stepId]!;
      result[preview.stepId] = takenBy
        ? `A component named "${takenBy.name}" already exists (v${takenBy.version}).`
        : 'This name is already taken — choose a different name.';
    } else if (config.domains.length === 0) {
      result[preview.stepId] = 'At least one domain is required.';
    }
  }
  return result;
}

/**
 * Per-step configuration for a parsed workflow upload, plus the validation that gates
 * saving. Every step must resolve to either an existing component or a fully-specified
 * new one before the workflow can be created - the backend rejects anything less.
 */
export function useComponentConfigs(previews: WorkflowStepPreviewDto[]) {
  const [configs, setConfigs] = useState<Record<string, ComponentConfigState>>({});
  const [nameConflicts, setNameConflicts] = useState<NameConflicts>({});

  const reset = useCallback((next: WorkflowStepPreviewDto[]) => {
    setConfigs(Object.fromEntries(next.map((p) => [p.stepId, initialConfigState(p)])));
    setNameConflicts({});
  }, []);

  const update = useCallback((stepId: string, patch: Partial<ComponentConfigState>) => {
    setConfigs((prev) => ({ ...prev, [stepId]: { ...prev[stepId], ...patch } }));
  }, []);

  /** apply one domain set to every step still being created - the common case is one set */
  const applyDomainsToAll = useCallback((domains: string[]) => {
    setConfigs((prev) =>
      Object.fromEntries(
        Object.entries(prev).map(([stepId, config]) => [
          stepId,
          config.mode === 'create' ? { ...config, domains } : config,
        ]),
      ),
    );
  }, []);

  const setNameConflict = useCallback((stepId: string, conflict: NameConflict | null) => {
    setNameConflicts((prev) => {
      const current = prev[stepId] ?? null;
      const unchanged =
        current === null ? conflict === null : conflict !== null && current.takenBy === conflict.takenBy;
      return unchanged ? prev : { ...prev, [stepId]: conflict };
    });
  }, []);

  const active = useMemo(() => activePreviews(previews, configs), [previews, configs]);
  const errors = useMemo(() => validateConfigs(active, configs, nameConflicts), [active, configs, nameConflicts]);

  const isComplete = active.length > 0 && Object.keys(errors).length === 0;

  const toDtos = useCallback(
    (): ComponentConfigDto[] => active.map((preview) => toConfigDto(preview, configs[preview.stepId])),
    [active, configs],
  );

  return { configs, active, errors, isComplete, reset, update, applyDomainsToAll, setNameConflict, toDtos };
}
