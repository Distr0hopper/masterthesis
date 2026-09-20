import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { DomainSelect } from '@/components/component-upload/common/DomainSelect';
import type { ComponentPreviewDto, ParseWorkflowResponseDto } from '@/api/workflows';
import type { ExistingComponentDto } from '@/api/components';
import type { ComponentConfigState } from '../lib/useComponentConfigs';
import { ComponentConfigCard } from './ComponentConfigCard';
import { ParsedWorkflowOverview } from './ParsedWorkflowOverview';

interface ComponentConfigStepProps {
  parsed: ParseWorkflowResponseDto;
  previews: ComponentPreviewDto[];
  configs: Record<string, ComponentConfigState>;
  errors: Record<string, string>;
  onChange: (stepId: string, patch: Partial<ComponentConfigState>) => void;
  onApplyDomainToAll: (domain: string) => void;
  onNameConflictChange: (stepId: string, existing: ExistingComponentDto | null) => void;
}

export function ComponentConfigStep({
  parsed,
  previews,
  configs,
  errors,
  onChange,
  onApplyDomainToAll,
  onNameConflictChange,
}: ComponentConfigStepProps) {
  const [bulkDomain, setBulkDomain] = useState('');
  const creating = previews.filter((p) => configs[p.stepId]?.mode === 'create').length;

  return (
    <div className="mt-6 flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          <ParsedWorkflowOverview parsed={parsed} />
          <div>
            <p className="text-sm font-medium text-slate-900">Configure components</p>
            <p className="mt-1 text-sm text-slate-500">
              {creating} of {previews.length} step(s) will create a new component. The rest reuse components
              already in the repository.
            </p>
          </div>
          <DomainSelect
            id="bulk-domain"
            label="Set domain for all new components"
            value={bulkDomain}
            onChange={(domain) => {
              setBulkDomain(domain);
              onApplyDomainToAll(domain);
            }}
          />
        </CardContent>
      </Card>

      {previews.map((preview) => {
        const config = configs[preview.stepId];
        if (!config) return null;
        return (
          <ComponentConfigCard
            key={preview.stepId}
            preview={preview}
            config={config}
            error={errors[preview.stepId]}
            onChange={(patch) => onChange(preview.stepId, patch)}
            onNameConflictChange={(existing) => onNameConflictChange(preview.stepId, existing)}
          />
        );
      })}
    </div>
  );
}
