import { Handle, Position, useReactFlow, type NodeProps } from '@xyflow/react';
import { Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { getDomainBadgeStyle, getDomainLabel, useDomains } from '@/api/components';
import { dataInputTypes, dataOutputTypes } from './lib/typeChecking';
import type { ComponentFlowNode } from './types';

// Handles are absolutely positioned against the nearest positioned ancestor, so they must
// be direct children of the `relative` card root - nested inside the body they anchor to
// the body's padding box instead of the node's edges. The card therefore cannot use
// `overflow-hidden` (it would clip the handles, which straddle the border): the header
// rounds its own top corners instead.
// Hover feedback is a box-shadow halo, deliberately not a scale/transform: React Flow
// centres each handle on the card edge with `transform: translate(-50%, -50%)`, and
// Tailwind's transform utilities emit `!important`, which would clobber that and make the
// dot jump inward on hover.
const HANDLE_BASE =
  '!h-3.5 !w-3.5 !rounded-full !border-2 !border-white !transition-shadow hover:!shadow-[0_0_0_4px_rgba(9,61,121,0.2)]';

export function ComponentNode({ id, data, selected }: NodeProps<ComponentFlowNode>) {
  // safe to call per node - useDomains() has a 1h staleTime, so every node reads the
  // same cached entry rather than triggering a request of its own
  const { data: domains } = useDomains();
  const { deleteElements } = useReactFlow();

  const inputCount = dataInputTypes(data.parameters).length;
  const outputCount = dataOutputTypes(data.parameters).length;

  return (
    <div
      className={`relative min-w-[220px] rounded-lg border bg-white shadow-sm transition-shadow ${
        selected ? 'border-jmu-blue-800 shadow-md' : 'border-slate-200'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        // slate: an input port, distinct from the blue output
        className={`${HANDLE_BASE} !bg-slate-400`}
        title={inputCount > 0 ? `${inputCount} file input(s)` : 'No file inputs'}
      />

      <div className="flex items-center justify-between gap-2 rounded-t-lg bg-jmu-blue-800 py-2 pl-3 pr-2">
        <span className="break-all font-mono text-sm font-semibold text-white">{data.label}</span>
        <button
          type="button"
          // `nodrag` stops React Flow from starting a node drag on mousedown, which would
          // otherwise swallow the click; deleteElements also removes the node's edges
          className="nodrag shrink-0 rounded p-1 text-white/60 transition-colors hover:bg-white/20 hover:text-white"
          aria-label={`Remove ${data.label}`}
          title="Remove from canvas"
          onClick={() => deleteElements({ nodes: [{ id }] })}
        >
          <Trash2 size={14} />
        </button>
      </div>

      <div className="flex flex-col gap-2 px-3 py-3">
        <Badge
          variant="outline"
          className="w-fit"
          style={domains ? getDomainBadgeStyle(data.domain, domains) : undefined}
        >
          {getDomainLabel(data.domain)}
        </Badge>

        {/* port labels sit flush with the card edges so each reads as belonging to the
            handle on its own side */}
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span className={inputCount === 0 ? 'text-slate-300' : undefined}>data</span>
          <span className={outputCount === 0 ? 'text-slate-300' : undefined}>output</span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className={`${HANDLE_BASE} !bg-jmu-blue-800`}
        title={outputCount > 0 ? `${outputCount} file output(s)` : 'No file outputs'}
      />
    </div>
  );
}
