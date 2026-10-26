import { describe, expect, it } from 'vitest';
import { ComponentStatus, ParameterDirection, type PreviewParameterDto } from '@/api/components';
import { ComponentOrigin, type PreviousStepComponentDto, type WorkflowStepPreviewDto } from '@/api/workflows';
import { initialConfigState, toConfigDto, validateConfigs } from './useComponentConfigs';

function filePort(name: string, direction: ParameterDirection): PreviewParameterDto {
  return {
    id: `preview:${direction}:${name}`,
    name,
    cwlType: 'File',
    defaultValue: null,
    description: null,
    format: null,
    formatLabel: null,
    ontologyUrl: null,
    formatLabelSource: null,
    acceptsManualFormatLabel: true,
    direction,
  };
}

function previous(overrides: Partial<PreviousStepComponentDto> = {}): PreviousStepComponentDto {
  return {
    componentId: 'tool-a-v1',
    kind: 'tool',
    name: 'tool-a',
    version: 1,
    status: ComponentStatus.PUBLISHED,
    cwlChanged: false,
    canAddVersion: true,
    ...overrides,
  };
}

function step(overrides: Partial<WorkflowStepPreviewDto> = {}): WorkflowStepPreviewDto {
  return {
    stepId: 'a',
    origin: ComponentOrigin.ARCHIVE,
    runReference: 'a.cwl',
    suggestedName: 'a',
    description: 'From the doc: field',
    cwlContent: 'class: CommandLineTool',
    cwlType: 'CommandLineTool',
    dockerfileContent: null,
    dockerPullReference: null,
    ontologyUrl: null,
    parameters: [filePort('inp', ParameterDirection.INPUT), filePort('out', ParameterDirection.OUTPUT)],
    nameConflict: null,
    suggestedMatch: null,
    previous: null,
    ...overrides,
  };
}

describe('initialConfigState - a new workflow version starts from the previous one', () => {
  it('versions the tool a step ran when its CWL changed and the tool is yours', () => {
    expect(initialConfigState(step({ previous: previous({ cwlChanged: true }) })).mode).toBe('version');
  });

  it('reuses the same component when the CWL is unchanged', () => {
    const state = initialConfigState(step({ previous: previous() }));
    expect(state).toMatchObject({ mode: 'reuse', reuseComponentId: 'tool-a-v1', reuseName: 'tool-a', reuseVersion: 1 });
  });

  it('does not reuse a since deprecated component - the backend would refuse it', () => {
    const state = initialConfigState(step({ previous: previous({ status: ComponentStatus.DEPRECATED }) }));
    expect(state.mode).toBe('create');
  });

  it("falls back to the usual default when the changed tool isn't yours to version", () => {
    const suggestedMatch = {
      componentId: 'match',
      kind: 'tool' as const,
      name: 'matched',
      version: 2,
      domains: [],
      score: 0.9,
      status: ComponentStatus.PUBLISHED,
    };
    const changedForeign = previous({ cwlChanged: true, canAddVersion: false });

    expect(initialConfigState(step({ previous: changedForeign })).mode).toBe('create');
    expect(initialConfigState(step({ previous: changedForeign, suggestedMatch }))).toMatchObject({
      mode: 'reuse',
      reuseComponentId: 'match',
    });
  });

  it('keeps the old default for a step without a previous version', () => {
    expect(initialConfigState(step())).toMatchObject({ mode: 'create', name: 'a', description: 'From the doc: field' });
  });
});

describe('toConfigDto - a versioning step', () => {
  it("names the tool it versions, and sends only the labels written here - a blank one would clear the tool's", () => {
    const preview = step({ previous: previous({ cwlChanged: true }) });
    const state = { ...initialConfigState(preview), formatLabels: { 'input:inp': ' ', 'output:out': 'GeoTIFF' } };

    expect(toConfigDto(preview, state)).toEqual({
      stepId: 'a',
      newVersionOfId: 'tool-a-v1',
      description: 'From the doc: field',
      formatLabels: [{ name: 'out', direction: 'output', label: 'GeoTIFF' }],
    });
  });

  it('carries no name or domains - they are the lineage\'s', () => {
    const preview = step({ previous: previous({ cwlChanged: true }) });
    const dto = toConfigDto(preview, initialConfigState(preview));
    expect(dto).not.toHaveProperty('name');
    expect(dto).not.toHaveProperty('domains');
  });
});

describe('validateConfigs - a name already taken', () => {
  const preview = step();
  const configs = { a: { ...initialConfigState(preview), domains: ['animal_behavior'] } };

  it('names the component holding it when the user may see it', () => {
    const takenBy = {
      id: 'b',
      kind: 'tool' as const,
      name: 'a',
      version: 3,
      domains: [],
      status: ComponentStatus.PUBLISHED,
      createdAt: '2026-01-01T00:00:00Z',
      canAddVersion: false,
    };
    expect(validateConfigs([preview], configs, { a: { takenBy } }).a).toBe('A component named "a" already exists (v3).');
  });

  it("blocks the save even when the holder is someone else's draft the user may not see", () => {
    expect(validateConfigs([preview], configs, { a: { takenBy: null } }).a).toBe(
      'This name is already taken — choose a different name.',
    );
  });

  it('passes a free name', () => {
    expect(validateConfigs([preview], configs, { a: null })).toEqual({});
  });
});
