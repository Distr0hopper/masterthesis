import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  useReactFlow,
  type Edge,
  type EdgeProps,
} from '@xyflow/react';
import { AlertTriangle, X } from 'lucide-react';
import type { ComponentEdgeData } from './types';

/** dashed amber: allowed, but the formats on either end couldn't be checked */
const UNVERIFIED_STYLE = { stroke: '#f59e0b', strokeDasharray: '6 4' };

/**
 * A smoothstep edge with a delete button at its midpoint. Without this, a connection can
 * only be removed by selecting it and pressing Delete - undiscoverable, and awkward on a
 * thin target. A connection the backend reports as unverified is drawn dashed
 * amber with a warning badge explaining why.
 */
export function ComponentEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
  data,
}: EdgeProps<Edge<ComponentEdgeData>>) {
  const { deleteElements } = useReactFlow();

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const unverifiedMessage = data?.check?.status === 'unverified' ? data.check.message : undefined;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={unverifiedMessage ? { ...style, ...UNVERIFIED_STYLE } : style}
      />

      {/* EdgeLabelRenderer hoists this out of the SVG into a DOM overlay, so it can be a
          real <button>. That overlay is pointer-events:none, hence the explicit re-enable. */}
      <EdgeLabelRenderer>
        {unverifiedMessage && (
          <span
            className="nodrag nopan pointer-events-auto absolute flex h-5 w-5 items-center justify-center rounded-full border border-amber-300 bg-amber-50 text-amber-600 shadow-sm"
            style={{ transform: `translate(-50%, -50%) translate(${labelX - 24}px, ${labelY}px)` }}
            title={`Not verified: ${unverifiedMessage}`}
            aria-label="Connection not verified"
          >
            <AlertTriangle size={12} />
          </span>
        )}
        <button
          type="button"
          className="nodrag nopan pointer-events-auto absolute flex h-5 w-5 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-400 shadow-sm transition-colors hover:border-destructive hover:bg-destructive hover:text-destructive-foreground"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          aria-label="Remove connection"
          title="Remove connection"
          onClick={(event) => {
            event.stopPropagation();
            deleteElements({ edges: [{ id }] });
          }}
        >
          <X size={12} />
        </button>
      </EdgeLabelRenderer>
    </>
  );
}
