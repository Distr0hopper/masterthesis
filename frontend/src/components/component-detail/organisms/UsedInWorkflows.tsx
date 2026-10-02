import { Link } from 'react-router-dom';
import { Workflow } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { ComponentStatus, useComponentUsages } from '@/api/components';
import { ROUTES } from '@/lib/routes';

interface UsedInWorkflowsProps {
  componentId: string;
  version: number;
}

/** The workflows running this component - a tool, or a workflow nested in them. */
export function UsedInWorkflows({ componentId, version }: UsedInWorkflowsProps) {
  const { data: usages, isLoading } = useComponentUsages(componentId);

  return (
    <Card className="mt-6">
      <CardContent className="pt-6">
        <h3 className="font-semibold text-slate-900">Used in these workflows</h3>

        {isLoading ? (
          <p className="mt-2 text-sm text-slate-500">Loading workflows...</p>
        ) : !usages?.length ? (
          <p className="mt-2 text-sm text-slate-500">Not used in any workflow yet.</p>
        ) : (
          <ul className="mt-3 flex flex-col divide-y divide-slate-100">
            {usages.map((usage) => {
              const otherVersions = usage.componentVersions.filter((v) => v !== version);
              return (
                <li key={usage.id} className="flex flex-wrap items-center gap-2 py-2">
                  <Workflow className="h-4 w-4 shrink-0 text-slate-400" />
                  <Link
                    to={ROUTES.workflowDetail(usage.id)}
                    className="font-mono text-sm font-semibold text-slate-900 hover:text-jmu-blue-800 hover:underline"
                  >
                    {usage.name}
                  </Link>
                  <span className="text-xs text-slate-500">v{usage.version}</span>
                  {otherVersions.length > 0 && (
                    <Badge variant="secondary" title="The component version this workflow's steps use">
                      uses {usage.componentVersions.map((v) => `v${v}`).join(', ')}
                    </Badge>
                  )}
                  {usage.status === ComponentStatus.DRAFT && (
                    <Badge variant="outline" className="border-amber-300 text-amber-700" title="Only visible to you">
                      Draft
                    </Badge>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
