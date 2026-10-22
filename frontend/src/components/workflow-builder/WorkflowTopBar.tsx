import { Link, useLocation } from 'react-router-dom';
import { ArrowUpRight, ChevronLeft, Download, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { ComponentKind } from '@/api/components';
import { ROUTES, componentDetailRoute } from '@/lib/routes';
import { useRelativeTime } from '@/lib/useRelativeTime';

interface WorkflowTopBarProps {
  workflowName: string;
  onWorkflowNameChange: (name: string) => void;
  onSave: () => void;
  isSaving: boolean;
  onExport: () => void;
  isExporting: boolean;
  onExportInputs: () => void;
  isExportingInputs: boolean;
  updatedAt: string | null;
  isDirty: boolean;
  linkedWorkflowId: string | null;
}

export function WorkflowTopBar({
  workflowName,
  onWorkflowNameChange,
  onSave,
  isSaving,
  onExport,
  isExporting,
  onExportInputs,
  isExportingInputs,
  updatedAt,
  isDirty,
  linkedWorkflowId,
}: WorkflowTopBarProps) {
  const savedAgo = useRelativeTime(updatedAt);
  const { pathname } = useLocation();

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
        {isDirty ? (
          <span className="inline-flex shrink-0 items-center gap-1.5 text-xs text-slate-500">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden /> Unsaved changes
          </span>
        ) : (
          savedAgo && <span className="shrink-0 text-xs text-slate-400">Saved {savedAgo}</span>
        )}

        {/* the way back to where the detail page's "Edit in Workflow Builder" came from */}
        {linkedWorkflowId && (
          <Link
            to={componentDetailRoute(ComponentKind.WORKFLOW, linkedWorkflowId)}
            state={{ from: pathname }}
            className="flex shrink-0 items-center gap-1 text-sm text-jmu-blue-800 hover:underline"
            title="Its page in My Components - publish it, set its details, see its versions. Shows what was last saved."
          >
            View in My Components
            <ArrowUpRight className="h-4 w-4" aria-hidden />
          </Link>
        )}

        <div className="flex items-center gap-2">
          {/* Save also syncs the workflow into "My Components"; publishing happens there */}
          <Button variant="outline" onClick={onSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
          {/* both exports persist first, so neither may start while a save is in flight */}
          <Button
            variant="outline"
            onClick={onExportInputs}
            disabled={isExportingInputs || isSaving}
            title="Download an inputs.yaml with a placeholder for every input file and the configuration of every step"
          >
            <FileText className="h-4 w-4" />
            {isExportingInputs ? 'Exporting...' : 'Export inputs.yaml'}
          </Button>
          <Button
            onClick={onExport}
            disabled={isExporting || isSaving}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            <Download className="h-4 w-4" />
            {isExporting ? 'Exporting...' : 'Export CWL'}
          </Button>
        </div>
      </div>
    </div>
  );
}
