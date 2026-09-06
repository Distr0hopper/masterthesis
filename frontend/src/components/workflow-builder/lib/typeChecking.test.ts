import { describe, expect, it } from 'vitest';
import { ParameterDirection } from '@/api/components';
import {
  NO_DATA_INPUTS_SCORE,
  areParametersCompatible,
  buildOutputStack,
  dataInputTypes,
  dataOutputTypes,
  isCompatible,
  matchComponent,
  scoreComponent,
  type OutputFrame,
  type TypedParameter,
} from './typeChecking';
import type { ComponentFlowNode } from '../types';

const input = (cwlType: string): TypedParameter => ({ cwlType, direction: ParameterDirection.INPUT });
const output = (cwlType: string): TypedParameter => ({ cwlType, direction: ParameterDirection.OUTPUT });

const node = (id: string, label: string, parameters: TypedParameter[]): ComponentFlowNode => ({
  id,
  type: 'componentNode',
  position: { x: 0, y: 0 },
  // the pure functions only read cwlType/direction; the rest of ParameterDisplayModel is
  // irrelevant here, so the cast keeps the fixtures readable
  data: { componentId: id, label, domain: 'animal_behavior', parameters: parameters as never },
});

describe('isCompatible', () => {
  it('matches identical types', () => {
    expect(isCompatible('File', 'File')).toBe(true);
    expect(isCompatible('File[]', 'File[]')).toBe(true);
  });

  it('is case-insensitive and ignores surrounding whitespace', () => {
    expect(isCompatible('file', ' File ')).toBe(true);
  });

  it('treats an optional File as a plain File', () => {
    expect(isCompatible('File?', 'File')).toBe(true);
    expect(isCompatible('File', 'File?')).toBe(true);
  });

  it('accepts File[] feeding a File (scatter case, revisited later)', () => {
    expect(isCompatible('File[]', 'File')).toBe(true);
  });

  it('rejects a File feeding a File[]', () => {
    expect(isCompatible('File', 'File[]')).toBe(false);
  });

  it('rejects unrelated types', () => {
    expect(isCompatible('string', 'File')).toBe(false);
    expect(isCompatible('File', 'int')).toBe(false);
  });
});

describe('dataInputTypes / dataOutputTypes', () => {
  const parameters = [
    input('File'),
    input('string'),
    input('double'),
    output('File'),
    output('File[]'),
    output('boolean'),
  ];

  it('keeps only File-ish parameters of the requested direction', () => {
    expect(dataInputTypes(parameters)).toEqual(['File']);
    expect(dataOutputTypes(parameters)).toEqual(['File', 'File[]']);
  });

  it('ignores configuration parameters entirely', () => {
    expect(dataInputTypes([input('string'), input('int')])).toEqual([]);
  });
});

describe('buildOutputStack', () => {
  it('orders frames most-recently-added first', () => {
    const stack = buildOutputStack([
      node('a', 'load-data', [output('File')]),
      node('b', 'remove-outliers', [output('File')]),
    ]);
    expect(stack.map((f) => f.componentName)).toEqual(['remove-outliers', 'load-data']);
  });

  it('drops nodes that produce no File outputs', () => {
    const stack = buildOutputStack([
      node('a', 'load-data', [output('File')]),
      node('b', 'print-summary', [output('string')]),
    ]);
    expect(stack.map((f) => f.nodeId)).toEqual(['a']);
  });

  it('collects every File output type of a node', () => {
    const [frame] = buildOutputStack([node('a', 'split', [output('File'), output('File[]'), output('int')])]);
    expect(frame.outputTypes).toEqual(['File', 'File[]']);
  });

  it('returns an empty stack for an empty canvas', () => {
    expect(buildOutputStack([])).toEqual([]);
  });

  it('does not mutate the input array', () => {
    const nodes = [node('a', 'first', [output('File')]), node('b', 'second', [output('File')])];
    buildOutputStack(nodes);
    expect(nodes.map((n) => n.id)).toEqual(['a', 'b']);
  });
});

describe('matchComponent', () => {
  const stack: OutputFrame[] = [
    { nodeId: 'b', componentName: 'remove-outliers', outputTypes: ['File'] },
    { nodeId: 'a', componentName: 'load-tracking-data', outputTypes: ['File[]'] },
  ];

  it('scores everything 0 with no frame when the canvas is empty', () => {
    expect(matchComponent([input('File')], [])).toEqual({ score: 0, frame: null });
  });

  it('scores a candidate with no data inputs below everything else', () => {
    const match = matchComponent([input('string'), output('File')], stack);
    expect(match.score).toBe(NO_DATA_INPUTS_SCORE);
    expect(match.frame).toBeNull();
  });

  it('gives the most recent matching frame the highest score', () => {
    const match = matchComponent([input('File')], stack);
    expect(match.score).toBe(2);
    expect(match.frame?.componentName).toBe('remove-outliers');
  });

  it('falls back to an older frame when the newest does not match', () => {
    // only File[] is accepted, which the newest frame (File) cannot satisfy
    const match = matchComponent([input('File[]')], stack);
    expect(match.score).toBe(1);
    expect(match.frame?.componentName).toBe('load-tracking-data');
  });

  it('scores 0 with no frame when nothing on the canvas matches', () => {
    const onlyArrays: OutputFrame[] = [{ nodeId: 'a', componentName: 'split', outputTypes: ['File'] }];
    expect(matchComponent([input('File[]')], onlyArrays)).toEqual({ score: 0, frame: null });
  });
});

describe('scoreComponent', () => {
  it('reports the score of the matching frame', () => {
    const stack: OutputFrame[] = [{ nodeId: 'a', componentName: 'load-data', outputTypes: ['File'] }];
    expect(scoreComponent([input('File')], stack)).toBe(1);
    expect(scoreComponent([input('string')], stack)).toBe(NO_DATA_INPUTS_SCORE);
    expect(scoreComponent([input('File')], [])).toBe(0);
  });
});

describe('areParametersCompatible', () => {
  it('accepts a connection when any File output feeds any File input', () => {
    expect(areParametersCompatible([output('File'), output('int')], [input('string'), input('File')])).toBe(true);
  });

  it('rejects a connection when the source produces no File outputs', () => {
    expect(areParametersCompatible([output('string')], [input('File')])).toBe(false);
  });

  it('rejects a connection when the target takes no File inputs', () => {
    expect(areParametersCompatible([output('File')], [input('string')])).toBe(false);
  });

  it('rejects mismatched File arities', () => {
    expect(areParametersCompatible([output('File')], [input('File[]')])).toBe(false);
  });
});
