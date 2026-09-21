import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { DomainFilter } from '@/components/ui/domain-filter.tsx';
import type { DomainDto } from '@/api/components';

interface ComponentFiltersProps {
  searchTerm: string;
  selectedDomains: string[];
  domains: DomainDto[];
  onSearchTermChange: (value: string) => void;
  onDomainsChange: (value: string[]) => void;
  showHideMineToggle?: boolean;
  hideMine?: boolean;
  onHideMineChange?: (value: boolean) => void;
  showFavoritesToggle?: boolean;
  favoritesOnly?: boolean;
  onFavoritesOnlyChange?: (value: boolean) => void;
}

export function ComponentFilters({
  searchTerm,
  selectedDomains,
  domains,
  onSearchTermChange,
  onDomainsChange,
  showHideMineToggle,
  hideMine,
  onHideMineChange,
  showFavoritesToggle,
  favoritesOnly,
  onFavoritesOnlyChange,
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
        <Label htmlFor="domain">Domains</Label>
        <DomainFilter
          id="domain"
          value={selectedDomains}
          domains={domains}
          onValueChange={onDomainsChange}
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
