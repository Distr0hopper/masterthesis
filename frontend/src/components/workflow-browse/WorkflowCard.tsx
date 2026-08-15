import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { getDomainBadgeStyle, useDomains } from '@/api/components';
import { WorkflowStatus, type WorkflowDisplayModel } from '@/api/workflows';

interface WorkflowCardProps {
  workflow: WorkflowDisplayModel;
  /** Where the detail page's "Back" link should return to - defaults to the public browse page. */
  backTo?: string;
}

export function WorkflowCard({ workflow, backTo = '/workflows' }: WorkflowCardProps) {
  const { data: domains } = useDomains();

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

        <Button asChild className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
          <Link to={`/workflows/${workflow.id}`} state={{ from: backTo }}>
            View
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
