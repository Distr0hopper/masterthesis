import { useState } from 'react';
import { ChevronLeft, ExternalLink, Plus } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Button } from '@/components/ui/button.tsx';
import { useInfiniteComponents } from '@/api/components';
import { useLoadMoreOnScroll } from '@/lib/useLoadMoreOnScroll';
import { ManualUploadWizard } from '@/components/tool-upload/organisms/ManualUploadWizard';
import { componentDetailRoute } from '@/lib/routes';
import { cn } from '@/lib/utils';
import { DomainBadges } from '@/components/common/DomainBadges';

/**
 * Picks the component a workflow step runs - a tool, or another workflow to nest (the
 * backend rejects one that would make the workflow contain itself).
 */
interface ComponentPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** currently matched component id, for highlighting the active row */
  value: string | null;
  onSelect: (componentId: string | null) => void;
}

const PAGE_SIZE = 20;

export function ComponentPickerDialog({ open, onOpenChange, value, onSelect }: ComponentPickerDialogProps) {
  const [mode, setMode] = useState<'browse' | 'upload'>('browse');
  const [search, setSearch] = useState('');
  const term = search.trim();
  const { data, isLoading, hasNextPage, isFetchingNextPage, fetchNextPage } = useInfiniteComponents({
    search: term || undefined,
    limit: PAGE_SIZE,
  });
  const { scrollRef, sentinelRef } = useLoadMoreOnScroll({ hasNextPage, isFetchingNextPage, fetchNextPage });

  const filtered = data?.items ?? [];

  const handleSelect = (componentId: string | null) => {
    onSelect(componentId);
    onOpenChange(false);
    setSearch('');
  };

  const handleOpenChange = (next: boolean) => {
    onOpenChange(next);
    if (!next) setMode('browse');
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="flex max-h-[80vh] flex-col">
        <DialogHeader>
          <DialogTitle>{mode === 'browse' ? 'Select a Component' : 'Upload New Tool'}</DialogTitle>
        </DialogHeader>

        {mode === 'browse' ? (
          <>
            <Input placeholder="Search by name..." value={search} onChange={(e) => setSearch(e.target.value)} autoFocus />

            <div ref={scrollRef} className="flex flex-col gap-2 overflow-y-auto">
              <button
                type="button"
                onClick={() => handleSelect(null)}
                className={cn(
                  'rounded-md border border-dashed px-3 py-2 text-left text-sm text-slate-500 hover:border-slate-300',
                  value === null && 'border-jmu-blue-800 text-jmu-blue-800',
                )}
              >
                — No match —
              </button>

              {filtered.map((component) => (
                <div
                  key={component.id}
                  className={cn(
                    'flex items-start gap-2 rounded-md border px-3 py-2 hover:border-slate-300',
                    component.id === value ? 'border-jmu-blue-800' : 'border-input',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => handleSelect(component.id)}
                    className="flex flex-1 flex-col gap-1 text-left"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-slate-900">{component.name}</span>
                      <span className="text-xs text-slate-500">v{component.version}</span>
                      {component.kind === 'workflow' && (
                        <span
                          className="rounded border px-1.5 text-xs text-slate-500"
                          title="Picking it nests this whole workflow as one step"
                        >
                          Workflow
                        </span>
                      )}
                      <span className="ml-auto flex flex-wrap gap-1">
                        <DomainBadges domains={component.domains} />
                      </span>
                    </div>
                    {component.description && <p className="line-clamp-1 text-sm text-slate-500">{component.description}</p>}
                  </button>

                  <a
                    href={componentDetailRoute(component.kind, component.id)}
                    target="_blank"
                    rel="noreferrer"
                    title="View component details"
                    className="shrink-0 rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
              ))}

              {isLoading ? (
                <p className="py-4 text-center text-sm text-slate-500">Loading components...</p>
              ) : filtered.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-500">No components found.</p>
              ) : (
                <>
                  <div ref={sentinelRef} />
                  <p className="pt-1 text-center text-xs text-slate-400">
                    {isFetchingNextPage
                      ? 'Loading more...'
                      : `Showing ${filtered.length} of ${data?.total ?? filtered.length}${hasNextPage ? ' - scroll for more' : ''}`}
                  </p>
                </>
              )}
            </div>

            <Button type="button" variant="outline" onClick={() => setMode('upload')}>
              <Plus className="mr-1 h-4 w-4" /> Upload New Tool
            </Button>
          </>
        ) : (
          <div className="flex flex-col gap-4 overflow-y-auto">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-fit"
              onClick={() => setMode('browse')}
            >
              <ChevronLeft className="mr-1 h-4 w-4" /> Back to browse
            </Button>

            <ManualUploadWizard onSuccess={(created) => handleSelect(created.id)} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
