import { CodeBlock } from '@/components/common/CodeBlock';
import type { WorkflowDetailDisplayModel } from '@/api/workflows';

interface WorkflowDefinitionProps {
  model: WorkflowDetailDisplayModel;
}

export function WorkflowDefinition({ model }: WorkflowDefinitionProps) {
  return (
    <>
      <h2 className="mt-8 text-lg font-semibold text-slate-900">Workflow Definition</h2>
      <div className="mt-4">
        <CodeBlock title={`${model.name}.cwl`} content={model.cwlContent} downloadFilename={`${model.name}.cwl`} />
      </div>
    </>
  );
}
