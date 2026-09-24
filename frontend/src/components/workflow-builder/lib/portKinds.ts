import { ParameterDirection } from '@/api/components';

/**
 * Port classification for drawing the builder - which parameters are connectable data
 * ports and which are configuration knobs.
 *
 * The type checking itself (whether a connection fits, and how the palette ranks against
 * the canvas) is decided by the backend: see app/domain/compatibility, reached through
 * `useConnectionChecks` / `checkConnection` and the list endpoint's `rankAgainst`.
 */

/** Structural minimum a parameter has to satisfy - fits both ParameterDto and ParameterDisplayModel. */
export interface TypedParameter {
  name: string;
  cwlType: string;
  direction: ParameterDirection;
}

/** A palette candidate with no data inputs at all - the backend scores these below "no match". */
export const NO_DATA_INPUTS_SCORE = -1;

/**
 * Only File/File[] parameters are data connections. string/int/double/boolean are
 * configuration knobs, given a value in the inspector rather than connected.
 */
const FILE_TYPE = /^File/i;

/** CWL numeric scalars - the inspector renders these as a number input, not free text. */
const NUMERIC_CWL_TYPES = new Set(['int', 'long', 'float', 'double']);

/** Drop the CWL optional marker and normalise case/whitespace. */
function normalizeCwlType(cwlType: string): string {
  return cwlType.replace('?', '').trim().toLowerCase();
}

export function isDataParameter(parameter: TypedParameter): boolean {
  return FILE_TYPE.test(parameter.cwlType);
}

/** A `boolean` config parameter (an optional `boolean?` counts too). */
export function isBooleanParameter(parameter: TypedParameter): boolean {
  return normalizeCwlType(parameter.cwlType) === 'boolean';
}

/** An `int`/`long`/`float`/`double` config parameter (optional marker tolerated). */
export function isNumericParameter(parameter: TypedParameter): boolean {
  return NUMERIC_CWL_TYPES.has(normalizeCwlType(parameter.cwlType));
}

function portsFor<T extends TypedParameter>(parameters: T[], direction: ParameterDirection): T[] {
  return parameters.filter((p) => p.direction === direction && isDataParameter(p));
}

/** File-typed inputs - the connectable target ports of a node. */
export function dataInputs<T extends TypedParameter>(parameters: T[]): T[] {
  return portsFor(parameters, ParameterDirection.INPUT);
}

/** File-typed outputs - the connectable source ports of a node. */
export function dataOutputs<T extends TypedParameter>(parameters: T[]): T[] {
  return portsFor(parameters, ParameterDirection.OUTPUT);
}

/**
 * Non-File inputs: string/int/double/boolean knobs. These are never connected, they are
 * given a value in the inspector panel.
 */
export function configParameters<T extends TypedParameter>(parameters: T[]): T[] {
  return parameters.filter((p) => p.direction === ParameterDirection.INPUT && !isDataParameter(p));
}

/** Look one port up by the handle id carried on an edge (handle id === parameter name). */
export function findPort<T extends TypedParameter>(
  parameters: T[],
  handleId: string | null | undefined,
): T | undefined {
  if (!handleId) return undefined;
  return parameters.find((p) => p.name === handleId);
}
