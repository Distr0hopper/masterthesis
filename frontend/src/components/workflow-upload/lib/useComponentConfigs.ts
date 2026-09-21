import { useCallback, useMemo, useState } from 'react';
import type { ComponentConfigDto, WorkflowStepPreviewDto } from '@/api/workflows';
import type { ExistingComponentDto } from '@/api/components';

export type ConfigMode = 'create' | 'reuse';

export interface ComponentConfigState {
  mode: ConfigMode;
  name: string;
  domains: string[];
  description: string;
  /** set in 'reuse' mode - the catalogue component this step binds to */
  reuseComponentId: string | null;
  reuseName: string | null;
  reuseVersion: number | null;
}

/** The component a step's name currently collides with, as last reported by a card. */
export type NameConflicts = Record<string, ExistingComponentDto | null>;

function initialState(preview: WorkflowStepPreviewDto): ComponentConfigState {
  // an archive step whose run: filename matches a catalogue component defaults to reusing
  // it - re-importing a component the repository already holds is almost never intended
  if (preview.suggestedMatch) {
    const { componentId, name, version } = preview.suggestedMatch;
    return {
      mode: 'reuse',
      name: preview.suggestedName,
      domains: [],
      description: '',
      reuseComponentId: componentId,
      reuseName: name,
      reuseVersion: version,
    };
  }
  return {
    mode: 'create',
    name: preview.suggestedName,
    domains: [],
    description: '',
    reuseComponentId: null,
    reuseName: null,
    reuseVersion: null,
  };
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
    setConfigs(Object.fromEntries(next.map((p) => [p.stepId, initialState(p)])));
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

  const setNameConflict = useCallback((stepId: string, existing: ExistingComponentDto | null) => {
    setNameConflicts((prev) => (prev[stepId] === existing ? prev : { ...prev, [stepId]: existing }));
  }, []);

  const errors = useMemo(() => {
    const result: Record<string, string> = {};
    const nameCounts = new Map<string, number>();
    for (const preview of previews) {
      const config = configs[preview.stepId];
      if (!config || config.mode === 'reuse') continue;
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
      const name = config.name.trim();
      if (!name) {
        result[preview.stepId] = 'Name is required.';
      } else if ((nameCounts.get(name) ?? 0) > 1) {
        result[preview.stepId] = 'Another step in this upload already uses this name.';
      } else if (nameConflicts[preview.stepId]) {
        const existing = nameConflicts[preview.stepId]!;
        result[preview.stepId] = `A component named "${existing.name}" already exists (v${existing.version}).`;
      } else if (config.domains.length === 0) {
        result[preview.stepId] = 'At least one domain is required.';
      }
    }
    return result;
  }, [previews, configs, nameConflicts]);

  const isComplete = previews.length > 0 && Object.keys(errors).length === 0;

  const toDtos = useCallback(
    (): ComponentConfigDto[] =>
      previews.map((preview) => {
        const config = configs[preview.stepId];
        if (config.mode === 'reuse') {
          return { stepId: preview.stepId, reuseComponentId: config.reuseComponentId };
        }
        return {
          stepId: preview.stepId,
          name: config.name.trim(),
          domains: config.domains,
          description: config.description.trim() || null,
        };
      }),
    [previews, configs],
  );

  return { configs, errors, isComplete, reset, update, applyDomainsToAll, setNameConflict, toDtos };
}
