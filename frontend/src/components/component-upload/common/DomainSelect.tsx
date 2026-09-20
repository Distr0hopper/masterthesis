import { Label } from '@/components/ui/label.tsx';
import { getDomainLabel, useDomains } from '@/api/components';

interface DomainSelectProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  /** override when several pickers share a page, so label/control ids stay unique */
  id?: string;
  label?: string;
}

export function DomainSelect({ value, onChange, error, id = 'domain', label = 'Domain' }: DomainSelectProps) {
  const { data: domains } = useDomains();

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm"
      >
        <option value="" disabled>
          Select domain...
        </option>
        {domains?.map((domain) => (
          <option key={domain.id} value={domain.id}>
            {getDomainLabel(domain.id)}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-error-foreground">{error}</p>}
    </div>
  );
}
