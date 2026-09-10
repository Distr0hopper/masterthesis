import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { DomainSelect } from '@/components/ui/domain-select.tsx';
import type { DomainDto } from '@/api/components';

interface WorkflowFiltersProps {
  searchTerm: string;
  selectedDomain: string;
  domains: DomainDto[];
  onSearchTermChange: (value: string) => void;
  onDomainChange: (value: string) => void;
}

export function WorkflowFilters({
  searchTerm,
  selectedDomain,
  domains,
  onSearchTermChange,
  onDomainChange,
}: WorkflowFiltersProps) {
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
        <DomainSelect
          id="domain"
          value={selectedDomain}
          domains={domains}
          onValueChange={onDomainChange}
        />
      </div>
    </div>
  );
}
