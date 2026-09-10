import { Input } from '@/components/ui/input.tsx';
import { DomainSelect } from '@/components/ui/domain-select.tsx';
import type { DomainDto } from '@/api/components';

interface WorkflowSidebarFiltersProps {
  search: string;
  selectedDomain: string;
  favoritesOnly: boolean;
  domains: DomainDto[];
  onSearchChange: (value: string) => void;
  onDomainChange: (value: string) => void;
  onFavoritesOnlyChange: (value: boolean) => void;
  /** the favourites toggle is hidden for anonymous visitors - the endpoint 401s on it */
  showFavoritesToggle: boolean;
}

/**
 * Filter header for the {@link WorkflowSidebar} palette. Same three controls as the
 * /browse ComponentFilters, but stacked for the narrow rail and label-less - the section
 * header does the labelling here.
 */
export function WorkflowSidebarFilters({
  search,
  selectedDomain,
  favoritesOnly,
  domains,
  onSearchChange,
  onDomainChange,
  onFavoritesOnlyChange,
  showFavoritesToggle,
}: WorkflowSidebarFiltersProps) {
  return (
    <div className="flex flex-col gap-3 border-b border-slate-200 p-4">
      <span className="text-xs uppercase tracking-wide text-slate-500">Components</span>
      <Input
        placeholder="Search by name..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />

      <DomainSelect
        aria-label="Filter by domain"
        value={selectedDomain}
        domains={domains}
        onValueChange={onDomainChange}
        className="text-sm"
      />

      {showFavoritesToggle && (
        <label
          htmlFor="builderFavoritesOnly"
          className="flex items-center gap-2 text-sm text-slate-700"
        >
          <input
            id="builderFavoritesOnly"
            type="checkbox"
            checked={favoritesOnly}
            onChange={(e) => onFavoritesOnlyChange(e.target.checked)}
            className="h-4 w-4 rounded border-input accent-jmu-blue-800"
          />
          Favorites only
        </label>
      )}
    </div>
  );
}
