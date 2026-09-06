import { ParameterDirection } from '@/api/components';
import type { ComponentFlowNode } from '../types';

/**
 * Pure type-checking core for the workflow builder. Deliberately free of React and of
 * the API layer's fetching code: everything here is a plain function over plain data.
 */

/** Structural minimum a parameter has to satisfy - fits both ParameterDto and ParameterDisplayModel. */
export interface TypedParameter {
  cwlType: string;
  direction: ParameterDirection;
}

export interface OutputFrame {
  nodeId: string;
  componentName: string;
  /** every File-ish output cwlType this node produces */
  outputTypes: string[];
}

export interface CompatibilityMatch {
  score: number;
  /** the stack frame that produced the score, or null when nothing matched */
  frame: OutputFrame | null;
}

/** score for a candidate that has no data inputs at all - sorts below "no match" */
export const NO_DATA_INPUTS_SCORE = -1;

/**
 * Only File/File[] parameters are data connections. string/int/double/boolean are
 * configuration knobs and take no part in compatibility ranking.
 */
const FILE_TYPE = /^File/i;

export function isDataParameter(parameter: TypedParameter): boolean {
  return FILE_TYPE.test(parameter.cwlType);
}

function typesFor(parameters: TypedParameter[], direction: ParameterDirection): string[] {
  return parameters.filter((p) => p.direction === direction && isDataParameter(p)).map((p) => p.cwlType);
}

export function dataInputTypes(parameters: TypedParameter[]): string[] {
  return typesFor(parameters, ParameterDirection.INPUT);
}

export function dataOutputTypes(parameters: TypedParameter[]): string[] {
  return typesFor(parameters, ParameterDirection.OUTPUT);
}

/**
 * Stage 1 (primitive) compatibility: normalised string equality, plus the one special
 * case below.
 * TODO: Replace this with a real check (format/EDAM ontology aware).
 */
export function isCompatible(outputType: string, inputType: string): boolean {
  const normalize = (t: string) => t.replace('?', '').trim().toLowerCase();
  const out = normalize(outputType);
  const inp = normalize(inputType);

  if (out === inp) return true;

  // file[] -> file: a scatter step would fan the array out over repeated invocations.
  // TODO: Counted as compatible for now; proper scatter handling is its own task.
  if (out === 'file[]' && inp === 'file') return true;

  return false;
}

/** True if any File output of the source can feed any File input of the target. */
export function areParametersCompatible(
  sourceParameters: TypedParameter[],
  targetParameters: TypedParameter[],
): boolean {
  const outputs = dataOutputTypes(sourceParameters);
  const inputs = dataInputTypes(targetParameters);
  return outputs.some((out) => inputs.some((inp) => isCompatible(out, inp)));
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
      outputTypes: dataOutputTypes(node.data.parameters),
    }))
    .filter((frame) => frame.outputTypes.length > 0);
}

/**
 * Rank one candidate against the canvas. Higher is better; the most recent frame that
 * matches wins, so `stack.length` is the top score and 1 the oldest.
 */
export function matchComponent(
  candidateParameters: TypedParameter[],
  outputStack: OutputFrame[],
): CompatibilityMatch {
  // nothing on the canvas yet -> everything ranks equally, list stays alphabetical
  if (outputStack.length === 0) return { score: 0, frame: null };

  const inputTypes = dataInputTypes(candidateParameters);
  if (inputTypes.length === 0) return { score: NO_DATA_INPUTS_SCORE, frame: null };

  for (let i = 0; i < outputStack.length; i++) {
    const frame = outputStack[i];
    const compatible = frame.outputTypes.some((out) => inputTypes.some((inp) => isCompatible(out, inp)));
    if (compatible) return { score: outputStack.length - i, frame };
  }

  return { score: 0, frame: null };
}

/** Score-only view of {@link matchComponent}. */
export function scoreComponent(candidateParameters: TypedParameter[], outputStack: OutputFrame[]): number {
  return matchComponent(candidateParameters, outputStack).score;
}
