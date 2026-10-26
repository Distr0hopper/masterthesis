import { useEffect, useState } from 'react';
import { AlertTriangle, FileCode, History, Package, Search, Workflow } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { ComponentPickerDialog } from '@/components/common/ComponentPickerDialog';
import { ComponentLink } from '@/components/common/ComponentLink';
import { DefinitionDisclosure } from '@/components/common/DefinitionDisclosure';
import { ToolTabs } from '@/components/tool-detail/organisms/ToolTabs';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import { FormatLabelFields } from '@/components/common/FormatLabelFields';
import { ComponentOrigin, type WorkflowStepPreviewDto } from '@/api/workflows';
import { toolTransformer } from '@/api/tools';
import { ComponentStatus, withFormatLabels, useComponent, useComponentNameAvailability } from '@/api/components';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import { isNestedWorkflow, type ComponentConfigState, type NameConflict } from '../lib/useComponentConfigs';

interface ComponentConfigCardProps {
  preview: WorkflowStepPreviewDto;
  config: ComponentConfigState;
  error?: string;
  onChange: (patch: Partial<ComponentConfigState>) => void;
  onNameConflictChange: (conflict: NameConflict | null) => void;
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

  // taken even when the holder isn't shown - someone else's draft keeps its name, but not its details
  const taken = config.mode === 'create' && availability?.available === false;
  const takenBy = taken ? (availability?.existing ?? null) : null;

  useEffect(() => {
    onNameConflictChange(taken ? { takenBy } : null);
  }, [taken, takenBy, onNameConflictChange]);

  useEffect(() => {
    if (reused) onChange({ reuseKind: reused.kind, reuseName: reused.name, reuseVersion: reused.version });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reused?.id, reused?.kind, reused?.name, reused?.version]);

  // uploading a new workflow version: what this step ran in the previous one
  const previous = preview.previous ?? null;
  const canVersion = !!previous?.canAddVersion;

  // a step's own CWL always previews as the tool it would become
  const model = toolTransformer.toPreviewDisplayModel(
    { ...preview, parameters: withFormatLabels(preview.parameters, config.formatLabels) },
    {
      name: config.mode === 'version' && previous ? previous.name : config.name,
      domains: config.domains,
      description: config.description,
    },
  );
  const nested = isNestedWorkflow(preview);
  const OriginIcon = nested ? Workflow : preview.origin === ComponentOrigin.INLINE ? FileCode : Package;
  const otherUses = (preview.usedBy ?? []).filter((path) => path !== preview.stepId);

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
            {nested && <span className="text-sm text-slate-500">nested workflow</span>}
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
            {canVersion && (
              <Button
                type="button"
                size="sm"
                variant={config.mode === 'version' ? 'default' : 'ghost'}
                onClick={() => onChange({ mode: 'version' })}
              >
                New version
              </Button>
            )}
          </div>
        </div>

        {otherUses.length > 0 && (
          <p className="text-sm text-slate-500">
            Also runs in{' '}
            {otherUses.map((path) => (
              <span key={path} className="mr-1 font-mono">
                {path}
              </span>
            ))}
            - one component for all of them.
          </p>
        )}

        {previous && (
          <div className="flex flex-col gap-1 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
            <p className="flex flex-wrap items-center gap-1">
              <History className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
              In the previous version this step ran
              <ComponentLink
                componentId={previous.componentId}
                kind={previous.kind}
                name={previous.name}
                version={previous.version}
              />
              <span>- {previous.cwlChanged ? 'its CWL has changed since.' : 'its CWL is unchanged.'}</span>
            </p>
            {previous.cwlChanged && !canVersion && (
              <p className="text-xs text-slate-500">
                You can&apos;t add a version to it (someone else&apos;s, or packaged from GitHub) - create a new tool
                from this CWL, or reuse the old one unchanged.
              </p>
            )}
          </div>
        )}

        {config.mode === 'version' && previous ? (
          <>
            <p className="text-sm text-slate-600">
              This step&apos;s CWL becomes the next version of{' '}
              <span className="font-mono font-semibold text-slate-900">{previous.name}</span>, keeping its name and
              domains. It starts as a draft and is published together with the workflow.
            </p>

            <div className="flex flex-col gap-2">
              <Label htmlFor={`component-description-${preview.stepId}`}>Description (optional)</Label>
              <Textarea
                id={`component-description-${preview.stepId}`}
                rows={3}
                placeholder="Taken from the CWL doc: field when left blank"
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
        ) : config.mode === 'create' ? (
          <>
            <div className="flex flex-col gap-2">
              <Label htmlFor={`component-name-${preview.stepId}`}>Name</Label>
              <Input
                id={`component-name-${preview.stepId}`}
                value={config.name}
                onChange={(e) => onChange({ name: e.target.value })}
              />
            </div>

            {taken && !takenBy && (
              <div className="flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>This name is already taken — choose a different name.</span>
              </div>
            )}
            {takenBy && (
              <div className="flex flex-wrap items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span className="flex flex-wrap items-center gap-1">
                  This name is already taken by
                  <ComponentLink
                    componentId={takenBy.id}
                    kind={takenBy.kind}
                    name={takenBy.name}
                    version={takenBy.version}
                  />
                  {takenBy.status === ComponentStatus.DEPRECATED && (
                    <span>- deprecated, so a new workflow can't reuse it. Choose another name.</span>
                  )}
                </span>
                {takenBy.status !== ComponentStatus.DEPRECATED && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      onChange({
                        mode: 'reuse',
                        reuseComponentId: takenBy.id,
                        reuseKind: takenBy.kind,
                        reuseName: takenBy.name,
                        reuseVersion: takenBy.version,
                      })
                    }
                  >
                    Reuse it
                  </Button>
                )}
              </div>
            )}

            <DomainMultiSelect value={config.domains} onChange={(domains) => onChange({ domains })} showHints={false} />

            <div className="flex flex-col gap-2">
              <Label htmlFor={`component-description-${preview.stepId}`}>Description (optional)</Label>
              <Textarea
                id={`component-description-${preview.stepId}`}
                rows={3}
                placeholder="Taken from the CWL doc: field when left blank"
                value={config.description}
                onChange={(e) => onChange({ description: e.target.value })}
              />
            </div>

            {!nested && (
              <FormatLabelFields
                parameters={preview.parameters}
                value={config.formatLabels}
                onChange={(formatLabels) => onChange({ formatLabels })}
                idPrefix={preview.stepId}
              />
            )}
          </>
        ) : (
          <div className="flex flex-col gap-2">
            <Label>Reused component</Label>
            <div className="flex items-center justify-between gap-2 rounded-md border border-input px-3 py-2">
              {config.reuseComponentId && config.reuseKind && config.reuseName ? (
                <ComponentLink
                  componentId={config.reuseComponentId}
                  kind={config.reuseKind}
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
              This step will link to the existing component. Nothing new is created from its CWL
              {nested && ' - and the steps of this nested workflow come along with it'}.
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
          <ToolTabs model={model} isPreview />
        </DefinitionDisclosure>
      </CardContent>
    </Card>
  );
}
