import { Label } from '@/components/ui/label.tsx';
import { getDomainLabel, useDomains } from '@/api/components';

interface DomainMultiSelectProps {
  value: string[];
  onChange: (value: string[]) => void;
  error?: string;
}

export function DomainMultiSelect({ value, onChange, error }: DomainMultiSelectProps) {
  const { data: domains } = useDomains();

  const toggle = (domainId: string) => {
    onChange(value.includes(domainId) ? value.filter((d) => d !== domainId) : [...value, domainId]);
  };

  return (
    <div className="flex flex-col gap-2">
      <Label>Domains</Label>
      <div className="flex flex-wrap gap-3 rounded-md border border-input p-3">
        {domains?.map((domain) => (
          <label key={domain.id} className="flex items-center gap-2 text-sm text-slate-700">
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
      {error && <p className="text-sm text-error-foreground">{error}</p>}
    </div>
  );
}
