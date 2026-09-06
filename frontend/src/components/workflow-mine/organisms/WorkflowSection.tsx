import { WorkflowCard } from '@/components/workflow-browse/WorkflowCard';
import type { WorkflowDisplayModel } from '@/api/workflows';
import { ROUTES } from '@/lib/routes';

interface WorkflowSectionProps {
  title: string;
  workflows: WorkflowDisplayModel[];
  total: number;
}

export function WorkflowSection({ title, workflows, total }: WorkflowSectionProps) {
  // no `workflows.length === 0` early-return here: with server-side pagination, a page
  // can legitimately have zero items while `total > 0` (user paged past the last one) -
  // the caller decides whether to render this section/its Pagination control based on
  // `total`, not on this page's item count, so the pagination controls stay reachable
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-slate-900">
        {title} <span className="font-normal text-slate-500">({total})</span>
      </h2>
      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((workflow) => (
          <WorkflowCard
            key={workflow.id}
            workflow={workflow}
            backTo={ROUTES.myWorkflows}
            showBuilderLink
          />
        ))}
      </div>
    </section>
  );
}
