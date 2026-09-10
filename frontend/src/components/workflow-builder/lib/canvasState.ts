import type { Edge } from '@xyflow/react';
import { COMPONENT_EDGE_TYPE } from '../types';
import type { ComponentFlowNode } from '../types';

export const DEFAULT_WORKFLOW_NAME = 'untitled-workflow';

export interface CanvasState {
  nodes: ComponentFlowNode[];
  edges: Edge[];
}

export interface ParsedCanvasState extends CanvasState {
  /** nodes thrown away because they no longer match the expected shape */
  droppedNodeCount: number;
  /** edges thrown away because an endpoint node is gone */
  droppedEdgeCount: number;
}

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
 * Shape check for one persisted node. `canvasState` is opaque to the backend, so a stored
 * canvas may have been written by an older build whose ComponentNodeData looked different;
 * a node missing `parameters` would break type-checking and ranking in confusing ways later.
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

/**
 * Edges must name the concrete ports they join. Canvases saved before per-port handles
 * existed carry `source`/`target` only, which no longer identifies a connection: a node
 * has several File outputs, so there is no honest way to infer which one was meant.
 * Those edges are dropped rather than guessed at - a wrong guess would silently produce
 * the wrong CWL on export.
 */
function isValidEdge(value: unknown): value is Edge {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === 'string' &&
    typeof value.source === 'string' &&
    typeof value.target === 'string' &&
    typeof value.sourceHandle === 'string' &&
    typeof value.targetHandle === 'string'
  );
}

/** Fill in fields added after a canvas may have been saved. */
function normalizeNode(node: ComponentFlowNode): ComponentFlowNode {
  const raw = (node.data as Record<string, unknown>).parameterValues;
  const parameterValues: Record<string, string> = {};
  if (isRecord(raw)) {
    for (const [key, value] of Object.entries(raw)) {
      if (typeof value === 'string') parameterValues[key] = value;
    }
  }
  return { ...node, data: { ...node.data, parameterValues } };
}

/** What the editor sends to the API: the whole canvas as one JSON string. */
export function serializeCanvasState(nodes: ComponentFlowNode[], edges: Edge[]): string {
  return JSON.stringify({ nodes, edges } satisfies CanvasState);
}

/**
 * Parse a stored `canvasState` string back into a usable canvas, dropping anything
 * malformed rather than failing the whole restore. Returns null when the payload is not
 * even readable JSON. Pure - no React, no network - so it is directly unit-testable.
 */
export function parseCanvasState(raw: string): ParsedCanvasState | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(parsed)) return null;

  const rawNodes = Array.isArray(parsed.nodes) ? parsed.nodes : [];
  const rawEdges = Array.isArray(parsed.edges) ? parsed.edges : [];

  const nodes = rawNodes.filter(isValidNode).map(normalizeNode);
  const nodeIds = new Set(nodes.map((n) => n.id));
  // an edge pointing at a dropped node would render as a dangling connection, so
  // surviving edges must have both endpoints still on the canvas
  const edges = rawEdges
    .filter((edge) => isValidEdge(edge) && nodeIds.has(edge.source) && nodeIds.has(edge.target))
    // force the custom edge type: a canvas saved before it existed carries the built-in
    // 'smoothstep', which renders fine but has no delete button
    .map((edge) => ({ ...edge, type: COMPONENT_EDGE_TYPE }));

  return {
    nodes,
    edges,
    droppedNodeCount: rawNodes.length - nodes.length,
    droppedEdgeCount: rawEdges.length - edges.length,
  };
}
