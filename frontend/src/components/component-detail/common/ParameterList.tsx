import type { ParameterDisplayModel } from '@/api/components';

interface ParameterListProps {
  title: string;
  parameters: ParameterDisplayModel[];
}

export function ParameterList({ title, parameters }: ParameterListProps) {
  return (
    <div>
      <h4 className="text-xs font-semibold tracking-wide text-slate-500">{title}</h4>
      <div className="mt-2 flex flex-col gap-1">
        {parameters.map((parameter) => (
          <div key={parameter.id} className="text-sm">
            <span className="font-mono font-semibold text-slate-900">{parameter.name}</span>{' '}
            <span className="text-slate-500">{parameter.cwlType}</span>
            {parameter.formatLabel && (
              <span className="text-slate-400"> ({parameter.formatLabel ?? parameter.format})</span>
            )}
            {parameter.defaultValue !== null && (
              <span className="text-slate-400"> = {parameter.defaultValue}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
