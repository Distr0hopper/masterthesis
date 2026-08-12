import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { getDomainLabel } from '@/api/components';

interface ComponentFiltersProps {
  searchTerm: string;
  selectedDomain: string;
  domains: string[];
  onSearchTermChange: (value: string) => void;
  onDomainChange: (value: string) => void;
}

export function ComponentFilters({
  searchTerm,
  selectedDomain,
  domains,
  onSearchTermChange,
  onDomainChange,
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
            <option key={domain} value={domain}>
              {getDomainLabel(domain)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
