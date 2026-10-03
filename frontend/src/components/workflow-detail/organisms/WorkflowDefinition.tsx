import { Card, CardContent } from '@/components/ui/card.tsx';
import { CodeBlock } from '@/components/common/CodeBlock';
import { ParameterList } from '@/components/component-detail/common/ParameterList';
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

      {/* the workflow's own interface - what a parent workflow sees when it nests this one */}
      <Card className="mt-4">
        <CardContent className="pt-6">
          <h3 className="font-semibold text-slate-900">Ports</h3>
          <p className="mt-1 text-sm text-slate-500">
            The inputs and outputs of the workflow as a whole - what it exposes when nested in another workflow.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
            <ParameterList title="INPUTS" parameters={model.inputs} />
            <ParameterList title="OUTPUTS" parameters={model.outputs} />
          </div>
        </CardContent>
      </Card>
    </>
  );
}
