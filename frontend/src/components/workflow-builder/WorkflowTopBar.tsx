import { useEffect, useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog.tsx';
import { Button, buttonVariants } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from './lib/useWorkflowPersistence';

interface WorkflowTopBarProps {
  workflowName: string;
  onWorkflowNameChange: (name: string) => void;
  onSave: () => void;
  /** ISO timestamp of the last successful save, or null if never saved */
  savedAt: string | null;
  onClear: () => void;
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
  onClear,
}: WorkflowTopBarProps) {
  const savedLabel = useRelativeTime(savedAt);
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4">
      <Input
        placeholder="untitled-workflow"
        value={workflowName}
        onChange={(e) => onWorkflowNameChange(e.target.value)}
        className="max-w-xs border-0 font-mono shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
      />

      <div className="flex items-center gap-3">
        {savedLabel && <span className="text-xs text-slate-400">{savedLabel}</span>}

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setConfirmOpen(true)}>
            New
          </Button>
          <Button variant="outline" onClick={onSave}>
            Save
          </Button>
          {/* wired up in AP 4 (CWL generation) */}
          <Button disabled className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            Export CWL
          </Button>
        </div>
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Start a new workflow?</AlertDialogTitle>
            <AlertDialogDescription>
              This will clear the canvas and delete the saved state. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className={cn(buttonVariants({ variant: 'destructive' }))}
              onClick={onClear}
            >
              Clear canvas
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
