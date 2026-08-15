import { WorkflowCard } from '@/components/workflow-browse/WorkflowCard';
import type { WorkflowDisplayModel } from '@/api/workflows';

interface WorkflowSectionProps {
  title: string;
  workflows: WorkflowDisplayModel[];
}

export function WorkflowSection({ title, workflows }: WorkflowSectionProps) {
  if (workflows.length === 0) return null;

  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-slate-900">
        {title} <span className="font-normal text-slate-500">({workflows.length})</span>
      </h2>
      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((workflow) => (
          <WorkflowCard key={workflow.id} workflow={workflow} backTo="/my-workflows" />
        ))}
      </div>
    </section>
  );
}
