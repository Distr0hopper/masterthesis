import type { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { DomainBadges } from '@/components/common/DomainBadges';
import { FormatLabelFields } from '@/components/common/FormatLabelFields';
import { ComponentTabs } from '@/components/component-detail/organisms/ComponentTabs';
import type { ComponentDetailDisplayModel, FormatLabelDraft, PreviewParameterDto } from '@/api/components';

interface ComponentReviewStepProps {
  /** e.g. "This component will be created" or "New version v3 of remove-outliers" */
  title: ReactNode;
  /** the preview with the draft labels already applied (withFormatLabels) */
  previewModel: ComponentDetailDisplayModel;
  /** the raw preview ports - which of them accept a hand label */
  parameters: PreviewParameterDto[];
  formatLabels: FormatLabelDraft;
  onFormatLabelsChange: (value: FormatLabelDraft) => void;
}

/**
 * The last step before a component is created: what will be saved, the hand labels for
 * File ports without an ontology format, and the full component preview. Shared by the
 * manual-upload and the GitHub-packaging wizard, so both review exactly the same way.
 */
export function ComponentReviewStep({
  title,
  previewModel,
  parameters,
  formatLabels,
  onFormatLabelsChange,
}: ComponentReviewStepProps) {
  return (
    <>
      <Card className="mt-6">
        <CardContent className="flex flex-col gap-3 pt-6">
          <p className="text-sm font-medium text-slate-900">{title}</p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold text-slate-900">{previewModel.name}</span>
            <Badge variant="secondary">v{previewModel.version}</Badge>
            <DomainBadges domains={previewModel.domains} />
          </div>
          {previewModel.description && <p className="text-sm text-slate-500">{previewModel.description}</p>}
          <FormatLabelFields
            parameters={parameters}
            value={formatLabels}
            onChange={onFormatLabelsChange}
            idPrefix="upload"
          />
        </CardContent>
      </Card>
      <ComponentTabs model={previewModel} isPreview />
    </>
  );
}
