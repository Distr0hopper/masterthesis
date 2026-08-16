import type { WorkflowDetailDisplayModel } from '@/api/workflows';
import { StepMatchCard } from './StepMatchCard';

interface WorkflowStepsProps {
  model: WorkflowDetailDisplayModel;
}

export function WorkflowSteps({ model }: WorkflowStepsProps) {
  return (
    <>
      <h2 className="mt-8 text-lg font-semibold text-slate-900">Steps</h2>
      <div className="mt-4 flex flex-col gap-4">
        {model.steps.map((step) => (
          <StepMatchCard key={step.id} step={step} />
        ))}
      </div>
    </>
  );
}
