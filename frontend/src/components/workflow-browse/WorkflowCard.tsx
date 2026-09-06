import { Link } from 'react-router-dom';
import { PenLine } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { getDomainBadgeStyle, useDomains } from '@/api/components';
import { WorkflowSource, WorkflowStatus, type WorkflowDisplayModel } from '@/api/workflows';
import { canDelete } from '@/api/permissions';
import { ROUTES } from '@/lib/routes';

interface WorkflowCardProps {
  workflow: WorkflowDisplayModel;
  /** Where the detail page's "Back" link should return to - defaults to the public browse page. */
  backTo?: string;
}

export function WorkflowCard({ workflow, backTo = ROUTES.workflows }: WorkflowCardProps) {
  const { data: domains } = useDomains();

  // Only the owner can open the draft - it is owner-scoped, so the link would 403 for
  // anyone else. `canDelete` is this codebase's ownership signal (the API only emits the
  // delete link for the owner), the same way ComponentCard gates its favourite button.
  // draftId is null once the draft has been deleted, which leaves the workflow intact but
  // no longer editable in the builder.
  const canEditInBuilder =
    workflow.source === WorkflowSource.WORKFLOW_BUILDER &&
    workflow.draftId !== null &&
    canDelete(workflow._links);

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-6">
        <div className="flex flex-wrap items-center gap-2">
          {workflow.status !== WorkflowStatus.VALIDATED && (
            <Badge variant="secondary" className="w-fit">
              {workflow.statusDisplay}
            </Badge>
          )}
          {workflow.domains.map((domainId, index) => (
            <Badge
              key={domainId}
              variant="outline"
              className="w-fit"
              style={domains ? getDomainBadgeStyle(domainId, domains) : undefined}
            >
              {workflow.domainsDisplay[index]}
            </Badge>
          ))}
        </div>

        <h3 className="font-mono text-lg font-bold text-slate-900">{workflow.name}</h3>

        {workflow.description && <p className="line-clamp-2 text-sm text-slate-500">{workflow.description}</p>}

        <div className="flex items-center justify-between border-t pt-3 text-sm text-slate-500">
          <span>{workflow.stepCount} steps</span>
          <span>{workflow.createdAtDisplay}</span>
        </div>

        <div className="flex gap-2">
          <Button asChild className="flex-1 bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link to={ROUTES.workflowDetail(workflow.id)} state={{ from: backTo }}>
              View
            </Link>
          </Button>

          {canEditInBuilder && (
            <Button asChild variant="outline" title="Open the draft this was published from">
              <Link to={ROUTES.builderWorkflow(workflow.draftId!)}>
                <PenLine className="h-4 w-4" />
                Edit
              </Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
