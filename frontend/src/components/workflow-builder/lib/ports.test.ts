import { describe, expect, it } from 'vitest';
import {
  FormatLabelSource,
  ParameterDirection,
  isManualFormatLabel,
  type ParameterDisplayModel,
} from '@/api/components';
import { formatNoteFor } from './ports';

const port = (overrides: Partial<ParameterDisplayModel>): ParameterDisplayModel => ({
  id: 'p',
  name: 'input_rds',
  cwlType: 'File',
  defaultValue: null,
  description: null,
  format: null,
  formatLabel: null,
  ontologyUrl: null,
  formatLabelSource: null,
  acceptsManualFormatLabel: true,
  direction: ParameterDirection.INPUT,
  directionDisplay: 'Input',
  ...overrides,
});

const BAM = { format: 'http://edamontology.org/format_2572', formatLabel: 'BAM' };

describe('isManualFormatLabel', () => {
  it('reads the backend decision', () => {
    expect(isManualFormatLabel(port({ formatLabel: 'RDS', formatLabelSource: FormatLabelSource.MANUAL }))).toBe(true);
    expect(isManualFormatLabel(port({ ...BAM, formatLabelSource: FormatLabelSource.ONTOLOGY }))).toBe(false);
    expect(isManualFormatLabel(port({}))).toBe(false);
  });
});

describe('formatNoteFor', () => {
  it('explains a manual label', () => {
    const rds = port({ formatLabel: 'RDS', formatLabelSource: FormatLabelSource.MANUAL });
    expect(formatNoteFor(rds)).toContain('"RDS" was entered by hand');
  });

  it('explains a missing or non-ontology format', () => {
    expect(formatNoteFor(port({}))).toContain('No format declared');
    expect(formatNoteFor(port({ format: 'rds' }))).toContain('"rds" is not an ontology format');
  });

  it('says nothing for an ontology format with its label', () => {
    expect(formatNoteFor(port({ ...BAM, formatLabelSource: FormatLabelSource.ONTOLOGY }))).toBeNull();
  });

  it('explains an ontology format whose name is missing', () => {
    const raster = port({ format: 'http://edamontology.org/format_4125', formatLabelSource: FormatLabelSource.UNRESOLVED });
    expect(formatNoteFor(raster)).toContain('name could not be looked up');
  });

  it('says nothing for canvases saved before formatLabelSource existed', () => {
    const legacy = port({ ...BAM });
    delete (legacy as Partial<ParameterDisplayModel>).formatLabelSource;
    expect(formatNoteFor(legacy)).toBeNull();
  });
});
