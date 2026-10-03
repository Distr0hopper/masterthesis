import type { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { FormatLabelFields } from '@/components/common/FormatLabelFields';
import { UploadMetadataFields } from '@/components/common/UploadMetadataFields';
import { ToolTabs } from '@/components/tool-detail/organisms/ToolTabs';
import type { FormatLabelDraft, PreviewParameterDto } from '@/api/components';
import type { ToolDetailDisplayModel } from '@/api/tools';

interface ToolReviewStepProps {
  /** e.g. "New tool" or "New version of remove-outliers" */
  title: ReactNode;
  /** name and domains shown but not editable - a new version keeps its lineage's */
  locked?: boolean;
  /** shown under the name - e.g. that it's taken, or which tool gets the new version */
  nameNotice?: ReactNode;
  descriptionPlaceholder?: string;
  /** the preview with the current details and draft labels applied (withFormatLabels) */
  previewModel: ToolDetailDisplayModel;
  /** the raw preview ports - which of them accept a hand label */
  parameters: PreviewParameterDto[];
  formatLabels: FormatLabelDraft;
  onFormatLabelsChange: (value: FormatLabelDraft) => void;
}

/**
 * The last step before a tool is created: everything that gets saved - details and
 * hand labels for File ports without an ontology format - editable next to the live
 * tool preview. Shared by the manual-upload and the GitHub-packaging wizard; must
 * render inside the wizard's FormProvider (useUploadMetadataForm).
 */
export function ToolReviewStep({
  title,
  locked = false,
  nameNotice,
  descriptionPlaceholder,
  previewModel,
  parameters,
  formatLabels,
  onFormatLabelsChange,
}: ToolReviewStepProps) {
  return (
    <>
      <Card className="mt-6">
        <CardContent className="flex flex-col gap-6 pt-6">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium text-slate-900">{title}</p>
            <Badge variant="secondary">v{previewModel.version}</Badge>
          </div>
          <UploadMetadataFields
            nameLabel="Tool Name"
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
      <ToolTabs model={previewModel} isPreview />
    </>
  );
}
