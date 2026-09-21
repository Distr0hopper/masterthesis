import { describe, expect, it } from 'vitest';
import { ParameterDirection } from '@/api/components';
import { isBlocking, validateCanvas } from './canvasValidation';
import { DEFAULT_WORKFLOW_NAME } from './canvasState';
import type { ComponentFlowNode } from '../types';

const param = (name: string, cwlType: string, direction: ParameterDirection) =>
  ({ id: `${name}-id`, name, cwlType, direction }) as never;

const node = (id: string, label: string, parameters: unknown[] = []): ComponentFlowNode =>
  ({
    id,
    type: 'componentNode',
    position: { x: 0, y: 0 },
    data: {
      componentId: `c-${id}`,
      label,
      domains: ['animal_behavior'],
      parameters,
      parameterValues: {},
    },
  }) as ComponentFlowNode;

const fileIn = (name = 'input_rds') => param(name, 'File', ParameterDirection.INPUT);
const fileOut = (name = 'output_rds') => param(name, 'File', ParameterDirection.OUTPUT);

const edge = (source: string, target: string, targetHandle = 'input_rds') => ({
  id: `${source}-${target}`,
  source,
  target,
  sourceHandle: 'output_rds',
  targetHandle,
});

const types = (errors: ReturnType<typeof validateCanvas>) => errors.map((e) => e.type);

describe('validateCanvas', () => {
  it('reports only the empty canvas when there are no nodes', () => {
    const errors = validateCanvas([], [], 'my-workflow');
    expect(types(errors)).toEqual(['no_nodes']);
  });

  it('rejects the placeholder name', () => {
    const errors = validateCanvas([node('a', 'x')], [], DEFAULT_WORKFLOW_NAME);
    expect(types(errors)).toContain('no_workflow_name');
  });

  it('rejects a blank or whitespace-only name', () => {
    expect(types(validateCanvas([node('a', 'x')], [], ''))).toContain('no_workflow_name');
    expect(types(validateCanvas([node('a', 'x')], [], '   '))).toContain('no_workflow_name');
  });

  it('accepts a single unconnected node as a valid one-step workflow', () => {
    // no edges is legitimate with one node, so it must not be reported as an island
    const errors = validateCanvas([node('a', 'only')], [], 'my-workflow');
    expect(types(errors)).not.toContain('disconnected_node');
  });

  it('flags an island in a multi-node graph, naming the component', () => {
    const nodes = [node('a', 'first', [fileOut()]), node('b', 'second', [fileIn()]), node('c', 'lonely')];
    const errors = validateCanvas(nodes, [edge('a', 'b')], 'my-workflow');
    const island = errors.find((e) => e.type === 'disconnected_node');
    expect(island?.message).toContain('"lonely"');
    expect(island?.nodeId).toBe('c');
  });

  it('flags a node with no linked component', () => {
    const orphan = node('a', 'ghost');
    orphan.data.componentId = '';
    expect(types(validateCanvas([orphan], [], 'my-workflow'))).toContain('unresolved_component');
  });

  it('warns about a File input nothing feeds', () => {
    const errors = validateCanvas([node('a', 'first', [fileIn()])], [], 'my-workflow');
    const warning = errors.find((e) => e.type === 'unconnected_input');
    expect(warning?.message).toContain('input_rds');
  });

  it('does not warn about an input that is connected', () => {
    const nodes = [node('a', 'first', [fileOut()]), node('b', 'second', [fileIn()])];
    const errors = validateCanvas(nodes, [edge('a', 'b')], 'my-workflow');
    expect(types(errors)).not.toContain('unconnected_input');
  });

  it('matches an input by its own handle, not just by node', () => {
    // two File inputs, only one wired - the other must still be reported
    const nodes = [
      node('a', 'first', [fileOut()]),
      node('b', 'second', [fileIn('input_rds'), fileIn('reference')]),
    ];
    const errors = validateCanvas(nodes, [edge('a', 'b', 'input_rds')], 'my-workflow');
    const warnings = errors.filter((e) => e.type === 'unconnected_input');
    expect(warnings).toHaveLength(1);
    expect(warnings[0].message).toContain('reference');
  });

  it('ignores config parameters when checking connections', () => {
    const configOnly = node('a', 'knobs', [param('max_speed', 'double', ParameterDirection.INPUT)]);
    expect(types(validateCanvas([configOnly], [], 'my-workflow'))).not.toContain('unconnected_input');
  });

  it('returns no errors for a well-formed two-step workflow', () => {
    const nodes = [node('a', 'first', [fileOut()]), node('b', 'second', [fileIn()])];
    expect(validateCanvas(nodes, [edge('a', 'b')], 'my-workflow')).toEqual([]);
  });
});

describe('isBlocking', () => {
  it('treats an unconnected input as advisory, everything else as blocking', () => {
    expect(isBlocking({ type: 'unconnected_input', message: '' })).toBe(false);
    expect(isBlocking({ type: 'no_nodes', message: '' })).toBe(true);
    expect(isBlocking({ type: 'disconnected_node', message: '' })).toBe(true);
    expect(isBlocking({ type: 'no_workflow_name', message: '' })).toBe(true);
    expect(isBlocking({ type: 'unresolved_component', message: '' })).toBe(true);
  });
});
