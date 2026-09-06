import { useCallback } from 'react';
import type { Edge } from '@xyflow/react';
import type { ComponentFlowNode } from '../types';

/** Ordered list of workflow ids - the overview's stable sort order. */
export const INDEX_KEY = 'workflow-index';
/** AP 3's single-slot key, migrated away on first visit to the overview. */
export const LEGACY_STORAGE_KEY = 'workflow-builder-state';

export const workflowKey = (id: string) => `workflow:${id}`;

export const DEFAULT_WORKFLOW_NAME = 'untitled-workflow';

export interface PersistedWorkflow {
  id: string;
  workflowName: string;
  nodes: ComponentFlowNode[];
  edges: Edge[];
  /** ISO timestamp of the write, rendered as a relative "Saved 5m ago" label */
  savedAt: string;
  /** denormalised for the overview card, so it need not walk the node list */
  nodeCount: number;
}

export interface RestoreResult {
  workflow: PersistedWorkflow;
  /** nodes thrown away because they no longer match the expected shape */
  droppedNodeCount: number;
  /** edges thrown away because an endpoint node is gone */
  droppedEdgeCount: number;
}

/** "just now" / "5m ago" / "2h ago" / "3d ago" - shared by the top bar label and the overview cards. */
export function formatRelativeTime(isoString: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (!Number.isFinite(seconds) || seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86_400)}d ago`;
}

/**
 * crypto.randomUUID() only exists in a secure context (https or localhost). The fallback
 * keeps the builder usable when the app is served over plain http on a LAN address.
 */
export function newWorkflowId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `w-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/**
 * Shape check for one persisted node. localStorage is untrusted input: it may hold a
 * payload written by an older build whose ComponentNodeData looked different, and a node
 * missing `parameters` would break type-checking and ranking in confusing ways later.
 */
function isValidNode(value: unknown): value is ComponentFlowNode {
  if (!isRecord(value)) return false;
  const { id, type, position, data } = value;

  if (typeof id !== 'string' || id.length === 0) return false;
  if (type !== 'componentNode') return false;
  if (!isRecord(position) || typeof position.x !== 'number' || typeof position.y !== 'number') return false;
  if (!isRecord(data)) return false;

  return (
    typeof data.componentId === 'string' &&
    typeof data.label === 'string' &&
    typeof data.domain === 'string' &&
    Array.isArray(data.parameters)
  );
}

function isValidEdge(value: unknown): value is Edge {
  if (!isRecord(value)) return false;
  return typeof value.id === 'string' && typeof value.source === 'string' && typeof value.target === 'string';
}

/** Shared node/edge cleanup - drops malformed nodes, then any edge left dangling by one. */
function sanitizeGraph(parsed: Record<string, unknown>) {
  const rawNodes = Array.isArray(parsed.nodes) ? parsed.nodes : [];
  const rawEdges = Array.isArray(parsed.edges) ? parsed.edges : [];

  const nodes = rawNodes.filter(isValidNode);
  const nodeIds = new Set(nodes.map((n) => n.id));
  // an edge pointing at a dropped node would render as a dangling connection, so
  // surviving edges must have both endpoints still on the canvas
  const edges = rawEdges.filter(
    (edge) => isValidEdge(edge) && nodeIds.has(edge.source) && nodeIds.has(edge.target),
  );

  return {
    nodes,
    edges,
    droppedNodeCount: rawNodes.length - nodes.length,
    droppedEdgeCount: rawEdges.length - edges.length,
  };
}

/**
 * Turn whatever was in storage into a usable workflow, dropping anything malformed rather
 * than failing the whole restore. Pure - takes already-parsed JSON, touches no browser
 * API - so it is directly unit-testable.
 *
 * `fallbackId` covers a record whose own id is missing or corrupt; callers pass the id
 * they looked the record up by.
 */
export function sanitizePersistedWorkflow(parsed: unknown, fallbackId: string): RestoreResult | null {
  if (!isRecord(parsed)) return null;

  const { nodes, edges, droppedNodeCount, droppedEdgeCount } = sanitizeGraph(parsed);

  return {
    workflow: {
      id: typeof parsed.id === 'string' && parsed.id.length > 0 ? parsed.id : fallbackId,
      workflowName: typeof parsed.workflowName === 'string' ? parsed.workflowName : DEFAULT_WORKFLOW_NAME,
      nodes,
      edges,
      savedAt: typeof parsed.savedAt === 'string' ? parsed.savedAt : new Date().toISOString(),
      // recomputed rather than trusted, so a stored count can never drift from the
      // nodes that actually survived sanitisation
      nodeCount: nodes.length,
    },
    droppedNodeCount,
    droppedEdgeCount,
  };
}

/** Lift an AP 3 single-slot payload into the multi-workflow schema. Pure. */
export function migrateLegacyState(parsed: unknown, id: string): PersistedWorkflow | null {
  const result = sanitizePersistedWorkflow(parsed, id);
  if (!result) return null;
  // the legacy record has no id of its own; force the freshly generated one
  return { ...result.workflow, id };
}

function readIndex(): string[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(INDEX_KEY) ?? '[]');
    return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === 'string') : [];
  } catch {
    return [];
  }
}

function writeIndex(index: string[]): void {
  localStorage.setItem(INDEX_KEY, JSON.stringify(index));
}

/**
 * Multi-workflow persistence for the builder, one localStorage key per workflow plus an
 * ordered index. Saving is explicit (the Save button) rather than automatic, so leaving
 * the editor without saving stays a valid way to discard changes.
 *
 * This hook is the whole storage seam: a later move to the backend replaces listAll/load/
 * save/remove with API calls and leaves the pages and routing untouched.
 */
export function useWorkflowPersistence() {
  const load = useCallback((id: string): RestoreResult | null => {
    try {
      const raw = localStorage.getItem(workflowKey(id));
      if (!raw) return null;
      return sanitizePersistedWorkflow(JSON.parse(raw), id);
    } catch {
      // unreadable or non-JSON payload - treat it as no saved workflow at all
      return null;
    }
  }, []);

  const listAll = useCallback((): PersistedWorkflow[] => {
    // index order, not Object.keys(localStorage) - that order is unspecified and would
    // make the overview reshuffle itself between reloads
    return readIndex()
      .map((id) => {
        try {
          const raw = localStorage.getItem(workflowKey(id));
          return raw ? sanitizePersistedWorkflow(JSON.parse(raw), id) : null;
        } catch {
          return null;
        }
      })
      .filter((result): result is RestoreResult => result !== null)
      .map((result) => result.workflow);
  }, []);

  const save = useCallback((workflow: PersistedWorkflow): boolean => {
    try {
      localStorage.setItem(workflowKey(workflow.id), JSON.stringify(workflow));
      const index = readIndex();
      if (!index.includes(workflow.id)) {
        index.unshift(workflow.id); // newest first
        writeIndex(index);
      }
      return true;
    } catch {
      // quota exceeded, or storage blocked entirely (private mode / disabled cookies)
      return false;
    }
  }, []);

  const remove = useCallback((id: string): void => {
    try {
      localStorage.removeItem(workflowKey(id));
      writeIndex(readIndex().filter((entry) => entry !== id));
    } catch {
      // nothing to do - failing to clear state we cannot reach is not actionable
    }
  }, []);

  /**
   * Move an AP 3 single-slot save into the new schema. Returns the migrated workflow, or
   * null when there was nothing to migrate. The legacy key is always removed, including
   * when its contents were unreadable, so this runs at most once.
   */
  const migrateLegacy = useCallback((): PersistedWorkflow | null => {
    let migrated: PersistedWorkflow | null = null;
    try {
      const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
      if (!legacy) return null;
      migrated = migrateLegacyState(JSON.parse(legacy), newWorkflowId());
      if (migrated) save(migrated);
    } catch {
      migrated = null;
    }
    try {
      localStorage.removeItem(LEGACY_STORAGE_KEY);
    } catch {
      // ignore - the migration itself already succeeded or was impossible
    }
    return migrated;
  }, [save]);

  return { listAll, load, save, remove, migrateLegacy };
}
