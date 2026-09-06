import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Badge } from '@/components/ui/badge.tsx';
import { getDomainBadgeStyle, getDomainLabel, useDomains } from '@/api/components';
import type { ComponentFlowNode } from './types';

export function ComponentNode({ data }: NodeProps<ComponentFlowNode>) {
  // safe to call per node - useDomains() has a 1h staleTime, so every node reads the
  // same cached entry rather than triggering a request of its own
  const { data: domains } = useDomains();

  return (
    <div className="min-w-[200px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="bg-jmu-blue-800 px-3 py-2">
        <span className="break-all font-mono text-sm font-semibold text-white">{data.label}</span>
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
