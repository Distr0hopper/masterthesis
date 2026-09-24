import { describe, expect, it } from 'vitest';
import { ParameterDirection } from '@/api/components';
import {
  configParameters,
  dataInputs,
  dataOutputs,
  findPort,
  isBooleanParameter,
  isNumericParameter,
  type TypedParameter,
} from './portKinds';

// Connection checks and palette ranking live in the backend now - their cases moved to
// backend-python/tests/domain (test_port_check.py, test_ranking.py).

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

