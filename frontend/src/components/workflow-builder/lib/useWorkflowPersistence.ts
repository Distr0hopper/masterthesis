import { useCallback } from 'react';
import type { Edge } from '@xyflow/react';
import type { ComponentFlowNode } from '../types';

export const STORAGE_KEY = 'workflow-builder-state';

export interface PersistedWorkflowState {
  workflowName: string;
  nodes: ComponentFlowNode[];
  edges: Edge[];
  /** ISO timestamp of the write, rendered as a relative "Saved 5m ago" label */
  savedAt: string;
}

export interface RestoreResult {
  state: PersistedWorkflowState;
  /** nodes thrown away because they no longer match the expected shape */
  droppedNodeCount: number;
  /** edges thrown away because an endpoint node is gone */
  droppedEdgeCount: number;
}

/** "just now" / "5m ago" / "2h ago" / "3d ago" - shared by the top bar label and the restore toast. */
export function formatRelativeTime(isoString: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (!Number.isFinite(seconds) || seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86_400)}d ago`;
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
  return (
    typeof value.id === 'string' && typeof value.source === 'string' && typeof value.target === 'string'
  );
}

/**
 * Turn whatever was in storage into usable state, dropping anything malformed rather
 * than failing the whole restore. Pure - takes already-parsed JSON, touches no browser
 * API - so it is directly unit-testable.
 */
export function sanitizePersistedState(parsed: unknown): RestoreResult | null {
  if (!isRecord(parsed)) return null;

  const rawNodes = Array.isArray(parsed.nodes) ? parsed.nodes : [];
  const rawEdges = Array.isArray(parsed.edges) ? parsed.edges : [];

  const nodes = rawNodes.filter(isValidNode);
  const nodeIds = new Set(nodes.map((n) => n.id));
  // an edge pointing at a dropped node would render as a dangling connection, so
  // surviving edges must have both endpoints still on the canvas
  const edges = rawEdges.filter(
    (edge) => isValidEdge(edge) && nodeIds.has(edge.source) && nodeIds.has(edge.target),
  );

  const savedAt = typeof parsed.savedAt === 'string' ? parsed.savedAt : new Date().toISOString();

  return {
    state: {
      workflowName: typeof parsed.workflowName === 'string' ? parsed.workflowName : '',
      nodes,
      edges,
      savedAt,
    },
    droppedNodeCount: rawNodes.length - nodes.length,
    droppedEdgeCount: rawEdges.length - edges.length,
  };
}

/**
 * Single-slot, last-write-wins persistence for the builder canvas. Saving is explicit
 * (the Save button) rather than automatic, so refreshing without saving stays a valid
 * way to discard changes.
 */
export function useWorkflowPersistence() {
  const load = useCallback((): RestoreResult | null => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return sanitizePersistedState(JSON.parse(raw));
    } catch {
      // unreadable or non-JSON payload - treat it as no saved state at all
      return null;
    }
  }, []);

  const save = useCallback((state: PersistedWorkflowState): boolean => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch {
      // quota exceeded, or storage blocked entirely (private mode / disabled cookies)
      return false;
    }
  }, []);

  const clear = useCallback((): void => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // nothing to do - clearing state we cannot reach is already the desired outcome
    }
  }, []);

  return { load, save, clear };
}
