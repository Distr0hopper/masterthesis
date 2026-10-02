import type { ComponentDetailDisplayModel } from '@/api/components';
import { CodeBlock } from '@/components/common/CodeBlock';
import { ToolTabs } from '@/components/tool-detail/organisms/ToolTabs';

interface ComponentDefinitionProps {
  model: ComponentDetailDisplayModel;
}

/** A component's definition, embedded elsewhere (e.g. under a workflow step) - whatever its kind. */
export function ComponentDefinition({ model }: ComponentDefinitionProps) {
  if (model.kind === 'tool') return <ToolTabs model={model} />;
  return <CodeBlock title={`${model.name}.cwl`} content={model.cwlContent} downloadFilename={`${model.name}.cwl`} />;
}
