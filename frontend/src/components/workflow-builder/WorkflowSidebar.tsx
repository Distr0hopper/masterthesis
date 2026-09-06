import { useState } from 'react';
import { Badge } from '@/components/ui/badge.tsx';
import { Input } from '@/components/ui/input.tsx';
import { getDomainBadgeStyle, useComponents, useDomains } from '@/api/components';
import { DRAG_MIME, type ComponentDragPayload } from './types';

export function WorkflowSidebar() {
  const [search, setSearch] = useState('');
  const term = search.trim();
  // 50 matches the backend's MAX_LIMIT - the palette has no pagination UI of its own,
  // so it asks for as many matches as the API allows in one page and relies on the
  // search box to narrow things down beyond that
  const { data, isLoading } = useComponents({ search: term || undefined, limit: 50 });
  const { data: domains } = useDomains();

  const components = data?.items ?? [];

  return (
    <aside className="flex w-[280px] shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4">
        <span className="text-xs uppercase tracking-wide text-slate-500">Components</span>
        <Input
          placeholder="Search by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading components...</p>
        ) : components.length === 0 ? (
          <p className="text-sm text-slate-500">No components found.</p>
        ) : (
          components.map((component) => (
            <div
              key={component.id}
              draggable
              onDragStart={(e) => {
                const payload: ComponentDragPayload = {
                  componentId: component.id,
                  componentName: component.name,
                  domain: component.domain,
                };
                e.dataTransfer.setData(DRAG_MIME, JSON.stringify(payload));
                e.dataTransfer.effectAllowed = 'copy';
              }}
              className="flex cursor-grab flex-col gap-2 rounded-md border border-slate-200 bg-white p-3 transition-colors hover:border-jmu-blue-300 active:cursor-grabbing"
            >
              <span className="break-all font-mono text-sm font-semibold text-slate-900">
                {component.name}
              </span>
              <Badge
                variant="outline"
                className="w-fit"
                style={domains ? getDomainBadgeStyle(component.domain, domains) : undefined}
              >
                {component.domainDisplay}
              </Badge>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
