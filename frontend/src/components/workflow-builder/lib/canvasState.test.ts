import { describe, expect, it } from 'vitest';
import { canvasFingerprint, parseCanvasState, serializeCanvasState } from './canvasState';
import { COMPONENT_EDGE_TYPE } from '../types';
import type { ComponentFlowNode } from '../types';

const node = (id: string) => ({
  id,
  type: 'componentNode',
  position: { x: 10, y: 20 },
  data: {
    componentId: 'c1',
    label: 'remove-outliers',
    domains: ['animal_behavior'],
    parameters: [],
    parameterValues: {},
  },
});

// handle ids are parameter names - an edge is only meaningful once it names its ports
const edge = (id: string, source: string, target: string) => ({
  id,
  source,
  target,
  sourceHandle: 'output_rds',
  targetHandle: 'input_rds',
});

const canvas = (overrides: Record<string, unknown> = {}) =>
  JSON.stringify({ nodes: [node('a'), node('b')], edges: [edge('a-b', 'a', 'b')], ...overrides });

describe('serializeCanvasState', () => {
  it('round-trips through parseCanvasState', () => {
    const nodes = [node('a'), node('b')] as unknown as ComponentFlowNode[];
    const edges = [edge('a-b', 'a', 'b')];

    const parsed = parseCanvasState(serializeCanvasState(nodes, edges))!;

    expect(parsed.nodes).toHaveLength(2);
    expect(parsed.edges).toHaveLength(1);
    expect(parsed.droppedNodeCount).toBe(0);
    expect(parsed.droppedEdgeCount).toBe(0);
    // positions must survive exactly, or nodes jump when a draft is reopened
    expect(parsed.nodes.map((n) => n.position)).toEqual([
      { x: 10, y: 20 },
      { x: 10, y: 20 },
    ]);
  });
});

describe('parseCanvasState', () => {
  it('reads a node saved before nesting existed as running a tool', () => {
    const parsed = parseCanvasState(canvas());
    expect(parsed?.nodes.map((n) => n.data.kind)).toEqual(['tool', 'tool']);
  });

  it('keeps a node that runs a nested workflow', () => {
    const nested = { ...node('w'), data: { ...node('w').data, kind: 'workflow' } };
    const parsed = parseCanvasState(JSON.stringify({ nodes: [nested], edges: [] }));
    expect(parsed?.nodes[0].data.kind).toBe('workflow');
  });

  it('returns null for unreadable JSON', () => {
    expect(parseCanvasState('')).toBeNull();
    expect(parseCanvasState('{ not json')).toBeNull();
  });

  it('returns null for JSON that is not an object', () => {
    expect(parseCanvasState('null')).toBeNull();
    expect(parseCanvasState('42')).toBeNull();
    expect(parseCanvasState('"a string"')).toBeNull();
  });

  it('reads a well-formed canvas untouched', () => {
    const parsed = parseCanvasState(canvas())!;
    expect(parsed.nodes.map((n) => n.id)).toEqual(['a', 'b']);
    expect(parsed.edges.map((e) => e.id)).toEqual(['a-b']);
  });

  it('drops nodes whose data lost its parameters', () => {
    const stale = { ...node('c'), data: { componentId: 'c', label: 'x', domains: ['y'] } };
    const parsed = parseCanvasState(canvas({ nodes: [node('a'), stale] }))!;
    expect(parsed.nodes.map((n) => n.id)).toEqual(['a']);
    expect(parsed.droppedNodeCount).toBe(1);
  });

  it('drops nodes with a malformed position', () => {
    const broken = { ...node('c'), position: { x: '10', y: 20 } };
    const parsed = parseCanvasState(canvas({ nodes: [broken] }))!;
    expect(parsed.nodes).toHaveLength(0);
    expect(parsed.droppedNodeCount).toBe(1);
  });

  it('drops edges left dangling by a dropped node', () => {
    const brokenB = { ...node('b'), data: { componentId: 'b', label: 'x', domains: ['y'] } };
    const parsed = parseCanvasState(canvas({ nodes: [node('a'), brokenB] }))!;
    expect(parsed.nodes.map((n) => n.id)).toEqual(['a']);
    expect(parsed.edges).toHaveLength(0);
    expect(parsed.droppedNodeCount).toBe(1);
    expect(parsed.droppedEdgeCount).toBe(1);
  });

  it('drops edges pointing at nodes that were never in the payload', () => {
    const parsed = parseCanvasState(canvas({ nodes: [node('a')] }))!;
    expect(parsed.droppedNodeCount).toBe(0);
    expect(parsed.edges).toHaveLength(0);
    expect(parsed.droppedEdgeCount).toBe(1);
  });

  it('normalises restored edges onto the custom edge type', () => {
    // a canvas saved before ComponentEdge existed carries the built-in 'smoothstep',
    // which renders but has no delete button
    const parsed = parseCanvasState(canvas({ edges: [{ ...edge('a-b', 'a', 'b'), type: 'smoothstep' }] }))!;
    expect(parsed.edges[0].type).toBe(COMPONENT_EDGE_TYPE);
  });

  it('gives type-less restored edges the custom edge type', () => {
    const parsed = parseCanvasState(canvas())!;
    expect(parsed.edges.every((e) => e.type === COMPONENT_EDGE_TYPE)).toBe(true);
  });

  it('keeps edges whose endpoints both survive', () => {
    const parsed = parseCanvasState(
      canvas({
        nodes: [node('a'), node('b'), node('c')],
        edges: [edge('a-b', 'a', 'b'), edge('b-c', 'b', 'c')],
      }),
    )!;
    expect(parsed.edges.map((e) => e.id)).toEqual(['a-b', 'b-c']);
    expect(parsed.droppedEdgeCount).toBe(0);
  });

  it('drops legacy edges that do not name their ports', () => {
    // saved before per-port handles existed: source/target only. A node has several File
    // outputs, so which one was meant is unknowable - guessing would produce wrong CWL.
    const parsed = parseCanvasState(canvas({ edges: [{ id: 'a-b', source: 'a', target: 'b' }] }))!;
    expect(parsed.edges).toHaveLength(0);
    expect(parsed.droppedEdgeCount).toBe(1);
  });

  it('drops an edge that names only one of its two ports', () => {
    const parsed = parseCanvasState(
      canvas({ edges: [{ id: 'a-b', source: 'a', target: 'b', sourceHandle: 'output_rds' }] }),
    )!;
    expect(parsed.edges).toHaveLength(0);
    expect(parsed.droppedEdgeCount).toBe(1);
  });

  it('preserves the handle ids of a well-formed edge', () => {
    const parsed = parseCanvasState(canvas())!;
    expect(parsed.edges[0].sourceHandle).toBe('output_rds');
    expect(parsed.edges[0].targetHandle).toBe('input_rds');
  });

  it('defaults parameterValues on a node saved before they existed', () => {
    const legacy = {
      ...node('a'),
      data: { componentId: 'c1', label: 'x', domains: ['y'], parameters: [] },
    };
    const parsed = parseCanvasState(JSON.stringify({ nodes: [legacy], edges: [] }))!;
    expect(parsed.nodes).toHaveLength(1);
    expect(parsed.nodes[0].data.parameterValues).toEqual({});
  });

  it('restores a canvas whose nodes carry the multi-domain `domains` array', () => {
    // regression: the shape check still demanded the pre-rename `domain` string, so every
    // node of every canvas saved after the multi-domain change was silently dropped -
    // reopening a draft came back empty with a "could not be restored" warning
    const parsed = parseCanvasState(canvas())!;
    expect(parsed.nodes).toHaveLength(2);
    expect(parsed.droppedNodeCount).toBe(0);
    expect(parsed.nodes[0].data.domains).toEqual(['animal_behavior']);
  });

  it('migrates a node saved with a single `domain` onto `domains`', () => {
    const legacy = {
      ...node('a'),
      data: { componentId: 'c1', label: 'x', domain: 'animal_behavior', parameters: [] },
    };
    const parsed = parseCanvasState(JSON.stringify({ nodes: [legacy], edges: [] }))!;
    expect(parsed.nodes).toHaveLength(1);
    expect(parsed.nodes[0].data.domains).toEqual(['animal_behavior']);
  });

  it('defaults domains to an empty array when a node carries neither key', () => {
    // DomainBadges maps over this, so undefined must never reach the canvas
    const bare = { ...node('a'), data: { componentId: 'c1', label: 'x', parameters: [] } };
    const parsed = parseCanvasState(JSON.stringify({ nodes: [bare], edges: [] }))!;
    expect(parsed.nodes[0].data.domains).toEqual([]);
  });

  it('discards non-string entries in a stored domains array', () => {
    const messy = { ...node('a'), data: { ...node('a').data, domains: ['ok', 42, null] } };
    const parsed = parseCanvasState(JSON.stringify({ nodes: [messy], edges: [] }))!;
    expect(parsed.nodes[0].data.domains).toEqual(['ok']);
  });

  it('keeps stored parameter values and discards non-string entries', () => {
    const configured = {
      ...node('a'),
      data: { ...node('a').data, parameterValues: { max_speed: '25', bad: 42 } },
    };
    const parsed = parseCanvasState(JSON.stringify({ nodes: [configured], edges: [] }))!;
    expect(parsed.nodes[0].data.parameterValues).toEqual({ max_speed: '25' });
  });

  it('tolerates a canvas with missing nodes/edges keys', () => {
    const parsed = parseCanvasState('{}')!;
    expect(parsed.nodes).toEqual([]);
    expect(parsed.edges).toEqual([]);
    expect(parsed.droppedNodeCount).toBe(0);
  });
});

// the fixtures predate the node kind - the fingerprint doesn't care what is in data
const flowNode = (n: object) => n as unknown as ComponentFlowNode;

describe('what counts as an unsaved change', () => {
  const saved = () => canvasFingerprint('pipeline', [flowNode(node('a'))], [edge('e', 'a', 'a')]);

  it('ignores what React Flow adds on its own - selecting or measuring a node', () => {
    const touched = { ...node('a'), selected: true, dragging: false, measured: { width: 200, height: 80 } };
    const selectedEdge = { ...edge('e', 'a', 'a'), selected: true };
    expect(canvasFingerprint('pipeline', [flowNode(touched)], [selectedEdge])).toBe(saved());
  });

  it('ignores whitespace the save trims off the name', () => {
    expect(canvasFingerprint(' pipeline ', [flowNode(node('a'))], [edge('e', 'a', 'a')])).toBe(saved());
  });

  it('counts a moved node, a changed setting, a removed edge and a new name', () => {
    const moved = { ...node('a'), position: { x: 99, y: 20 } };
    const configured = { ...node('a'), data: { ...node('a').data, parameterValues: { k: '3' } } };

    expect(canvasFingerprint('pipeline', [flowNode(moved)], [edge('e', 'a', 'a')])).not.toBe(saved());
    expect(canvasFingerprint('pipeline', [flowNode(configured)], [edge('e', 'a', 'a')])).not.toBe(saved());
    expect(canvasFingerprint('pipeline', [flowNode(node('a'))], [])).not.toBe(saved());
    expect(canvasFingerprint('renamed', [flowNode(node('a'))], [edge('e', 'a', 'a')])).not.toBe(saved());
  });
});
