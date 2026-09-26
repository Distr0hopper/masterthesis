import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { DomainFilter } from '@/components/ui/domain-filter.tsx';
import type { DomainDto } from '@/api/components';

interface ListFiltersProps {
  searchTerm: string;
  selectedDomains: string[];
  domains: DomainDto[];
  onSearchTermChange: (value: string) => void;
  onDomainsChange: (value: string[]) => void;
  showUserToggles: boolean;
  favoritesOnly: boolean;
  onFavoritesOnlyChange: (value: boolean) => void;
  hideMine: boolean;
  onHideMineChange: (value: boolean) => void;
  itemLabel: string;
}

/**
 * The filter row of the Components and Workflows pages - one component so both lists
 * filter the same way: search, domains, and (signed in) favourites only / hide my own.
 */
export function ListFilters({
  searchTerm,
  selectedDomains,
  domains,
  onSearchTermChange,
  onDomainsChange,
  showUserToggles,
  favoritesOnly,
  onFavoritesOnlyChange,
  hideMine,
  onHideMineChange,
  itemLabel,
}: ListFiltersProps) {
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
        <DomainFilter id="domain" value={selectedDomains} domains={domains} onValueChange={onDomainsChange} />
      </div>

      {showUserToggles && (
        <>
          <label htmlFor="favoritesOnly" className="flex items-center gap-2 pb-2.5 text-sm text-slate-700">
            <input
              id="favoritesOnly"
              type="checkbox"
              checked={favoritesOnly}
              onChange={(e) => onFavoritesOnlyChange(e.target.checked)}
              className="h-4 w-4 rounded border-input accent-jmu-blue-800"
            />
            Favorites only
          </label>

          <label htmlFor="hideMine" className="flex items-center gap-2 pb-2.5 text-sm text-slate-700">
            <input
              id="hideMine"
              type="checkbox"
              checked={hideMine}
              onChange={(e) => onHideMineChange(e.target.checked)}
              className="h-4 w-4 rounded border-input accent-jmu-blue-800"
            />
            Hide my {itemLabel}
          </label>
        </>
      )}
    </div>
  );
}
