import { Link, useLocation } from 'react-router-dom';
import { ArrowUpRight, ChevronDown, ChevronLeft, Download, FileArchive, FileText, Lock, Pencil } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ComponentKind } from '@/api/components';
import type { LinkedWorkflowDto } from '@/api/workflow-drafts';
import { StatusBadge } from '@/components/common/StatusBadge';
import { saveTarget } from './lib/saveTarget';
import { DEFAULT_WORKFLOW_NAME } from './lib/canvasState';
import { cn } from '@/lib/utils';
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
  linkedWorkflow: LinkedWorkflowDto | null;
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
  linkedWorkflow,
}: WorkflowTopBarProps) {
  const savedAgo = useRelativeTime(updatedAt);
  const { pathname } = useLocation();
  const save = saveTarget(linkedWorkflow);
  const isExportingAny = isExporting || isExportingInputs;
  // the default is a placeholder, not a name - export refuses it too (canvasValidation)
  const isUnnamed = !workflowName.trim() || workflowName.trim() === DEFAULT_WORKFLOW_NAME;
  // a public version was seen, nested or cited under this name - the backend refuses a rename
  const nameLocked = linkedWorkflow?.nameLocked ?? false;
  const NameIcon = nameLocked ? Lock : Pencil;

  return (
    <div className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4">
      {/* what this is and where it stands - laid out like the detail page's header */}
      <div className="flex min-w-0 items-center gap-3">
        <Link
          to={ROUTES.builder}
          aria-label="All workflows"
          title="All workflows"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
        >
          <ChevronLeft className="h-5 w-5" />
        </Link>
        <div className="h-8 w-px shrink-0 bg-slate-200" aria-hidden />

        <div className="flex min-w-0 flex-col gap-1">
          {/* looks like a field to type into - and asks for a name until it has a real one */}
          <label className="group relative flex w-80 max-w-full items-center">
            <span className="sr-only">Workflow name</span>
            <Input
              placeholder="Name your workflow"
              value={isUnnamed ? '' : workflowName}
              onChange={(e) => onWorkflowNameChange(e.target.value)}
              readOnly={nameLocked}
              title={nameLocked ? 'A version of this workflow is public, so its name is fixed.' : undefined}
              className={cn(
                'h-8 pr-8 font-mono font-semibold shadow-none focus-visible:ring-1 focus-visible:ring-offset-0',
                isUnnamed
                  ? 'border-dashed border-slate-400 placeholder:font-sans placeholder:font-normal placeholder:text-slate-500'
                  : nameLocked
                    ? 'cursor-default border-transparent'
                    : 'border-transparent group-hover:border-slate-300',
              )}
            />
            <NameIcon className="pointer-events-none absolute right-2.5 h-3.5 w-3.5 text-slate-400" aria-hidden />
          </label>
          <div className="flex min-w-0 items-center gap-2 px-3 text-xs text-slate-500">
            {linkedWorkflow && (
              <>
                {/* one element for the version, its state and the way to its page */}
                <Link
                  to={componentDetailRoute(ComponentKind.WORKFLOW, linkedWorkflow.id)}
                  state={{ from: pathname }}
                  className="flex shrink-0 items-center gap-1.5 rounded hover:underline"
                  title="Open in My Components - publish it, set its details, see its versions. Shows what was last saved."
                >
                  v{linkedWorkflow.version}
                  <StatusBadge status={linkedWorkflow.status} />
                  <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
                <span aria-hidden>·</span>
              </>
            )}
            {isDirty ? (
              <span className="inline-flex shrink-0 items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden /> Unsaved changes
              </span>
            ) : savedAgo ? (
              <span className="shrink-0">Saved {savedAgo}</span>
            ) : (
              <span className="shrink-0">Not saved yet</span>
            )}
          </div>
        </div>
      </div>

      {/* what to do with it - the frequent step stands out, the rare ones wait in a menu */}
      <div className="flex shrink-0 items-center gap-2">
        {/* modal={false}: an export may open the validation dialog, which a modal menu would steal focus from */}
        <DropdownMenu modal={false}>
          <DropdownMenuTrigger asChild>
            {/* both exports persist first, so neither may start while a save is in flight */}
            <Button variant="outline" disabled={isExportingAny || isSaving}>
              <Download className="h-4 w-4" />
              {isExportingAny ? 'Exporting...' : 'Export'}
              <ChevronDown className="h-3.5 w-3.5" aria-hidden />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72">
            <DropdownMenuItem className="cursor-pointer items-start" onSelect={onExport}>
              <FileArchive className="mt-0.5 h-4 w-4 text-slate-500" />
              <span className="flex flex-col">
                CWL archive (.zip)
                <span className="text-xs text-slate-500">The workflow with every step document it runs</span>
              </span>
            </DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer items-start" onSelect={onExportInputs}>
              <FileText className="mt-0.5 h-4 w-4 text-slate-500" />
              <span className="flex flex-col">
                inputs.yaml
                <span className="text-xs text-slate-500">
                  A placeholder for every input file and the configuration of every step
                </span>
              </span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          onClick={onSave}
          disabled={isSaving}
          title={save.hint}
          className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
        >
          {isSaving ? 'Saving...' : save.label}
        </Button>
      </div>
    </div>
  );
}
