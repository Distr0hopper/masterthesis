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
  showFavoritesToggle?: boolean;
  favoritesOnly?: boolean;
  onFavoritesOnlyChange?: (value: boolean) => void;
}

export function WorkflowFilters({
  searchTerm,
  selectedDomain,
  domains,
  onSearchTermChange,
  onDomainChange,
  showFavoritesToggle,
  favoritesOnly,
  onFavoritesOnlyChange,
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

      {showFavoritesToggle && (
        <label htmlFor="favoritesOnly" className="flex items-center gap-2 pb-2.5 text-sm text-slate-700">
          <input
            id="favoritesOnly"
            type="checkbox"
            checked={favoritesOnly}
            onChange={(e) => onFavoritesOnlyChange?.(e.target.checked)}
            className="h-4 w-4 rounded border-input accent-jmu-blue-800"
          />
          Favorites only
        </label>
      )}
    </div>
  );
}
