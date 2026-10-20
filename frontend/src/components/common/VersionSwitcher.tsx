import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, History } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { VersionStatusBadges } from '@/components/common/VersionStatusBadges';
import { latestPublished, newestFirst, useComponentVersions, type ComponentKind } from '@/api/components';
import { componentDetailRoute } from '@/lib/routes';
import { cn } from '@/lib/utils';

interface VersionSwitcherProps {
  /** the version the card stands for */
  componentId: string;
  kind: ComponentKind;
  version: number;
  versionCount: number;
  /** where a version's page leads back to - the list the card is in */
  backTo?: string;
  className?: string;
}

/**
 * The version shown, and the way to the others: "v2" as plain text, then "3 versions ▾" as a
 * framed pill - the frame is what says it can be clicked, which grey text alone never did.
 * Right where the version is read, like a branch or package version picker. The list loads
 * when opened - a page of cards never asks for every lineage's versions up front.
 */
export function VersionSwitcher({ componentId, kind, version, versionCount, backTo, className }: VersionSwitcherProps) {
  const [open, setOpen] = useState(false);
  const { data: versions, isLoading } = useComponentVersions(open ? componentId : '');
  const latest = versions ? latestPublished(versions) : undefined;

  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span className="text-sm text-slate-400">v{version}</span>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2 py-0.5 text-xs font-medium text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-jmu-blue-800 data-[state=open]:bg-slate-100"
          aria-label={`Version ${version} of ${versionCount} - choose another`}
        >
          <History className="h-3.5 w-3.5 text-slate-500" aria-hidden />
          {versionCount} versions
          <ChevronDown className="h-3.5 w-3.5 text-slate-500" aria-hidden />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-72">
          <DropdownMenuLabel className="text-xs font-medium text-slate-500">Versions</DropdownMenuLabel>
          {isLoading || !versions ? (
            <p className="px-2 py-1.5 text-sm text-slate-500">Loading versions...</p>
          ) : (
            newestFirst(versions).map((v) => {
              const isThis = v.id === componentId;
              return (
                <DropdownMenuItem key={v.id} asChild>
                  <Link
                    to={componentDetailRoute(kind, v.id)}
                    state={backTo ? { from: backTo } : undefined}
                    aria-current={isThis ? 'true' : undefined}
                    className={cn('flex cursor-pointer items-center gap-2 text-slate-900', isThis && 'bg-slate-50')}
                  >
                    <span className={cn('font-mono text-sm', isThis && 'font-semibold')}>v{v.version}</span>
                    <VersionStatusBadges version={v} isLatest={v.id === latest?.id} />
                    <span className="ml-auto text-xs text-slate-500">{v.createdAtDisplay}</span>
                  </Link>
                </DropdownMenuItem>
              );
            })
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  );
}
