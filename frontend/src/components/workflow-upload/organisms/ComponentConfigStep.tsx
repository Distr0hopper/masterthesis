import { useState, type ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import { UploadMetadataFields } from '@/components/common/UploadMetadataFields';
import type { WorkflowStepPreviewDto, ParseWorkflowResponseDto } from '@/api/workflows';
import type { ComponentConfigState, NameConflict } from '../lib/useComponentConfigs';
import { ComponentConfigCard } from './ComponentConfigCard';
import { ParsedWorkflowOverview } from './ParsedWorkflowOverview';

interface ComponentConfigStepProps {
  parsed: ParseWorkflowResponseDto;
  workflowNameNotice?: ReactNode;
  /** the previews still needing a decision - see activePreviews */
  previews: WorkflowStepPreviewDto[];
  /** steps that come along with a reused nested workflow, so need no decision */
  hiddenCount?: number;
  configs: Record<string, ComponentConfigState>;
  errors: Record<string, string>;
  onChange: (stepId: string, patch: Partial<ComponentConfigState>) => void;
  onApplyDomainsToAll: (domains: string[]) => void;
  onNameConflictChange: (stepId: string, conflict: NameConflict | null) => void;
  locked?: boolean;
}

export function ComponentConfigStep({
  parsed,
  workflowNameNotice,
  previews,
  hiddenCount = 0,
  configs,
  errors,
  onChange,
  onApplyDomainsToAll,
  onNameConflictChange,
  locked = false,
}: ComponentConfigStepProps) {
  const [bulkDomains, setBulkDomains] = useState<string[]>([]);
  const countOf = (mode: ComponentConfigState['mode']) =>
    previews.filter((p) => configs[p.stepId]?.mode === mode).length;
  const creating = countOf('create');
  const versioning = countOf('version');

  return (
    <div className="mt-6 flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-6 pt-6">
          <p className="text-sm font-medium text-slate-900">Workflow</p>
          <ParsedWorkflowOverview parsed={parsed} />
          <UploadMetadataFields
            nameLabel="Workflow Name"
            namePlaceholder="e.g. thin-and-aggregate"
            nameNotice={workflowNameNotice}
            nameReadOnly={locked}
            domainsReadOnly={locked}
            descriptionPlaceholder="Taken from the workflow's doc: field - or write your own"
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          <div>
            <p className="text-sm font-medium text-slate-900">Configure components</p>
            <p className="mt-1 text-sm text-slate-500">
              {creating} of {previews.length} step(s) will create a new component
              {versioning > 0 && `, ${versioning} will add a new version to a tool`}. The rest reuse components already
              in the repository.
              {hiddenCount > 0 && ` ${hiddenCount} more come along with the nested workflows you reuse.`}
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
        // a nested workflow's steps follow it, indented below it
        const depth = preview.stepId.split('/').length - 1;
        return (
          <div
            key={preview.stepId}
            className={depth > 0 ? 'border-l-2 border-slate-200 pl-4' : undefined}
            style={depth > 0 ? { marginLeft: (depth - 1) * 20 } : undefined}
          >
            <ComponentConfigCard
              preview={preview}
              config={config}
              error={errors[preview.stepId]}
              onChange={(patch) => onChange(preview.stepId, patch)}
              onNameConflictChange={(conflict) => onNameConflictChange(preview.stepId, conflict)}
            />
          </div>
        );
      })}
    </div>
  );
}
