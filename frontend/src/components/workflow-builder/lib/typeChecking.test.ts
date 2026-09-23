import { describe, expect, it } from 'vitest';
import { ParameterDirection } from '@/api/components';
import {
  NO_DATA_INPUTS_SCORE,
  compareByRank,
  arePortsCompatible,
  checkPorts,
  collectFormatPairs,
  configParameters,
  dataInputs,
  dataOutputs,
  findPort,
  buildOutputStack,
  dataInputTypes,
  dataOutputTypes,
  isBooleanParameter,
  isCompatible,
  isNumericParameter,
  matchComponent,
  scoreComponent,
  type FormatLookup,
  type OutputFrame,
  type TypedParameter,
} from './typeChecking';
import type { ComponentFlowNode } from '../types';

let seq = 0;
const input = (cwlType: string, name = `in_${seq++}`): TypedParameter => ({
  name,
  cwlType,
  direction: ParameterDirection.INPUT,
});
const output = (cwlType: string, name = `out_${seq++}`): TypedParameter => ({
  name,
  cwlType,
  direction: ParameterDirection.OUTPUT,
});

const EDAM = 'http://ontology/edam_eo.owl';
const GEOJSON = 'http://edamontology.org/format_4106';
const GEOPACKAGE = 'http://edamontology.org/format_4107';
const VECTOR = 'http://edamontology.org/format_4126';
const SHAPEFILE = 'http://edamontology.org/format_4119';

/** a File port declaring `format` within `ontologyUrl` */
const formatted = (port: TypedParameter, format: string, ontologyUrl: string | null = EDAM): TypedParameter => ({
  ...port,
  format,
  ontologyUrl,
});

/** the format service, faked: GeoJSON and GeoPackage are vectors, nothing is a Shapefile */
const fakeService: FormatLookup = ({ actualFormat, expectedFormat }) =>
  expectedFormat === VECTOR && [GEOJSON, GEOPACKAGE].includes(actualFormat)
    ? true
    : expectedFormat === SHAPEFILE
      ? false
      : undefined;

const node = (id: string, label: string, parameters: TypedParameter[]): ComponentFlowNode => ({
  id,
  type: 'componentNode',
  position: { x: 0, y: 0 },
  // the pure functions only read cwlType/direction; the rest of ParameterDisplayModel is
  // irrelevant here, so the cast keeps the fixtures readable
  data: {
    componentId: id,
    label,
    domains: ['animal_behavior'],
    parameters: parameters as never,
    parameterValues: {},
  },
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

describe('isBooleanParameter / isNumericParameter', () => {
  it('recognises boolean, tolerating the optional marker and casing', () => {
    expect(isBooleanParameter(input('boolean'))).toBe(true);
    expect(isBooleanParameter(input('Boolean?'))).toBe(true);
    expect(isBooleanParameter(input('string'))).toBe(false);
  });

  it('recognises the CWL numeric scalars', () => {
    for (const t of ['int', 'long', 'float', 'double']) {
      expect(isNumericParameter(input(t))).toBe(true);
    }
    expect(isNumericParameter(input('double?'))).toBe(true);
    expect(isNumericParameter(input('string'))).toBe(false);
    expect(isNumericParameter(input('File'))).toBe(false);
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

  it('collects every File output port of a node', () => {
    const [frame] = buildOutputStack([node('a', 'split', [output('File'), output('File[]'), output('int')])]);
    expect(frame.outputs.map((p) => p.cwlType)).toEqual(['File', 'File[]']);
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
    { nodeId: 'b', componentName: 'remove-outliers', outputs: [output('File')] },
    { nodeId: 'a', componentName: 'load-tracking-data', outputs: [output('File[]')] },
  ];

  it('scores everything 0 with no frame when the canvas is empty', () => {
    expect(matchComponent([input('File')], [])).toEqual({ score: 0, frame: null, status: null });
  });

  it('scores a candidate with no data inputs below everything else', () => {
    const match = matchComponent([input('string'), output('File')], stack);
    expect(match.score).toBe(NO_DATA_INPUTS_SCORE);
    expect(match.frame).toBeNull();
  });

  it('gives the most recent matching frame the highest score', () => {
    // untyped ports: the types fit, the formats are unknown - an unverified match
    const match = matchComponent([input('File')], stack);
    expect(match.score).toBe(3);
    expect(match.frame?.componentName).toBe('remove-outliers');
    expect(match.status).toBe('unverified');
  });

  it('falls back to an older frame when the newest does not match', () => {
    // only File[] is accepted, which the newest frame (File) cannot satisfy
    const match = matchComponent([input('File[]')], stack);
    expect(match.score).toBe(1);
    expect(match.frame?.componentName).toBe('load-tracking-data');
  });

  it('scores 0 with no frame when nothing on the canvas matches', () => {
    const onlyArrays: OutputFrame[] = [{ nodeId: 'a', componentName: 'split', outputs: [output('File')] }];
    expect(matchComponent([input('File[]')], onlyArrays)).toEqual({ score: 0, frame: null, status: null });
  });

  it('ranks an unverified match just below a verified one in the same frame', () => {
    const geojson: OutputFrame[] = [
      { nodeId: 'a', componentName: 'load', outputs: [formatted(output('File'), GEOJSON)] },
    ];
    const verified = matchComponent([formatted(input('File'), VECTOR)], geojson, fakeService);
    const unverified = matchComponent([formatted(input('File'), VECTOR, 'http://other.org/o.owl')], geojson, fakeService);
    expect(verified).toMatchObject({ score: 2, status: 'compatible' });
    expect(unverified).toMatchObject({ score: 1, status: 'unverified' });
  });

  it('skips a frame whose formats the service rejects', () => {
    const frames: OutputFrame[] = [
      { nodeId: 'b', componentName: 'newest', outputs: [formatted(output('File'), GEOPACKAGE)] },
      { nodeId: 'a', componentName: 'oldest', outputs: [formatted(output('File'), SHAPEFILE)] },
    ];
    const match = matchComponent([formatted(input('File'), SHAPEFILE)], frames, fakeService);
    expect(match.frame?.componentName).toBe('oldest');
  });
});

describe('scoreComponent', () => {
  it('reports the score of the matching frame', () => {
    const stack: OutputFrame[] = [{ nodeId: 'a', componentName: 'load-data', outputs: [output('File')] }];
    expect(scoreComponent([input('File')], stack)).toBe(1);
    expect(scoreComponent([input('string')], stack)).toBe(NO_DATA_INPUTS_SCORE);
    expect(scoreComponent([input('File')], [])).toBe(0);
  });
});

describe('dataInputs / dataOutputs / configParameters', () => {
  const parameters = [
    input('File', 'input_rds'),
    input('string', 'accuracy_var'),
    input('double', 'max_speed'),
    output('File', 'output_rds'),
    output('File[]', 'artifacts'),
  ];

  it('splits File ports from config knobs', () => {
    expect(dataInputs(parameters).map((p) => p.name)).toEqual(['input_rds']);
    expect(dataOutputs(parameters).map((p) => p.name)).toEqual(['output_rds', 'artifacts']);
    expect(configParameters(parameters).map((p) => p.name)).toEqual(['accuracy_var', 'max_speed']);
  });

  it('never counts an output as a config parameter', () => {
    expect(configParameters([output('string', 'log_text')])).toEqual([]);
  });
});

describe('findPort', () => {
  const parameters = [input('File', 'input_rds'), output('File', 'output_rds')];

  it('resolves a handle id to its parameter', () => {
    expect(findPort(parameters, 'output_rds')?.name).toBe('output_rds');
  });

  it('returns undefined for a missing or absent handle id', () => {
    expect(findPort(parameters, 'gone')).toBeUndefined();
    expect(findPort(parameters, null)).toBeUndefined();
    expect(findPort(parameters, undefined)).toBeUndefined();
  });
});

describe('arePortsCompatible', () => {
  it('accepts a File output feeding a File input', () => {
    expect(arePortsCompatible(output('File'), input('File'))).toBe(true);
  });

  it('accepts File[] feeding File (scatter case)', () => {
    expect(arePortsCompatible(output('File[]'), input('File'))).toBe(true);
  });

  it('rejects mismatched arities', () => {
    expect(arePortsCompatible(output('File'), input('File[]'))).toBe(false);
  });

  it('rejects config parameters as connection endpoints', () => {
    expect(arePortsCompatible(output('string'), input('File'))).toBe(false);
    expect(arePortsCompatible(output('File'), input('string'))).toBe(false);
  });

  it('rejects a backwards connection (input as source, output as target)', () => {
    expect(arePortsCompatible(input('File'), output('File'))).toBe(false);
  });

  it('rejects a missing port on either side', () => {
    expect(arePortsCompatible(undefined, input('File'))).toBe(false);
    expect(arePortsCompatible(output('File'), undefined)).toBe(false);
  });
});

describe('checkPorts', () => {
  it('is incompatible when the cwlTypes do not fit, whatever the formats', () => {
    const check = checkPorts(formatted(output('File'), GEOJSON), formatted(input('File[]'), GEOJSON), fakeService);
    expect(check).toEqual({ status: 'incompatible' });
  });

  it('is unverified - not compatible - when the input declares no format', () => {
    // e.g. an .rds input: no ontology covers it, so a GeoJSON output only *might* fit
    expect(checkPorts(formatted(output('File'), GEOJSON), input('File'))).toEqual({
      status: 'unverified',
      reason: 'missing-input-format',
    });
  });

  it('is unverified when neither port declares a format', () => {
    expect(checkPorts(output('File'), input('File'))).toEqual({ status: 'unverified', reason: 'missing-formats' });
  });

  it('is unverified when only the input declares a format', () => {
    expect(checkPorts(output('File'), formatted(input('File'), VECTOR))).toEqual({
      status: 'unverified',
      reason: 'missing-output-format',
    });
  });

  it('is unverified across ontologies', () => {
    const other = formatted(input('File'), VECTOR, 'http://other.org/o.owl');
    expect(checkPorts(formatted(output('File'), GEOJSON), other, fakeService).reason).toBe('different-ontology');
  });

  it('is unverified when a format belongs to no known ontology', () => {
    // e.g. `format: rds` in a CWL without $schemas
    const rds = formatted(input('File'), 'rds', null);
    expect(checkPorts(formatted(output('File'), GEOJSON), rds, fakeService)).toEqual({
      status: 'unverified',
      reason: 'unknown-ontology',
    });
  });

  it('is compatible for identical formats without asking the service', () => {
    const neverCalled: FormatLookup = () => {
      throw new Error('lookup should not be consulted');
    };
    const check = checkPorts(formatted(output('File'), GEOJSON), formatted(input('File'), GEOJSON), neverCalled);
    expect(check).toEqual({ status: 'compatible' });
  });

  it('follows the service for different formats in one ontology', () => {
    const out = formatted(output('File'), GEOPACKAGE);
    expect(checkPorts(out, formatted(input('File'), VECTOR), fakeService)).toEqual({ status: 'compatible' });
    expect(checkPorts(out, formatted(input('File'), SHAPEFILE), fakeService)).toEqual({ status: 'incompatible' });
  });

  it('is unverified while the service has not answered', () => {
    const check = checkPorts(formatted(output('File'), GEOPACKAGE), formatted(input('File'), VECTOR));
    expect(check).toEqual({ status: 'unverified', reason: 'not-checked' });
  });

  it('only lets a definite service "no" block a connection', () => {
    const out = formatted(output('File'), GEOPACKAGE);
    expect(arePortsCompatible(out, formatted(input('File'), VECTOR))).toBe(true);
    expect(arePortsCompatible(out, formatted(input('File'), SHAPEFILE), fakeService)).toBe(false);
  });
});

describe('collectFormatPairs', () => {
  it('returns each distinct question the service has to answer, and nothing decidable locally', () => {
    const outputs = [formatted(output('File'), GEOJSON), formatted(output('File'), GEOJSON), output('File')];
    const inputs = [
      formatted(input('File'), VECTOR),
      formatted(input('File'), GEOJSON), // identical format - decided locally
      input('File'), // no format - unverifiable
      formatted(input('File'), VECTOR, 'http://other.org/o.owl'), // another ontology
    ];
    expect(collectFormatPairs(outputs, inputs)).toEqual([
      { actualFormat: GEOJSON, expectedFormat: VECTOR, ontologyUrl: EDAM },
    ]);
  });
});

describe('compareByRank', () => {
  const candidate = (name: string, score: number, isFavorite = false) => ({
    component: { name, isFavorite },
    match: { score, frame: null, status: null },
  });

  const order = (items: ReturnType<typeof candidate>[]) =>
    [...items].sort(compareByRank).map((c) => c.component.name);

  it('ranks a higher compatibility score first', () => {
    expect(order([candidate('low', 1), candidate('high', 3)])).toEqual(['high', 'low']);
  });

  it('puts favourites first within the same score bucket', () => {
    expect(order([candidate('plain', 2), candidate('starred', 2, true)])).toEqual([
      'starred',
      'plain',
    ]);
  });

  it('never lets a favourite outrank a better-matching component', () => {
    // the whole point of the tie-break: favourites order within a bucket, not across
    expect(order([candidate('starred-but-worse', 1, true), candidate('better', 3)])).toEqual([
      'better',
      'starred-but-worse',
    ]);
  });

  it('falls back to name order for equal score and favourite state', () => {
    expect(order([candidate('beta', 2), candidate('alpha', 2)])).toEqual(['alpha', 'beta']);
  });

  it('keeps favourites ahead among the no-data-input bucket too', () => {
    expect(
      order([
        candidate('plain', NO_DATA_INPUTS_SCORE),
        candidate('starred', NO_DATA_INPUTS_SCORE, true),
      ]),
    ).toEqual(['starred', 'plain']);
  });

  it('orders a full mixed palette correctly', () => {
    expect(
      order([
        candidate('zeta-no-match', 0),
        candidate('alpha-no-inputs', NO_DATA_INPUTS_SCORE),
        candidate('beta-best', 2),
        candidate('alpha-best-fav', 2, true),
        candidate('gamma-no-match-fav', 0, true),
      ]),
    ).toEqual([
      'alpha-best-fav',
      'beta-best',
      'gamma-no-match-fav',
      'zeta-no-match',
      'alpha-no-inputs',
    ]);
  });
});
