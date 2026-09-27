import { useState, type ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import { UploadMetadataFields } from '@/components/common/UploadMetadataFields';
import type { WorkflowStepPreviewDto, ParseWorkflowResponseDto } from '@/api/workflows';
import type { ExistingComponentDto } from '@/api/components';
import type { ComponentConfigState } from '../lib/useComponentConfigs';
import { ComponentConfigCard } from './ComponentConfigCard';
import { ParsedWorkflowOverview } from './ParsedWorkflowOverview';

interface ComponentConfigStepProps {
  parsed: ParseWorkflowResponseDto;
  /** shown under the workflow name - e.g. that it's already taken */
  workflowNameNotice?: ReactNode;
  previews: WorkflowStepPreviewDto[];
  configs: Record<string, ComponentConfigState>;
  errors: Record<string, string>;
  onChange: (stepId: string, patch: Partial<ComponentConfigState>) => void;
  onApplyDomainsToAll: (domains: string[]) => void;
  onNameConflictChange: (stepId: string, existing: ExistingComponentDto | null) => void;
}

export function ComponentConfigStep({
  parsed,
  workflowNameNotice,
  previews,
  configs,
  errors,
  onChange,
  onApplyDomainsToAll,
  onNameConflictChange,
}: ComponentConfigStepProps) {
  const [bulkDomains, setBulkDomains] = useState<string[]>([]);
  const creating = previews.filter((p) => configs[p.stepId]?.mode === 'create').length;

  return (
    <div className="mt-6 flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-6 pt-6">
          <p className="text-sm font-medium text-slate-900">Workflow</p>
          <ParsedWorkflowOverview parsed={parsed} />
          {/* the workflow's own fields - from the page's FormProvider (useUploadMetadataForm) */}
          <UploadMetadataFields
            nameLabel="Workflow Name"
            namePlaceholder="e.g. thin-and-aggregate"
            nameNotice={workflowNameNotice}
            descriptionPlaceholder="Taken from the workflow's doc: field - or write your own"
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          <div>
            <p className="text-sm font-medium text-slate-900">Configure components</p>
            <p className="mt-1 text-sm text-slate-500">
              {creating} of {previews.length} step(s) will create a new component. The rest reuse components already in
              the repository.
            </p>
          </div>
          <DomainMultiSelect
            label="Set domains for all new components"
            value={bulkDomains}
            onChange={(domains) => {
              setBulkDomains(domains);
              onApplyDomainsToAll(domains);
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
