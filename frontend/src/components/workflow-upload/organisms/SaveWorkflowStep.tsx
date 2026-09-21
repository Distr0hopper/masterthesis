import { Badge } from '@/components/ui/badge.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { getDomainLabel } from '@/api/components';
import { ComponentLink } from '@/components/common/ComponentLink';
import type { WorkflowStepPreviewDto } from '@/api/workflows';
import type { ComponentConfigState } from '../lib/useComponentConfigs';

interface SaveWorkflowStepProps {
  name: string;
  domains: string[];
  description: string;
  previews: WorkflowStepPreviewDto[];
  configs: Record<string, ComponentConfigState>;
}

export function SaveWorkflowStep({ name, domains, description, previews, configs }: SaveWorkflowStepProps) {
  return (
    <Card className="mt-6">
      <CardContent className="flex flex-col gap-4 pt-6">
        <div>
          <p className="text-sm font-medium text-slate-900">Workflow</p>
          <p className="mt-1 font-mono text-sm text-slate-900">{name}</p>
          <div className="mt-2 flex flex-wrap gap-1">
            {domains.map((domain) => (
              <Badge key={domain} variant="secondary">
                {getDomainLabel(domain)}
              </Badge>
            ))}
          </div>
          {description && <p className="mt-2 text-sm text-slate-500">{description}</p>}
        </div>

        <div>
          <p className="text-sm font-medium text-slate-900">Components</p>
          <ul className="mt-2 divide-y rounded-md border border-input">
            {previews.map((preview) => {
              const config = configs[preview.stepId];
              if (!config) return null;
              return (
                <li
                  key={preview.stepId}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm"
                >
                  <span className="font-mono text-slate-500">{preview.stepId}</span>
                  {config.mode === 'reuse' ? (
                    <>
                      <Badge variant="secondary">reuse</Badge>
                      {config.reuseComponentId && config.reuseName ? (
                        <ComponentLink
                          componentId={config.reuseComponentId}
                          name={config.reuseName}
                          version={config.reuseVersion}
                        />
                      ) : (
                        <span className="font-mono text-slate-500">No component selected</span>
                      )}
                    </>
                  ) : (
                    <>
                      <Badge>create</Badge>
                      <span className="font-mono text-slate-900">{config.name}</span>
                      <span className="text-slate-500">{config.domains.map(getDomainLabel).join(', ')}</span>
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
