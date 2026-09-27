import type { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { FormatLabelFields } from '@/components/common/FormatLabelFields';
import { UploadMetadataFields } from '@/components/common/UploadMetadataFields';
import { ComponentTabs } from '@/components/component-detail/organisms/ComponentTabs';
import type { ComponentDetailDisplayModel, FormatLabelDraft, PreviewParameterDto } from '@/api/components';

interface ComponentReviewStepProps {
  /** e.g. "New component" or "New version of remove-outliers" */
  title: ReactNode;
  /** name and domains shown but not editable - a new version keeps its lineage's */
  locked?: boolean;
  /** shown under the name - e.g. that it's taken, or which component gets the new version */
  nameNotice?: ReactNode;
  descriptionPlaceholder?: string;
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
 * component preview. Shared by the manual-upload and the GitHub-packaging wizard; must
 * render inside the wizard's FormProvider (useUploadMetadataForm).
 */
export function ComponentReviewStep({
  title,
  locked = false,
  nameNotice,
  descriptionPlaceholder,
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
          <UploadMetadataFields
            nameLabel="Component Name"
            namePlaceholder="e.g. remove-outliers"
            nameReadOnly={locked}
            nameNotice={nameNotice}
            domainsReadOnly={locked}
            descriptionPlaceholder={descriptionPlaceholder}
          />
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
