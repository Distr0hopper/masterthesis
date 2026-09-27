import type { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { FormatLabelFields } from '@/components/common/FormatLabelFields';
import { ComponentTabs } from '@/components/component-detail/organisms/ComponentTabs';
import type { ComponentDetailDisplayModel, FormatLabelDraft, PreviewParameterDto } from '@/api/components';

interface ComponentReviewStepProps {
  /** e.g. "New component" or "New version of remove-outliers" */
  title: ReactNode;
  /** the editable name/domains/description (UploadMetadataFields) */
  details: ReactNode;
  /** the preview with the current details and draft labels applied (withFormatLabels) */
  previewModel: ComponentDetailDisplayModel;
  /** the raw preview ports - which of them accept a hand label */
  parameters: PreviewParameterDto[];
  formatLabels: FormatLabelDraft;
  onFormatLabelsChange: (value: FormatLabelDraft) => void;
}

/**
 * The last step before a component is created: everything that gets saved - details and
 * hand labels for File ports without an ontology format - editable next to the live
 * component preview. Shared by the manual-upload and the GitHub-packaging wizard.
 */
export function ComponentReviewStep({
  title,
  details,
  previewModel,
  parameters,
  formatLabels,
  onFormatLabelsChange,
}: ComponentReviewStepProps) {
  return (
    <>
      <Card className="mt-6">
        <CardContent className="flex flex-col gap-6 pt-6">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium text-slate-900">{title}</p>
            <Badge variant="secondary">v{previewModel.version}</Badge>
          </div>
          {details}
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
