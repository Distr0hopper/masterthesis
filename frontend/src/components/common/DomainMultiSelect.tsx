import { Label } from '@/components/ui/label.tsx';
import { getDomainLabel, useDomains } from '@/api/components';

interface DomainMultiSelectProps {
  value: string[];
  onChange: (value: string[]) => void;
  error?: string;
  label?: string;
  /**
   * Show the per-domain hints under the picker. On by default; turn it off where the
   * picker repeats (one per workflow step), so the same sentence isn't restated N times.
   */
  showHints?: boolean;
}

export function DomainMultiSelect({
  value,
  onChange,
  error,
  label = 'Domains',
  showHints = true,
}: DomainMultiSelectProps) {
  const { data: domains } = useDomains();

  const toggle = (domainId: string) => {
    onChange(value.includes(domainId) ? value.filter((d) => d !== domainId) : [...value, domainId]);
  };

  const described = domains?.filter((domain) => domain.description) ?? [];

  return (
    <div className="flex flex-col gap-2">
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-3 rounded-md border border-input p-3">
        {domains?.map((domain) => (
          <label
            key={domain.id}
            title={domain.description ?? undefined}
            className="flex items-center gap-2 text-sm text-slate-700"
          >
            <input
              type="checkbox"
              checked={value.includes(domain.id)}
              onChange={() => toggle(domain.id)}
              className="h-4 w-4 rounded border-input accent-jmu-blue-800"
            />
            {getDomainLabel(domain.id)}
          </label>
        ))}
      </div>
      {showHints && described.length > 0 && (
        <p className="text-xs text-slate-500">
          {described.map((domain, index) => (
            <span key={domain.id}>
              {index > 0 && ' · '}
              <span className="font-medium">{getDomainLabel(domain.id)}</span> - {domain.description}
            </span>
          ))}
        </p>
      )}
      {error && <p className="text-sm text-error-foreground">{error}</p>}
    </div>
  );
}
