import { afterEach, describe, expect, it, vi } from 'vitest';
import { formatRelativeTime, sanitizePersistedState } from './useWorkflowPersistence';

const node = (id: string) => ({
  id,
  type: 'componentNode',
  position: { x: 10, y: 20 },
  data: { componentId: 'c1', label: 'remove-outliers', domain: 'animal_behavior', parameters: [] },
});

const edge = (id: string, source: string, target: string) => ({ id, source, target });

const valid = {
  workflowName: 'my-workflow',
  nodes: [node('a'), node('b')],
  edges: [edge('a-b', 'a', 'b')],
  savedAt: '2026-09-06T10:00:00.000Z',
};

describe('formatRelativeTime', () => {
  afterEach(() => vi.useRealTimers());

  const at = (iso: string, now: string) => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(now));
    return formatRelativeTime(iso);
  };

  it('reports sub-minute ages as "just now"', () => {
    expect(at('2026-09-06T10:00:00Z', '2026-09-06T10:00:30Z')).toBe('just now');
  });

  it('reports minutes, hours and days', () => {
    expect(at('2026-09-06T10:00:00Z', '2026-09-06T10:05:00Z')).toBe('5m ago');
    expect(at('2026-09-06T10:00:00Z', '2026-09-06T12:00:00Z')).toBe('2h ago');
    expect(at('2026-09-03T10:00:00Z', '2026-09-06T10:00:00Z')).toBe('3d ago');
  });

  it('does not produce absurd hour counts for old saves', () => {
    expect(at('2026-08-06T10:00:00Z', '2026-09-06T10:00:00Z')).toBe('31d ago');
  });

  it('falls back to "just now" for an unparseable timestamp', () => {
    expect(formatRelativeTime('not-a-date')).toBe('just now');
  });
});

describe('sanitizePersistedState', () => {
  it('returns null for anything that is not an object', () => {
    expect(sanitizePersistedState(null)).toBeNull();
    expect(sanitizePersistedState('nope')).toBeNull();
    expect(sanitizePersistedState(42)).toBeNull();
  });

  it('round-trips a well-formed payload untouched', () => {
    const result = sanitizePersistedState(valid)!;
    expect(result.state.workflowName).toBe('my-workflow');
    expect(result.state.nodes).toHaveLength(2);
    expect(result.state.edges).toHaveLength(1);
    expect(result.state.savedAt).toBe(valid.savedAt);
    expect(result.droppedNodeCount).toBe(0);
    expect(result.droppedEdgeCount).toBe(0);
  });

  it('drops nodes whose data lost its parameters', () => {
    const stale = { ...node('c'), data: { componentId: 'c', label: 'x', domain: 'y' } };
    const result = sanitizePersistedState({ ...valid, nodes: [node('a'), stale] })!;
    expect(result.state.nodes.map((n) => n.id)).toEqual(['a']);
    expect(result.droppedNodeCount).toBe(1);
  });

  it('drops nodes with a malformed position', () => {
    const broken = { ...node('c'), position: { x: '10', y: 20 } };
    const result = sanitizePersistedState({ ...valid, nodes: [broken] })!;
    expect(result.state.nodes).toHaveLength(0);
    expect(result.droppedNodeCount).toBe(1);
  });

  it('drops edges left dangling by a dropped node', () => {
    // node 'b' is malformed, so it is discarded - and the a->b edge cannot survive it
    const brokenB = { ...node('b'), data: { componentId: 'b', label: 'x', domain: 'y' } };
    const result = sanitizePersistedState({ ...valid, nodes: [node('a'), brokenB] })!;
    expect(result.state.nodes.map((n) => n.id)).toEqual(['a']);
    expect(result.state.edges).toHaveLength(0);
    expect(result.droppedNodeCount).toBe(1);
    expect(result.droppedEdgeCount).toBe(1);
  });

  it('drops edges pointing at nodes that were never in the payload', () => {
    const result = sanitizePersistedState({ ...valid, nodes: [node('a')] })!;
    expect(result.droppedNodeCount).toBe(0);
    expect(result.state.edges).toHaveLength(0);
    expect(result.droppedEdgeCount).toBe(1);
  });

  it('keeps edges whose endpoints both survive', () => {
    const result = sanitizePersistedState({
      ...valid,
      nodes: [node('a'), node('b'), node('c')],
      edges: [edge('a-b', 'a', 'b'), edge('b-c', 'b', 'c')],
    })!;
    expect(result.state.edges.map((e) => e.id)).toEqual(['a-b', 'b-c']);
    expect(result.droppedEdgeCount).toBe(0);
  });

  it('tolerates missing nodes/edges/name fields', () => {
    const result = sanitizePersistedState({ savedAt: valid.savedAt })!;
    expect(result.state.workflowName).toBe('');
    expect(result.state.nodes).toEqual([]);
    expect(result.state.edges).toEqual([]);
  });

  it('substitutes a timestamp when savedAt is missing', () => {
    const result = sanitizePersistedState({ nodes: [], edges: [] })!;
    expect(Number.isNaN(new Date(result.state.savedAt).getTime())).toBe(false);
  });
});
