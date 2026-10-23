import { describe, expect, it } from 'vitest';
import { verifyOtpFormSchema } from '@/api/auth/schema';
import { MAX_DESCRIPTION_LENGTH } from '@/api/schema';
import {
  ComponentCommand,
  ComponentKind,
  ComponentSource,
  ComponentStatus,
  FormatLabelSource,
  ParameterDirection,
} from '@/api/components/types';
import { ToolCommand } from '@/api/tools/types';
import { StepMatchStatus, WorkflowStepCommand } from '@/api/workflows/types';
// the mono-repo's checked-in spec, generated from the backend (make openapi)
import openapi from '../../../openapi.json';

/**
 * The frontend's copies of what the backend defines - its enums and its input limits -
 * held against the checked-in openapi.json, which the backend tests in turn keep equal to
 * what the API serves. A value added on one side only fails here, not as a 422 or a
 * silently unknown status in the UI.
 */

interface Schema {
  enum?: string[];
  properties?: Record<string, unknown>;
}

const schemas = (openapi as unknown as { components: { schemas: Record<string, Schema> } }).components.schemas;

function enumOf(name: string): string[] {
  const values = schemas[name]?.enum;
  if (!values) throw new Error(`openapi.json has no enum ${name}`);
  return [...values].sort();
}

const values = (constants: Record<string, string>) => Object.values(constants).sort();

describe('the enums mirror the backend', () => {
  it.each([
    ['ComponentCommandType', ComponentCommand],
    ['ToolCommandType', ToolCommand],
    ['WorkflowStepCommandType', WorkflowStepCommand],
    ['ComponentKind', ComponentKind],
    ['ComponentSource', ComponentSource],
    ['ComponentStatus', ComponentStatus],
    ['FormatLabelSource', FormatLabelSource],
    ['ParameterDirection', ParameterDirection],
    ['StepMatchStatus', StepMatchStatus],
  ])('%s', (backendName, frontendConstants) => {
    expect(values(frontendConstants as Record<string, string>)).toEqual(enumOf(backendName));
  });
});

/** every `maxLength` the backend puts on a property called `property`, across all DTOs */
function maxLengthsOf(property: string): Set<number> {
  const found = new Set<number>();
  for (const schema of Object.values(schemas)) {
    const definition = schema.properties?.[property];
    for (const match of JSON.stringify(definition ?? {}).matchAll(/"maxLength":(\d+)/g)) found.add(Number(match[1]));
  }
  return found;
}

describe('the input limits mirror the backend', () => {
  it('allows exactly as long a description as every DTO taking one', () => {
    expect(maxLengthsOf('description')).toEqual(new Set([MAX_DESCRIPTION_LENGTH]));
  });

  it('accepts exactly the login codes the backend does', () => {
    const code = schemas.VerifyOtpDto.properties?.code as { pattern: string } | undefined;
    if (!code) throw new Error('openapi.json has no VerifyOtpDto.code');
    const backend = new RegExp(code.pattern);
    for (const code of ['123456', '000000', '12345', '1234567', 'abcdef', '12 456', '']) {
      expect(verifyOtpFormSchema.safeParse({ code }).success, code).toBe(backend.test(code));
    }
  });
});
