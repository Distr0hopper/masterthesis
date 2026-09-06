import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  DEFAULT_WORKFLOW_NAME,
  formatRelativeTime,
  migrateLegacyState,
  newWorkflowId,
  sanitizePersistedWorkflow,
} from './useWorkflowPersistence';

const node = (id: string) => ({
  id,
  type: 'componentNode',
  position: { x: 10, y: 20 },
  data: { componentId: 'c1', label: 'remove-outliers', domain: 'animal_behavior', parameters: [] },
});

const edge = (id: string, source: string, target: string) => ({ id, source, target });

const valid = {
  id: 'wf-1',
  workflowName: 'my-workflow',
  nodes: [node('a'), node('b')],
  edges: [edge('a-b', 'a', 'b')],
  savedAt: '2026-09-06T10:00:00.000Z',
  nodeCount: 2,
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

describe('newWorkflowId', () => {
  it('produces distinct non-empty ids', () => {
    const ids = new Set(Array.from({ length: 50 }, newWorkflowId));
    expect(ids.size).toBe(50);
    expect([...ids].every((id) => id.length > 0)).toBe(true);
  });
});

describe('sanitizePersistedWorkflow', () => {
  it('returns null for anything that is not an object', () => {
    expect(sanitizePersistedWorkflow(null, 'x')).toBeNull();
    expect(sanitizePersistedWorkflow('nope', 'x')).toBeNull();
    expect(sanitizePersistedWorkflow(42, 'x')).toBeNull();
  });

  it('round-trips a well-formed payload untouched', () => {
    const result = sanitizePersistedWorkflow(valid, 'lookup-id')!;
    expect(result.workflow.id).toBe('wf-1');
    expect(result.workflow.workflowName).toBe('my-workflow');
    expect(result.workflow.nodes).toHaveLength(2);
    expect(result.workflow.edges).toHaveLength(1);
    expect(result.workflow.savedAt).toBe(valid.savedAt);
    expect(result.droppedNodeCount).toBe(0);
    expect(result.droppedEdgeCount).toBe(0);
  });

  it('falls back to the lookup id when the record has none', () => {
    const { id: _omitted, ...withoutId } = valid;
    expect(sanitizePersistedWorkflow(withoutId, 'lookup-id')!.workflow.id).toBe('lookup-id');
    expect(sanitizePersistedWorkflow({ ...valid, id: '' }, 'lookup-id')!.workflow.id).toBe('lookup-id');
  });

  it('recomputes nodeCount so a stored count cannot drift', () => {
    // claims 99 nodes but carries two, one of which is malformed
    const stale = { ...node('c'), data: { componentId: 'c', label: 'x', domain: 'y' } };
    const result = sanitizePersistedWorkflow({ ...valid, nodes: [node('a'), stale], nodeCount: 99 }, 'x')!;
    expect(result.workflow.nodeCount).toBe(1);
  });

  it('drops nodes whose data lost its parameters', () => {
    const stale = { ...node('c'), data: { componentId: 'c', label: 'x', domain: 'y' } };
    const result = sanitizePersistedWorkflow({ ...valid, nodes: [node('a'), stale] }, 'x')!;
    expect(result.workflow.nodes.map((n) => n.id)).toEqual(['a']);
    expect(result.droppedNodeCount).toBe(1);
  });

  it('drops nodes with a malformed position', () => {
    const broken = { ...node('c'), position: { x: '10', y: 20 } };
    const result = sanitizePersistedWorkflow({ ...valid, nodes: [broken] }, 'x')!;
    expect(result.workflow.nodes).toHaveLength(0);
    expect(result.droppedNodeCount).toBe(1);
  });

  it('drops edges left dangling by a dropped node', () => {
    const brokenB = { ...node('b'), data: { componentId: 'b', label: 'x', domain: 'y' } };
    const result = sanitizePersistedWorkflow({ ...valid, nodes: [node('a'), brokenB] }, 'x')!;
    expect(result.workflow.nodes.map((n) => n.id)).toEqual(['a']);
    expect(result.workflow.edges).toHaveLength(0);
    expect(result.droppedNodeCount).toBe(1);
    expect(result.droppedEdgeCount).toBe(1);
  });

  it('drops edges pointing at nodes that were never in the payload', () => {
    const result = sanitizePersistedWorkflow({ ...valid, nodes: [node('a')] }, 'x')!;
    expect(result.droppedNodeCount).toBe(0);
    expect(result.workflow.edges).toHaveLength(0);
    expect(result.droppedEdgeCount).toBe(1);
  });

  it('keeps edges whose endpoints both survive', () => {
    const result = sanitizePersistedWorkflow(
      {
        ...valid,
        nodes: [node('a'), node('b'), node('c')],
        edges: [edge('a-b', 'a', 'b'), edge('b-c', 'b', 'c')],
      },
      'x',
    )!;
    expect(result.workflow.edges.map((e) => e.id)).toEqual(['a-b', 'b-c']);
    expect(result.droppedEdgeCount).toBe(0);
  });

  it('tolerates missing nodes/edges/name fields', () => {
    const result = sanitizePersistedWorkflow({ savedAt: valid.savedAt }, 'x')!;
    expect(result.workflow.workflowName).toBe(DEFAULT_WORKFLOW_NAME);
    expect(result.workflow.nodes).toEqual([]);
    expect(result.workflow.edges).toEqual([]);
    expect(result.workflow.nodeCount).toBe(0);
  });

  it('substitutes a timestamp when savedAt is missing', () => {
    const result = sanitizePersistedWorkflow({ nodes: [], edges: [] }, 'x')!;
    expect(Number.isNaN(new Date(result.workflow.savedAt).getTime())).toBe(false);
  });
});

describe('migrateLegacyState', () => {
  // exactly what AP 3 wrote: no id, no nodeCount
  const legacy = {
    workflowName: 'legacy-workflow',
    nodes: [node('a'), node('b')],
    edges: [edge('a-b', 'a', 'b')],
    savedAt: '2026-09-05T09:00:00.000Z',
  };

  it('lifts an AP 3 payload into the multi-workflow schema', () => {
    const migrated = migrateLegacyState(legacy, 'new-id')!;
    expect(migrated.id).toBe('new-id');
    expect(migrated.workflowName).toBe('legacy-workflow');
    expect(migrated.nodes).toHaveLength(2);
    expect(migrated.edges).toHaveLength(1);
    expect(migrated.nodeCount).toBe(2);
    expect(migrated.savedAt).toBe(legacy.savedAt);
  });

  it('forces the supplied id even when the legacy record carries one', () => {
    expect(migrateLegacyState({ ...legacy, id: 'stale-id' }, 'new-id')!.id).toBe('new-id');
  });

  it('names an unnamed legacy workflow', () => {
    expect(migrateLegacyState({ nodes: [], edges: [] }, 'new-id')!.workflowName).toBe(
      DEFAULT_WORKFLOW_NAME,
    );
  });

  it('returns null for an unusable payload', () => {
    expect(migrateLegacyState(null, 'new-id')).toBeNull();
    expect(migrateLegacyState('garbage', 'new-id')).toBeNull();
  });
});
