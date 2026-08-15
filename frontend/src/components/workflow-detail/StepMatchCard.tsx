import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Label } from '@/components/ui/label.tsx';
import { useComponents } from '@/api/components';
import { StepMatchStatus, useUpdateWorkflowStepComponent, type WorkflowStepDisplayModel } from '@/api/workflows';
import { getErrorMessage } from '@/lib/errors';

const STATUS_BADGE_VARIANT: Record<StepMatchStatus, 'secondary' | 'default' | 'destructive'> = {
  [StepMatchStatus.SUGGESTED]: 'secondary',
  [StepMatchStatus.CONFIRMED]: 'default',
  [StepMatchStatus.UNMATCHED]: 'destructive',
};

interface StepMatchCardProps {
  step: WorkflowStepDisplayModel;
  workflowId: string;
}

export function StepMatchCard({ step, workflowId }: StepMatchCardProps) {
  const { data: components } = useComponents();
  const { mutate, isPending } = useUpdateWorkflowStepComponent();

  const handleChange = (componentId: string | null) => {
    mutate(
      { stepId: step.id, componentId, workflowId },
      {
        onSuccess: () => toast.success('Step updated'),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

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

        <div className="flex flex-col gap-2">
          <Label htmlFor={`step-component-${step.id}`}>Matched Component</Label>
          <select
            id={`step-component-${step.id}`}
            value={step.componentId ?? ''}
            disabled={isPending}
            onChange={(e) => handleChange(e.target.value || null)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm"
          >
            <option value="">— No match —</option>
            {components?.map((component) => (
              <option key={component.id} value={component.id}>
                {component.name} (v{component.version})
              </option>
            ))}
          </select>
        </div>
      </CardContent>
    </Card>
  );
}
