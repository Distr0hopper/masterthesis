import { WorkflowCard } from '@/components/workflow-browse/WorkflowCard';
import { MineSection } from '@/components/common/MineSection';
import { MyWorkflowCardActions } from './MyWorkflowCardActions';
import type { WorkflowDisplayModel } from '@/api/workflows';
import { ROUTES } from '@/lib/routes';

interface WorkflowSectionProps {
  title: string;
  workflows: WorkflowDisplayModel[];
  total: number;
}

export function WorkflowSection({ title, workflows, total }: WorkflowSectionProps) {
  return (
    <MineSection title={title} total={total}>
      {workflows.map((workflow) => (
        <WorkflowCard
          key={workflow.id}
          workflow={workflow}
          backTo={ROUTES.myWorkflows}
          showBuilderLink
          actions={<MyWorkflowCardActions workflow={workflow} />}
        />
      ))}
    </MineSection>
  );
}
