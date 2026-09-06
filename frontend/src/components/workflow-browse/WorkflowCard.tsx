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
  /**
   * Opt in to the "Edit in builder" action. Off by default: browsing is for viewing, and
   * editing belongs to My Workflows only - so the button stays off the public list even
   * for workflows you own.
   */
  showBuilderLink?: boolean;
}

export function WorkflowCard({
  workflow,
  backTo = ROUTES.workflows,
  showBuilderLink = false,
}: WorkflowCardProps) {
  const { data: domains } = useDomains();

  // Three separate conditions, all required:
  //  - showBuilderLink: this surface is an editing one (My Workflows), not the browse list
  //  - source/draftId:  it came from the builder, and that draft still exists (the FK is
  //                     ON DELETE SET NULL, so a deleted draft leaves the workflow intact
  //                     but no longer editable)
  //  - canDelete:       you own it. Drafts are owner-scoped, so the link would 404 for
  //                     anyone else. `canDelete` is this codebase's ownership signal - the
  //                     API only emits that link for the owner.
  const canEditInBuilder =
    showBuilderLink &&
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

        {/* stacked, not side by side: "Edit in Workflow Builder" is too long to sit
            next to View in a three-column card grid without truncating */}
        <div className="flex flex-col gap-2">
          <Button asChild className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link to={ROUTES.workflowDetail(workflow.id)} state={{ from: backTo }}>
              View
            </Link>
          </Button>

          {canEditInBuilder && (
            <Button
              asChild
              variant="outline"
              className="w-full"
              title="Open the draft this was published from"
            >
              <Link to={ROUTES.builderWorkflow(workflow.draftId!)}>
                <PenLine className="h-4 w-4" />
                Edit in Workflow Builder
              </Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
