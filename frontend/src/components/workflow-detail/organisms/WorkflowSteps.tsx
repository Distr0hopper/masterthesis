import { ComponentStatus } from '@/api/components';
import { canAddVersion } from '@/api/permissions';
import type { WorkflowDetailDisplayModel } from '@/api/workflows';
import { editableBuilderDraftId } from '@/lib/builderDraft';
import { ROUTES } from '@/lib/routes';
import { StepMatchCard } from './StepMatchCard';

interface WorkflowStepsProps {
  model: WorkflowDetailDisplayModel;
}

export function WorkflowSteps({ model }: WorkflowStepsProps) {
  const builderDraftId = editableBuilderDraftId(model);
  // taken back after it was public: hidden again, but its steps stay as they were published
  const frozen = model.status === ComponentStatus.DRAFT && model.wasPublished;
  const newVersionRoute = canAddVersion(model._links) ? ROUTES.workflowNewVersion(model.id) : null;
  return (
    <>
      <h2 className="mt-8 text-lg font-semibold text-slate-900">Steps</h2>
      <div className="mt-4 flex flex-col gap-4">
        {model.steps.map((step) => (
          <StepMatchCard
            key={step.id}
            step={step}
            builderDraftId={builderDraftId}
            frozen={frozen}
            newVersionRoute={newVersionRoute}
          />
        ))}
      </div>
    </>
  );
}
