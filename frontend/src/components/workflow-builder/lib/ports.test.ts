import { describe, expect, it } from 'vitest';
import { ParameterDirection, isManualFormatLabel, type ParameterDisplayModel } from '@/api/components';
import { formatNoteFor } from './ports';

const EDAM = 'http://ontology/edam_eo.owl';

const port = (overrides: Partial<ParameterDisplayModel>): ParameterDisplayModel => ({
  id: 'p',
  name: 'input_rds',
  cwlType: 'File',
  defaultValue: null,
  description: null,
  format: null,
  formatLabel: null,
  ontologyUrl: null,
  direction: ParameterDirection.INPUT,
  directionDisplay: 'Input',
  ...overrides,
});

describe('isManualFormatLabel', () => {
  it('flags a label on a port without an ontology format', () => {
    expect(isManualFormatLabel(port({ formatLabel: 'RDS' }))).toBe(true);
    expect(isManualFormatLabel(port({ format: 'rds', formatLabel: 'RDS' }))).toBe(true);
  });

  it('does not flag a label resolved from the ontology', () => {
    const bam = port({ format: 'http://edamontology.org/format_2572', formatLabel: 'BAM', ontologyUrl: EDAM });
    expect(isManualFormatLabel(bam)).toBe(false);
  });

  it('does not flag labels from canvases saved before ontologyUrl existed', () => {
    const legacy = port({ format: 'http://edamontology.org/format_2572', formatLabel: 'BAM' });
    delete (legacy as Partial<ParameterDisplayModel>).ontologyUrl;
    expect(isManualFormatLabel(legacy)).toBe(false);
  });

  it('is false without a label', () => {
    expect(isManualFormatLabel(port({}))).toBe(false);
  });
});

describe('formatNoteFor', () => {
  it('explains a manual label', () => {
    expect(formatNoteFor(port({ formatLabel: 'RDS' }))).toContain('"RDS" was entered by hand');
  });

  it('explains a missing or non-ontology format', () => {
    expect(formatNoteFor(port({}))).toContain('No format declared');
    expect(formatNoteFor(port({ format: 'rds' }))).toContain('"rds" is not an ontology format');
  });

  it('says nothing for an ontology format', () => {
    const bam = port({ format: 'http://edamontology.org/format_2572', formatLabel: 'BAM', ontologyUrl: EDAM });
    expect(formatNoteFor(bam)).toBeNull();
  });
});
