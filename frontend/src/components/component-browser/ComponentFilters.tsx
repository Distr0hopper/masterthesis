import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { getDomainLabel, type DomainDto } from '@/api/components';

interface ComponentFiltersProps {
  searchTerm: string;
  selectedDomain: string;
  domains: DomainDto[];
  onSearchTermChange: (value: string) => void;
  onDomainChange: (value: string) => void;
  showHideMineToggle?: boolean;
  hideMine?: boolean;
  onHideMineChange?: (value: boolean) => void;
}

export function ComponentFilters({
  searchTerm,
  selectedDomain,
  domains,
  onSearchTermChange,
  onDomainChange,
  showHideMineToggle,
  hideMine,
  onHideMineChange,
}: ComponentFiltersProps) {
  return (
    <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-end">
      <div className="flex flex-1 flex-col gap-2">
        <Label htmlFor="search">Search</Label>
        <Input
          id="search"
          placeholder="Search by name..."
          value={searchTerm}
          onChange={(e) => onSearchTermChange(e.target.value)}
        />
      </div>

      <div className="flex flex-col gap-2 sm:w-56">
        <Label htmlFor="domain">Domain</Label>
        <select
          id="domain"
          value={selectedDomain}
          onChange={(e) => onDomainChange(e.target.value)}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm"
        >
          <option value="">All Domains</option>
          {domains.map((domain) => (
            <option key={domain.id} value={domain.id}>
              {getDomainLabel(domain.id)}
            </option>
          ))}
        </select>
      </div>

      {showHideMineToggle && (
        <label htmlFor="hideMine" className="flex items-center gap-2 pb-2.5 text-sm text-slate-700">
          <input
            id="hideMine"
            type="checkbox"
            checked={hideMine}
            onChange={(e) => onHideMineChange?.(e.target.checked)}
            className="h-4 w-4 rounded border-input accent-jmu-blue-800"
          />
          Hide my components
        </label>
      )}
    </div>
  );
}
