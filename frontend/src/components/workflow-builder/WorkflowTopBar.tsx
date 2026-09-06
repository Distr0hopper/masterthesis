import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { ROUTES } from '@/lib/routes';
import { formatRelativeTime } from './lib/useWorkflowPersistence';

interface WorkflowTopBarProps {
  workflowName: string;
  onWorkflowNameChange: (name: string) => void;
  onSave: () => void;
  /** ISO timestamp of the last successful save, or null if never saved */
  savedAt: string | null;
}

/** Live "Saved 5m ago" label. Only used here, so it stays local to this file. */
function useRelativeTime(isoString: string | null): string | null {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!isoString) {
      setLabel(null);
      return;
    }

    const update = () => setLabel(`Saved ${formatRelativeTime(isoString)}`);
    update();
    const interval = setInterval(update, 60_000);
    return () => clearInterval(interval);
  }, [isoString]);

  return label;
}

export function WorkflowTopBar({
  workflowName,
  onWorkflowNameChange,
  onSave,
  savedAt,
}: WorkflowTopBarProps) {
  const savedLabel = useRelativeTime(savedAt);

  return (
    <div className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4">
      <div className="flex min-w-0 items-center gap-3">
        <Link
          to={ROUTES.builder}
          className="flex shrink-0 items-center gap-1 text-sm text-slate-500 transition-colors hover:text-slate-900"
        >
          <ChevronLeft className="h-4 w-4" />
          Workflows
        </Link>

        <Input
          placeholder="untitled-workflow"
          value={workflowName}
          onChange={(e) => onWorkflowNameChange(e.target.value)}
          className="max-w-xs border-0 font-mono shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
        />
      </div>

      <div className="flex items-center gap-3">
        {savedLabel && <span className="shrink-0 text-xs text-slate-400">{savedLabel}</span>}

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={onSave}>
            Save
          </Button>
          {/* wired up in AP 4 (CWL generation) */}
          <Button disabled className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            Export CWL
          </Button>
        </div>
      </div>
    </div>
  );
}
