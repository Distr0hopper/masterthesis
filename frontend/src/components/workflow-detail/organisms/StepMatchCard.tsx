import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { AlertTriangle, PenLine, Search } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import {
  StepMatchStatus,
  useConfirmWorkflowStep,
  useUpdateWorkflowStepComponent,
  type WorkflowStepDisplayModel,
} from '@/api/workflows';
import { canUpdate as hasUpdateLink, canConfirm as hasConfirmLink, getLink } from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { ComponentPickerDialog } from '@/components/common/ComponentPickerDialog';
import { ComponentLink } from '@/components/common/ComponentLink';
import { StatusBadge } from '@/components/common/StatusBadge';
import { DefinitionDisclosure } from '@/components/common/DefinitionDisclosure';
import { ComponentDefinition } from '@/components/component-detail/organisms/ComponentDefinition';
import { ComponentStatus, useComponent } from '@/api/components';

const STATUS_BADGE_VARIANT: Record<StepMatchStatus, 'secondary' | 'default' | 'destructive'> = {
  [StepMatchStatus.SUGGESTED]: 'secondary',
  [StepMatchStatus.CONFIRMED]: 'default',
  [StepMatchStatus.UNMATCHED]: 'destructive',
  [StepMatchStatus.INLINE]: 'secondary',
};

interface StepMatchCardProps {
  step: WorkflowStepDisplayModel;
  builderDraftId?: string | null;
}

/** A step whose component was deleted - what is wrong, and the one place it gets fixed. */
function LostComponentNotice({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
      <p className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>{children}</span>
      </p>
      {action}
    </div>
  );
}

export function StepMatchCard({ step, builderDraftId = null }: StepMatchCardProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [showDefinition, setShowDefinition] = useState(false);
  // only fetched once the definition is actually opened - a workflow can have many steps,
  // and the list would otherwise pull a full component detail for every one of them
  const { data: component } = useComponent(showDefinition && step.componentId ? step.componentId : '');
  const { mutate: updateComponent, isPending: isUpdating } = useUpdateWorkflowStepComponent();
  const { mutate: confirmStep, isPending: isConfirming } = useConfirmWorkflowStep();
  // an inline step (an embedded ExpressionTool / Workflow) never had a component to pick
  const isInline = step.matchStatus === StepMatchStatus.INLINE;
  const canUpdate = !isInline && hasUpdateLink(step._links);
  const canConfirm = !isInline && hasConfirmLink(step._links);

  const handleChange = (componentId: string | null) => {
    updateComponent(
      { link: getLink(step._links, 'update')!, componentId },
      {
        onSuccess: () => toast.success('Step updated'),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  const handleConfirm = () => {
    confirmStep(getLink(step._links, 'confirm')!, {
      onSuccess: () => toast.success('Step confirmed'),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  const isPending = isUpdating || isConfirming;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-6">
        <div className="flex items-center justify-between">
          <span className="font-mono text-sm text-slate-500">{step.stepId}</span>
          <Badge variant={STATUS_BADGE_VARIANT[step.matchStatus]}>{step.matchStatusDisplay}</Badge>
        </div>

        <h4 className="font-mono text-base font-semibold text-slate-900">{step.runReference}</h4>

        {step.matchScore !== null && (
          <p className="text-sm text-slate-500">Match confidence: {Math.round(step.matchScore * 100)}%</p>
        )}

        {isInline ? (
          <p className="text-sm text-slate-500">
            This step's definition is embedded in the workflow itself, so it needs no component.
          </p>
        ) : (
        <div className="flex flex-col gap-2">
          <Label>Matched Component</Label>
          {step.component ? (
            <div className="flex items-center justify-between gap-2 rounded-md border border-input px-3 py-2">
              <ComponentLink
                componentId={step.component.id}
                kind={step.component.kind}
                name={step.component.name}
                version={step.component.version}
              />
              {step.component.kind === 'workflow' && (
                <Badge variant="outline" title="This step runs a whole workflow">
                  Nested workflow
                </Badge>
              )}
              {step.component.status === ComponentStatus.DEPRECATED && (
                <StatusBadge
                  status={step.component.status}
                  hint={`Keeps working here, but can't be used in new workflows${
                    step.component.deprecationNote ? ` - ${step.component.deprecationNote}` : ''
                  }`}
                />
              )}
              {canUpdate && (
                <Button type="button" variant="outline" size="sm" disabled={isPending} onClick={() => setPickerOpen(true)}>
                  Change
                </Button>
              )}
            </div>
          ) : builderDraftId ? (
            <LostComponentNotice
              action={
                <Button asChild variant="outline" size="sm" className="self-start bg-white">
                  <Link to={ROUTES.builderWorkflow(builderDraftId)}>
                    <PenLine className="mr-1 h-4 w-4" /> Replace in Workflow Builder
                  </Link>
                </Button>
              }
            >
              The component of this step was deleted. Replace it on the canvas in the Workflow Builder and save - the
              workflow can&apos;t be published until then.
            </LostComponentNotice>
          ) : canUpdate ? (
            <Button type="button" variant="outline" disabled={isPending} onClick={() => setPickerOpen(true)}>
              <Search className="mr-1 h-4 w-4" /> Browse Components
            </Button>
          ) : (
            <p className="text-sm text-slate-500">No component matched.</p>
          )}
        </div>
        )}

        {canUpdate && (
          <ComponentPickerDialog open={pickerOpen} onOpenChange={setPickerOpen} value={step.componentId} onSelect={handleChange} />
        )}

        {step.componentId && (
          <DefinitionDisclosure open={showDefinition} onOpenChange={setShowDefinition}>
            {component ? (
              <ComponentDefinition model={component} />
            ) : (
              <p className="text-sm text-slate-500">Loading definition...</p>
            )}
          </DefinitionDisclosure>
        )}

        {canConfirm && (
          <Button
            size="sm"
            className="self-start"
            disabled={isPending || step.componentId === null || step.matchStatus === StepMatchStatus.CONFIRMED}
            onClick={handleConfirm}
          >
            {step.matchStatus === StepMatchStatus.CONFIRMED ? 'Confirmed' : 'Confirm'}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
