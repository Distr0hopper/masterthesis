import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  useReactFlow,
  type EdgeProps,
} from '@xyflow/react';
import { X } from 'lucide-react';

/**
 * A smoothstep edge with a delete button at its midpoint. Without this, a connection can
 * only be removed by selecting it and pressing Delete - undiscoverable, and awkward on a
 * thin target.
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
}: EdgeProps) {
  const { deleteElements } = useReactFlow();

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={style} />

      {/* EdgeLabelRenderer hoists this out of the SVG into a DOM overlay, so it can be a
          real <button>. That overlay is pointer-events:none, hence the explicit re-enable. */}
      <EdgeLabelRenderer>
        <button
          type="button"
          // nodrag/nopan: without them a click here starts a canvas pan instead
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
