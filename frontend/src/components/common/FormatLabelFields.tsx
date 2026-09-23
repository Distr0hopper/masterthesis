import { Info } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Input } from '@/components/ui/input.tsx';
import {
  ParameterDirection,
  formatLabelKey,
  labelablePorts,
  type FormatLabelDraft,
  type ParameterDisplayModel,
  type PreviewParameterDto,
} from '@/api/components';

/** labels suggested in the input - RDS is what almost every MoveApps component passes around */
const SUGGESTED_LABELS = ['RDS', 'CSV', 'GeoJSON', 'GeoTIFF'];
const SUGGESTIONS_ID = 'format-label-suggestions';

interface FormatLabelFieldsProps {
  parameters: (ParameterDisplayModel | PreviewParameterDto)[];
  value: FormatLabelDraft;
  onChange: (value: FormatLabelDraft) => void;
  /** keeps input ids unique when several of these render on one page (workflow upload) */
  idPrefix: string;
}

/**
 * One input per File port without an ontology format, for a hand-written label such as
 * "RDS". Renders nothing when every File port already has a real format.
 */
export function FormatLabelFields({ parameters, value, onChange, idPrefix }: FormatLabelFieldsProps) {
  const ports = labelablePorts(parameters);
  if (ports.length === 0) return null;

  return (
    <div className="flex flex-col gap-3 rounded-md border border-amber-200 bg-amber-50/60 px-3 py-3">
      <div className="flex items-start gap-2 text-sm text-amber-800">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          {ports.length === 1 ? 'This File port has' : `These ${ports.length} File ports have`} no ontology format, so
          the workflow builder cannot check what they fit - connections to them show as unverified. You can add a
          format label by hand (e.g. <strong>RDS</strong>) so the port shows which file it expects. Labels are for
          display only and are not verified.
        </span>
      </div>

      <datalist id={SUGGESTIONS_ID}>
        {SUGGESTED_LABELS.map((label) => (
          <option key={label} value={label} />
        ))}
      </datalist>

      <div className="flex flex-col gap-2">
        {ports.map((port) => {
          const key = formatLabelKey(port);
          const id = `${idPrefix}-format-label-${key}`;
          return (
            <div key={key} className="flex flex-wrap items-center gap-2">
              <label htmlFor={id} className="flex min-w-0 flex-1 items-center gap-2 text-sm">
                <Badge variant="secondary" className="shrink-0">
                  {port.direction === ParameterDirection.INPUT ? 'in' : 'out'}
                </Badge>
                <span className="truncate font-mono text-slate-900">{port.name}</span>
                <span className="shrink-0 font-mono text-xs text-slate-500">{port.cwlType}</span>
                {port.format && <span className="truncate text-xs text-slate-500">({port.format})</span>}
              </label>
              <Input
                id={id}
                className="h-8 w-40 bg-white"
                list={SUGGESTIONS_ID}
                maxLength={64}
                placeholder="e.g. RDS"
                value={value[key] ?? ''}
                onChange={(e) => onChange({ ...value, [key]: e.target.value })}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
