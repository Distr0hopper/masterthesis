import { useState } from 'react';
import { ChevronLeft, ExternalLink, Plus } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { getDomainBadgeStyle, getDomainLabel, useComponents, useDomains } from '@/api/components';
import { ManualUploadForm } from '@/components/component-upload/organisms/ManualUploadForm';
import { ROUTES } from '@/lib/routes';
import { cn } from '@/lib/utils';

interface ComponentPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** currently matched component id, for highlighting the active row */
  value: string | null;
  onSelect: (componentId: string | null) => void;
}

export function ComponentPickerDialog({ open, onOpenChange, value, onSelect }: ComponentPickerDialogProps) {
  const [mode, setMode] = useState<'browse' | 'upload'>('browse');
  const [search, setSearch] = useState('');
  const { data: components } = useComponents();
  const { data: domains } = useDomains();

  const term = search.trim().toLowerCase();
  const filtered = (components ?? []).filter((c) => c.name.toLowerCase().includes(term));

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
          <DialogTitle>{mode === 'browse' ? 'Select a Component' : 'Upload New Component'}</DialogTitle>
        </DialogHeader>

        {mode === 'browse' ? (
          <>
            <Input placeholder="Search by name..." value={search} onChange={(e) => setSearch(e.target.value)} autoFocus />

            <div className="flex flex-col gap-2 overflow-y-auto">
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
                      <Badge
                        variant="outline"
                        className="ml-auto w-fit"
                        style={domains ? getDomainBadgeStyle(component.domain, domains) : undefined}
                      >
                        {getDomainLabel(component.domain)}
                      </Badge>
                    </div>
                    {component.description && <p className="line-clamp-1 text-sm text-slate-500">{component.description}</p>}
                  </button>

                  <a
                    href={ROUTES.componentDetail(component.id)}
                    target="_blank"
                    rel="noreferrer"
                    title="View component details"
                    className="shrink-0 rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
              ))}

              {filtered.length === 0 && <p className="py-4 text-center text-sm text-slate-500">No components found.</p>}
            </div>

            <Button type="button" variant="outline" onClick={() => setMode('upload')}>
              <Plus className="mr-1 h-4 w-4" /> Upload New Component
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

            <ManualUploadForm onSuccess={(created) => handleSelect(created.id)} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
