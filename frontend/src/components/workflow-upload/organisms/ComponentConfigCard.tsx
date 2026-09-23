import { useEffect, useState } from 'react';
import { AlertTriangle, FileCode, Package, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { ComponentPickerDialog } from '@/components/common/ComponentPickerDialog';
import { ComponentLink } from '@/components/common/ComponentLink';
import { DefinitionDisclosure } from '@/components/common/DefinitionDisclosure';
import { ComponentTabs } from '@/components/component-detail/organisms/ComponentTabs';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import { FormatLabelFields } from '@/components/common/FormatLabelFields';
import { ComponentOrigin, type WorkflowStepPreviewDto } from '@/api/workflows';
import {
  componentTransformer,
  withFormatLabels,
  useComponent,
  useComponentNameAvailability,
  type ExistingComponentDto,
} from '@/api/components';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import type { ComponentConfigState } from '../lib/useComponentConfigs';

interface ComponentConfigCardProps {
  preview: WorkflowStepPreviewDto;
  config: ComponentConfigState;
  error?: string;
  onChange: (patch: Partial<ComponentConfigState>) => void;
  onNameConflictChange: (existing: ExistingComponentDto | null) => void;
}

export function ComponentConfigCard({
  preview,
  config,
  error,
  onChange,
  onNameConflictChange,
}: ComponentConfigCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);

  const debouncedName = useDebouncedValue(config.mode === 'create' ? config.name : '');
  const { data: availability } = useComponentNameAvailability(debouncedName);
  // the picked component isn't in the parse response, so its details are fetched for the label
  const { data: reused } = useComponent(config.reuseComponentId ?? '');

  const taken = config.mode === 'create' && availability?.available === false ? availability.existing : null;

  useEffect(() => {
    onNameConflictChange(taken);
  }, [taken, onNameConflictChange]);

  useEffect(() => {
    if (reused) onChange({ reuseName: reused.name, reuseVersion: reused.version });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reused?.id, reused?.name, reused?.version]);

  const model = componentTransformer.toPreviewDisplayModel(
    { ...preview, parameters: withFormatLabels(preview.parameters, config.formatLabels) },
    {
      name: config.name,
      domains: config.domains,
      description: config.description,
    },
  );
  const OriginIcon = preview.origin === ComponentOrigin.INLINE ? FileCode : Package;

  return (
    <Card className={error ? 'border-error-foreground/40' : undefined}>
      <CardContent className="flex flex-col gap-4 pt-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <OriginIcon className="h-4 w-4 text-slate-400" />
            <span className="font-mono text-sm text-slate-500">{preview.stepId}</span>
            <Badge variant="secondary">
              {preview.origin === ComponentOrigin.INLINE ? 'inline tool' : preview.runReference}
            </Badge>
          </div>
          <div className="flex gap-1 rounded-md border border-input p-0.5">
            <Button
              type="button"
              size="sm"
              variant={config.mode === 'create' ? 'default' : 'ghost'}
              onClick={() => onChange({ mode: 'create' })}
            >
              Create new
            </Button>
            <Button
              type="button"
              size="sm"
              variant={config.mode === 'reuse' ? 'default' : 'ghost'}
              onClick={() => onChange({ mode: 'reuse' })}
            >
              Reuse existing
            </Button>
          </div>
        </div>

        {config.mode === 'create' ? (
          <>
            <div className="flex flex-col gap-2">
              <Label htmlFor={`component-name-${preview.stepId}`}>Name</Label>
              <Input
                id={`component-name-${preview.stepId}`}
                value={config.name}
                onChange={(e) => onChange({ name: e.target.value })}
              />
            </div>

            {taken && (
              <div className="flex flex-wrap items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span className="flex flex-wrap items-center gap-1">
                  This name is already taken by
                  <ComponentLink componentId={taken.id} name={taken.name} version={taken.version} />
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    onChange({
                      mode: 'reuse',
                      reuseComponentId: taken.id,
                      reuseName: taken.name,
                      reuseVersion: taken.version,
                    })
                  }
                >
                  Reuse it
                </Button>
              </div>
            )}

            <DomainMultiSelect
              value={config.domains}
              onChange={(domains) => onChange({ domains })}
              showHints={false}
            />

            <div className="flex flex-col gap-2">
              <Label htmlFor={`component-description-${preview.stepId}`}>Description (optional)</Label>
              <Textarea
                id={`component-description-${preview.stepId}`}
                rows={3}
                placeholder={preview.description ?? 'Taken from the CWL doc: field when left blank'}
                value={config.description}
                onChange={(e) => onChange({ description: e.target.value })}
              />
            </div>

            <FormatLabelFields
              parameters={preview.parameters}
              value={config.formatLabels}
              onChange={(formatLabels) => onChange({ formatLabels })}
              idPrefix={preview.stepId}
            />
          </>
        ) : (
          <div className="flex flex-col gap-2">
            <Label>Reused component</Label>
            <div className="flex items-center justify-between gap-2 rounded-md border border-input px-3 py-2">
              {config.reuseComponentId && config.reuseName ? (
                <ComponentLink
                  componentId={config.reuseComponentId}
                  name={config.reuseName}
                  version={config.reuseVersion}
                />
              ) : (
                <span className="font-mono text-sm text-slate-500">No component selected</span>
              )}
              <Button type="button" variant="outline" size="sm" onClick={() => setPickerOpen(true)}>
                <Search className="mr-1 h-4 w-4" /> Change
              </Button>
            </div>
            <p className="text-sm text-slate-500">
              This step will link to the existing component. Nothing new is created from its CWL.
            </p>
            <ComponentPickerDialog
              open={pickerOpen}
              onOpenChange={setPickerOpen}
              value={config.reuseComponentId}
              onSelect={(componentId) => onChange({ reuseComponentId: componentId })}
            />
          </div>
        )}

        {error && <p className="text-sm text-error-foreground">{error}</p>}

        <DefinitionDisclosure open={expanded} onOpenChange={setExpanded} label="extracted definition">
          <ComponentTabs model={model} isPreview />
        </DefinitionDisclosure>
      </CardContent>
    </Card>
  );
}
