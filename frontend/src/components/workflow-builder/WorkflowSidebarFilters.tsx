import { Input } from '@/components/ui/input.tsx';
import { DomainFilter } from '@/components/ui/domain-filter.tsx';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { ComponentKind, DomainDto } from '@/api/components';
import { KIND_COPY, KIND_ICONS, KINDS, parseKind } from '@/lib/componentKinds';

const ALL = 'all';

interface WorkflowSidebarFiltersProps {
  /** undefined lists both kinds */
  kind: ComponentKind | undefined;
  onKindChange: (value: ComponentKind | undefined) => void;
  search: string;
  selectedDomains: string[];
  favoritesOnly: boolean;
  domains: DomainDto[];
  onSearchChange: (value: string) => void;
  onDomainsChange: (value: string[]) => void;
  onFavoritesOnlyChange: (value: boolean) => void;
  /** the favourites toggle is hidden for anonymous visitors - the endpoint 401s on it */
  showFavoritesToggle: boolean;
}

/**
 * Filter header for the {@link WorkflowSidebar} palette. Same controls as the Browse
 * page - the kind tabs and ListFilters - but stacked for the narrow rail and label-less;
 * the section header does the labelling here.
 */
export function WorkflowSidebarFilters({
  kind,
  onKindChange,
  search,
  selectedDomains,
  favoritesOnly,
  domains,
  onSearchChange,
  onDomainsChange,
  onFavoritesOnlyChange,
  showFavoritesToggle,
}: WorkflowSidebarFiltersProps) {
  return (
    <div className="flex flex-col gap-3 border-b border-slate-200 p-4">
      <span className="text-xs uppercase tracking-wide text-slate-500">Components</span>
      {/* a filter, not tabbed content - as on the Browse page */}
      <Tabs value={kind ?? ALL} onValueChange={(value) => onKindChange(parseKind(value))}>
        <TabsList className="w-full">
          <TabsTrigger value={ALL} className="flex-1">
            All
          </TabsTrigger>
          {KINDS.map((k) => {
            const Icon = KIND_ICONS[k];
            return (
              <TabsTrigger key={k} value={k} className="flex-1 gap-1.5">
                <Icon className="h-4 w-4" />
                {KIND_COPY[k].plural}
              </TabsTrigger>
            );
          })}
        </TabsList>
      </Tabs>
      <Input
        placeholder="Search by name..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />

      <DomainFilter
        aria-label="Filter by domain"
        value={selectedDomains}
        domains={domains}
        onValueChange={onDomainsChange}
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
