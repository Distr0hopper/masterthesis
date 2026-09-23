import { ParameterDirection } from '@/api/components';
import type { ComponentFlowNode } from '../types';

/**
 * Pure type-checking core for the workflow builder. Deliberately free of React and of
 * the API layer's fetching code: everything here is a plain function over plain data.
 */

/** Structural minimum a parameter has to satisfy - fits both ParameterDto and ParameterDisplayModel. */
export interface TypedParameter {
  name: string;
  cwlType: string;
  direction: ParameterDirection;
  /** ontology format URI, e.g. http://edamontology.org/format_4106 - absent on untyped ports */
  format?: string | null;
  /** the component's ontology; formats are only comparable when both ports share it */
  ontologyUrl?: string | null;
}

/**
 * - `compatible`: the types fit, and the formats are identical or the format service said they fit
 * - `incompatible`: the types don't fit, or the format service said the formats don't
 * - `unverified`: the types fit but the formats couldn't be checked - allowed, but flagged.
 *   A port without a format is unknown, not "accepts anything": File -> File only *might* fit.
 */
export type ConnectionStatus = 'compatible' | 'incompatible' | 'unverified';

export type UnverifiedReason =
  | 'missing-formats'
  | 'missing-input-format'
  | 'missing-output-format'
  | 'unknown-ontology'
  | 'different-ontology'
  | 'not-checked';

export const UNVERIFIED_REASON_TEXT: Record<UnverifiedReason, string> = {
  'missing-formats': 'Neither port declares a format, so they may or may not fit.',
  'missing-input-format': 'The input declares no format, so it cannot be checked against the output’s format.',
  'missing-output-format': 'The output declares no format, so it cannot be checked against the input’s format.',
  'unknown-ontology': 'A format is not from a known ontology ($schemas), so it cannot be checked.',
  'different-ontology': 'The components use different ontologies ($schemas), so their formats cannot be compared.',
  'not-checked': 'The format service could not check these formats.',
};

export interface PortCheck {
  status: ConnectionStatus;
  /** why the check was inconclusive - set only when status is `unverified` */
  reason?: UnverifiedReason;
}

/** One question for the format service: may an output of `actualFormat` feed an input of `expectedFormat`? */
export interface FormatPair {
  actualFormat: string;
  expectedFormat: string;
  ontologyUrl: string;
}

/** The format service's answer for a pair, or undefined while unknown (not fetched yet, or it failed). */
export type FormatLookup = (pair: FormatPair) => boolean | undefined;

/** A lookup that knows nothing - every format question stays unverified. */
export const noFormatLookup: FormatLookup = () => undefined;

export interface OutputFrame {
  nodeId: string;
  componentName: string;
  /** every File-ish output port this node produces */
  outputs: TypedParameter[];
}

export interface CompatibilityMatch {
  score: number;
  /** the stack frame that produced the score, or null when nothing matched */
  frame: OutputFrame | null;
  /** whether that frame's best match was format-checked - null when nothing matched */
  status: Exclude<ConnectionStatus, 'incompatible'> | null;
}

/** score for a candidate that has no data inputs at all - sorts below "no match" */
export const NO_DATA_INPUTS_SCORE = -1;

/**
 * Only File/File[] parameters are data connections. string/int/double/boolean are
 * configuration knobs and take no part in compatibility ranking.
 */
const FILE_TYPE = /^File/i;

/** CWL numeric scalars - the inspector renders these as a number input, not free text. */
const NUMERIC_CWL_TYPES = new Set(['int', 'long', 'float', 'double']);

/** Drop the CWL optional marker and normalise case/whitespace for comparison. */
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

export function dataInputTypes(parameters: TypedParameter[]): string[] {
  return dataInputs(parameters).map((p) => p.cwlType);
}

export function dataOutputTypes(parameters: TypedParameter[]): string[] {
  return dataOutputs(parameters).map((p) => p.cwlType);
}

/**
 * Structural compatibility of two cwlTypes: normalised string equality, plus the one
 * special case below. The format-aware part lives in {@link checkPorts}.
 */
export function isCompatible(outputType: string, inputType: string): boolean {
  const out = normalizeCwlType(outputType);
  const inp = normalizeCwlType(inputType);

  if (out === inp) return true;

  // file[] -> file: a scatter step would fan the array out over repeated invocations.
  // TODO: Counted as compatible for now; proper scatter handling is its own task.
  if (out === 'file[]' && inp === 'file') return true;

  return false;
}

/** Look one port up by the handle id carried on an edge (handle id === parameter name). */
export function findPort<T extends TypedParameter>(
  parameters: T[],
  handleId: string | null | undefined,
): T | undefined {
  if (!handleId) return undefined;
  return parameters.find((p) => p.name === handleId);
}

/** Whether the ports are a File output feeding a File input whose cwlTypes fit. */
function structurallyCompatible(sourcePort: TypedParameter, targetPort: TypedParameter): boolean {
  if (!isDataParameter(sourcePort) || !isDataParameter(targetPort)) return false;
  if (sourcePort.direction !== ParameterDirection.OUTPUT) return false;
  if (targetPort.direction !== ParameterDirection.INPUT) return false;
  return isCompatible(sourcePort.cwlType, targetPort.cwlType);
}

/**
 * The format question a connection has to put to the format service, or null when it can
 * be decided without one - see {@link checkPorts} for the order the rules apply in.
 */
export function formatPairFor(sourcePort: TypedParameter, targetPort: TypedParameter): FormatPair | null {
  if (!structurallyCompatible(sourcePort, targetPort)) return null;
  if (!targetPort.format || !sourcePort.format) return null;
  if (!sourcePort.ontologyUrl || sourcePort.ontologyUrl !== targetPort.ontologyUrl) return null;
  if (sourcePort.format === targetPort.format) return null;
  return { actualFormat: sourcePort.format, expectedFormat: targetPort.format, ontologyUrl: sourcePort.ontologyUrl };
}

/**
 * Whether one concrete output port may feed one concrete input port. Follows CWL's own
 * semantics, in order:
 *
 * 1. the cwlTypes must fit (File -> File, File[] -> File, ...) - otherwise incompatible
 * 2. a port without a format can't be checked - unverified.
 * 3. a format outside any known ontology (no $schemas), or formats from two different
 *    ontologies, can't be compared - unverified
 * 4. identical formats - compatible
 * 5. otherwise the format service decides (via `lookup`) - unverified until it has
 */
export function checkPorts(
  sourcePort: TypedParameter | undefined,
  targetPort: TypedParameter | undefined,
  lookup: FormatLookup = noFormatLookup,
): PortCheck {
  if (!sourcePort || !targetPort || !structurallyCompatible(sourcePort, targetPort)) {
    return { status: 'incompatible' };
  }
  if (!sourcePort.format && !targetPort.format) return { status: 'unverified', reason: 'missing-formats' };
  if (!targetPort.format) return { status: 'unverified', reason: 'missing-input-format' };
  if (!sourcePort.format) return { status: 'unverified', reason: 'missing-output-format' };
  if (!sourcePort.ontologyUrl || !targetPort.ontologyUrl) return { status: 'unverified', reason: 'unknown-ontology' };
  if (sourcePort.ontologyUrl !== targetPort.ontologyUrl) return { status: 'unverified', reason: 'different-ontology' };
  if (sourcePort.format === targetPort.format) return { status: 'compatible' };

  const answer = lookup(formatPairFor(sourcePort, targetPort)!);
  if (answer === undefined) return { status: 'unverified', reason: 'not-checked' };
  return { status: answer ? 'compatible' : 'incompatible' };
}

/** Whether a connection may be drawn at all - only a definite `incompatible` blocks it. */
export function arePortsCompatible(
  sourcePort: TypedParameter | undefined,
  targetPort: TypedParameter | undefined,
  lookup: FormatLookup = noFormatLookup,
): boolean {
  return checkPorts(sourcePort, targetPort, lookup).status !== 'incompatible';
}

/** Stable identity of a pair - the key the format service's answers are stored under. */
export function formatPairKey(pair: FormatPair): string {
  return `${pair.ontologyUrl}|${pair.actualFormat}|${pair.expectedFormat}`;
}

/** Every distinct format question between any of `outputs` and any of `inputs`. */
export function collectFormatPairs(outputs: TypedParameter[], inputs: TypedParameter[]): FormatPair[] {
  const pairs = new Map<string, FormatPair>();
  for (const out of outputs) {
    for (const inp of inputs) {
      const pair = formatPairFor(out, inp);
      if (pair) pairs.set(formatPairKey(pair), pair);
    }
  }
  return [...pairs.values()];
}

/**
 * Available outputs on the canvas, most-recently-added node first. Insertion order, not
 * visual left-to-right position. Nodes with no File outputs contribute nothing and are dropped.
 */
export function buildOutputStack(nodes: ComponentFlowNode[]): OutputFrame[] {
  return [...nodes]
    .reverse()
    .map((node) => ({
      nodeId: node.id,
      componentName: node.data.label,
      outputs: dataOutputs(node.data.parameters),
    }))
    .filter((frame) => frame.outputs.length > 0);
}

/**
 * Rank one candidate against the canvas. Higher is better; the most recent frame that
 * matches wins. Within a frame a format-checked match outranks an unverified one, so the
 * top frame scores `2 * stack.length` (verified) or one less, and the oldest 2 or 1.
 */
export function matchComponent(
  candidateParameters: TypedParameter[],
  outputStack: OutputFrame[],
  lookup: FormatLookup = noFormatLookup,
): CompatibilityMatch {
  // nothing on the canvas yet -> everything ranks equally, list stays alphabetical
  if (outputStack.length === 0) return { score: 0, frame: null, status: null };

  const inputs = dataInputs(candidateParameters);
  if (inputs.length === 0) return { score: NO_DATA_INPUTS_SCORE, frame: null, status: null };

  for (let i = 0; i < outputStack.length; i++) {
    const frame = outputStack[i];
    const statuses = frame.outputs.flatMap((out) => inputs.map((inp) => checkPorts(out, inp, lookup).status));
    const frameScore = 2 * (outputStack.length - i);
    if (statuses.includes('compatible')) return { score: frameScore, frame, status: 'compatible' };
    if (statuses.includes('unverified')) return { score: frameScore - 1, frame, status: 'unverified' };
  }

  return { score: 0, frame: null, status: null };
}

/** The fields the palette ordering reads off a candidate. */
export interface RankableComponent {
  name: string;
  isFavorite: boolean;
}

export interface RankedCandidate {
  component: RankableComponent;
  match: CompatibilityMatch;
}

/**
 * Palette ordering: compatibility score first, then favourites, then name.
 *
 * Favourites deliberately only break a tie *within* a score bucket - a favourite must
 * never outrank a component that fits the canvas better, or the ranking stops meaning
 * anything.
 */
export function compareByRank(a: RankedCandidate, b: RankedCandidate): number {
  return (
    b.match.score - a.match.score ||
    Number(b.component.isFavorite) - Number(a.component.isFavorite) ||
    a.component.name.localeCompare(b.component.name)
  );
}

/** Score-only view of {@link matchComponent}. */
export function scoreComponent(
  candidateParameters: TypedParameter[],
  outputStack: OutputFrame[],
  lookup: FormatLookup = noFormatLookup,
): number {
  return matchComponent(candidateParameters, outputStack, lookup).score;
}
