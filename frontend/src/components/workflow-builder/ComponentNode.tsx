import { Handle, Position, useReactFlow, type NodeProps } from '@xyflow/react';
import { ExternalLink, Trash2 } from 'lucide-react';
import type { ParameterDisplayModel } from '@/api/components';
import { Badge } from '@/components/ui/badge.tsx';
import { getDomainBadgeStyle, getDomainLabel, useDomains } from '@/api/components';
import { configParameters, dataInputs, dataOutputs } from './lib/typeChecking';
import { formatPortType } from './lib/ports';
import { ROUTES } from '@/lib/routes';
import type { ComponentFlowNode } from './types';

// Handles are absolutely positioned against their containing block's padding box, so each
// one lands on the card's edge as long as its row spans the full card width - horizontal
// padding inside the row does not push it in. The card therefore cannot use
// `overflow-hidden` (it would clip handles straddling the border); the header rounds its
// own top corners instead.
//
// Hover feedback is a box-shadow halo, deliberately not a scale/transform: React Flow
// centres each handle with `transform: translate(-50%, -50%)`, and Tailwind's transform
// utilities emit `!important`, which would clobber that and make the dot jump on hover.
const HANDLE_BASE =
  '!h-3 !w-3 !rounded-full !border-2 !border-white !transition-shadow hover:!shadow-[0_0_0_4px_rgba(9,61,121,0.2)]';

interface PortRowProps {
  parameter: ParameterDisplayModel;
  side: 'input' | 'output';
}

function PortRow({ parameter, side }: PortRowProps) {
  const isInput = side === 'input';

  return (
    // `relative` + full width: the handle anchors to this row, landing on the card edge
    // at the row's vertical centre
    <div className={`relative px-3 py-1 ${isInput ? 'text-left' : 'text-right'}`}>
      <Handle
        type={isInput ? 'target' : 'source'}
        position={isInput ? Position.Left : Position.Right}
        // handle id === parameter name: this is what makes an edge name its real ports
        id={parameter.name}
        className={`${HANDLE_BASE} ${isInput ? '!bg-slate-400' : '!bg-jmu-blue-800'}`}
        title={parameter.description ?? parameter.name}
      />
      <div className="truncate font-mono text-xs font-semibold text-slate-900">
        {parameter.name}
      </div>
      <div className="truncate text-[11px] text-slate-400">{formatPortType(parameter)}</div>
    </div>
  );
}

export function ComponentNode({ id, data, selected }: NodeProps<ComponentFlowNode>) {
  // safe to call per node - useDomains() has a 1h staleTime, so every node reads the
  // same cached entry rather than triggering a request of its own
  const { data: domains } = useDomains();
  const { deleteElements } = useReactFlow();

  const inputs = dataInputs(data.parameters);
  const outputs = dataOutputs(data.parameters);
  const configs = configParameters(data.parameters);
  const setCount = configs.filter((p) => data.parameterValues[p.name] !== undefined).length;

  return (
    <div
      className={`relative min-w-[260px] rounded-lg border bg-white shadow-sm transition-shadow ${
        selected ? 'border-jmu-blue-800 shadow-md' : 'border-slate-200'
      }`}
    >
      <div className="flex items-center justify-between gap-2 rounded-t-lg bg-jmu-blue-800 py-2 pl-3 pr-2">
        <span className="break-all font-mono text-sm font-semibold text-white">{data.label}</span>
        <div className="flex shrink-0 items-center">
          <a
            href={ROUTES.componentDetail(data.componentId)}
            target="_blank"
            rel="noreferrer"
            // `nodrag` keeps React Flow from starting a node drag on mousedown, which
            // would otherwise swallow the click; draggable={false} stops the browser's
            // own link drag; stopPropagation keeps the click from selecting the node
            draggable={false}
            className="nodrag rounded p-1 text-white/60 transition-colors hover:bg-white/20 hover:text-white"
            aria-label={`Open ${data.label} details in a new tab`}
            title="Open details in a new tab"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={14} />
          </a>
          <button
            type="button"
            className="nodrag rounded p-1 text-white/60 transition-colors hover:bg-white/20 hover:text-white"
            aria-label={`Remove ${data.label}`}
            title="Remove from canvas"
            onClick={() => deleteElements({ nodes: [{ id }] })}
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="px-3 py-2">
        <Badge
          variant="outline"
          className="w-fit"
          style={domains ? getDomainBadgeStyle(data.domain, domains) : undefined}
        >
          {getDomainLabel(data.domain)}
        </Badge>
      </div>

      {inputs.length > 0 && (
        <div className="border-t border-slate-100 py-1">
          {inputs.map((parameter) => (
            <PortRow key={parameter.id} parameter={parameter} side="input" />
          ))}
        </div>
      )}

      {outputs.length > 0 && (
        <div className="border-t border-slate-100 py-1">
          {outputs.map((parameter) => (
            <PortRow key={parameter.id} parameter={parameter} side="output" />
          ))}
        </div>
      )}

      {configs.length > 0 && (
        <div className="rounded-b-lg border-t border-slate-100 px-3 py-1.5 text-[11px] text-slate-400">
          {setCount} of {configs.length} parameter{configs.length === 1 ? '' : 's'} set
        </div>
      )}
    </div>
  );
}
