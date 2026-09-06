import { Handle, Position, useReactFlow, type NodeProps } from '@xyflow/react';
import { Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { getDomainBadgeStyle, getDomainLabel, useDomains } from '@/api/components';
import type { ComponentFlowNode } from './types';

export function ComponentNode({ id, data }: NodeProps<ComponentFlowNode>) {
  const { data: domains } = useDomains();
  const { deleteElements } = useReactFlow();

  return (
    <div className="min-w-[200px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-2 bg-jmu-blue-800 py-2 pl-3 pr-2">
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

        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Handle type="target" position={Position.Left} className="!bg-slate-400" />
            <span className="text-xs text-slate-500">data</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-500">output</span>
            <Handle type="source" position={Position.Right} className="!bg-jmu-blue-800" />
          </div>
        </div>
      </div>
    </div>
  );
}
