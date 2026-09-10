import { ExternalLink } from 'lucide-react';
import type { ParameterDisplayModel } from '@/api/components';
import { getDomainBadgeStyle, getDomainLabel, useDomains } from '@/api/components';
import { Badge } from '@/components/ui/badge.tsx';
import { Input } from '@/components/ui/input.tsx';
import {
  configParameters,
  dataInputs,
  dataOutputs,
  isBooleanParameter,
  isNumericParameter,
} from './lib/typeChecking';
import { formatPortType } from './lib/ports';
import { ROUTES } from '@/lib/routes';
import type { ComponentFlowNode } from './types';

interface WorkflowInspectorProps {
  node: ComponentFlowNode;
  onParameterChange: (nodeId: string, parameterName: string, value: string | undefined) => void;
}

function PortSummary({ title, ports }: { title: string; ports: ParameterDisplayModel[] }) {
  if (ports.length === 0) return null;

  return (
    <div>
      <h3 className="text-xs uppercase tracking-wide text-slate-500">{title}</h3>
      <div className="mt-2 flex flex-col gap-2">
        {ports.map((port) => (
          <div key={port.id} className="rounded-md border border-slate-200 p-2">
            <div className="break-all font-mono text-xs font-semibold text-slate-900">
              {port.name}
            </div>
            <div className="text-[11px] text-slate-400">{formatPortType(port)}</div>
            {port.description && (
              <p className="mt-1 text-[11px] leading-snug text-slate-500">{port.description}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function WorkflowInspector({ node, onParameterChange }: WorkflowInspectorProps) {
  const { data: domains } = useDomains();

  const { parameters, parameterValues } = node.data;
  const configs = configParameters(parameters);

  // undefined (not "") means unset - the component's own default applies, which is why an
  // emptied field clears the key instead of storing an empty string
  const commit = (name: string, value: string) =>
    onParameterChange(node.id, name, value === '' ? undefined : value);

  return (
    <aside className="flex w-[300px] shrink-0 flex-col overflow-y-auto border-l border-slate-200 bg-white">
      <div className="flex flex-col gap-2 border-b border-slate-200 p-4">
        <span className="text-xs uppercase tracking-wide text-slate-500">Configure</span>
        <div className="flex items-start justify-between gap-2">
          <span className="break-all font-mono text-sm font-semibold text-slate-900">
            {node.data.label}
          </span>
          <a
            href={ROUTES.componentDetail(node.data.componentId)}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-jmu-blue-800"
            aria-label={`Open ${node.data.label} details in a new tab`}
            title="Open details in a new tab"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
        <Badge
          variant="outline"
          className="w-fit"
          style={domains ? getDomainBadgeStyle(node.data.domain, domains) : undefined}
        >
          {getDomainLabel(node.data.domain)}
        </Badge>
      </div>

      <div className="flex flex-col gap-6 p-4">
        <div>
          <h3 className="text-xs uppercase tracking-wide text-slate-500">Parameters</h3>

          {configs.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">This component has no parameters.</p>
          ) : (
            <div className="mt-3 flex flex-col gap-4">
              {configs.map((parameter) => {
                const inputId = `param-${node.id}-${parameter.name}`;
                const stored = parameterValues[parameter.name];

                return (
                  <div key={parameter.id} className="flex flex-col gap-1.5">
                    <label
                      htmlFor={inputId}
                      className="break-all font-mono text-xs font-semibold text-slate-900"
                    >
                      {parameter.name}
                    </label>
                    <span className="text-[11px] text-slate-400">{parameter.cwlType}</span>

                    {isBooleanParameter(parameter) ? (
                      <label className="flex items-center gap-2 text-sm text-slate-700">
                        <input
                          id={inputId}
                          type="checkbox"
                          // falls back to the component's own default while unset
                          checked={(stored ?? parameter.defaultValue ?? 'false') === 'true'}
                          onChange={(e) =>
                            onParameterChange(node.id, parameter.name, String(e.target.checked))
                          }
                          className="h-4 w-4 rounded border-input accent-jmu-blue-800"
                        />
                        {(stored ?? parameter.defaultValue ?? 'false') === 'true'
                          ? 'true'
                          : 'false'}
                      </label>
                    ) : (
                      <Input
                        id={inputId}
                        type={isNumericParameter(parameter) ? 'number' : 'text'}
                        value={stored ?? ''}
                        // the placeholder carries the default, so an empty field reads as
                        // "using the default" rather than "empty"
                        placeholder={parameter.defaultValue ?? 'not set'}
                        onChange={(e) => commit(parameter.name, e.target.value)}
                        className="h-9 font-mono text-sm"
                      />
                    )}

                    {parameter.description && (
                      <p className="text-[11px] leading-snug text-slate-500">
                        {parameter.description}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <PortSummary title="Inputs" ports={dataInputs(parameters)} />
        <PortSummary title="Outputs" ports={dataOutputs(parameters)} />
      </div>
    </aside>
  );
}
