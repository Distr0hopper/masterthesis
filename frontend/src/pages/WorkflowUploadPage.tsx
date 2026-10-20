import { WorkflowUploadWizard } from '@/components/workflow-upload/organisms/WorkflowUploadWizard';

export default function WorkflowUploadPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Upload Workflow</h1>
      <p className="mt-1 text-slate-500">
        Upload a .zip archive (with a pipeline CWL file and the step CWL files it references), or a single
        self-contained .cwl file with its steps embedded inline. Every step is configured as a tool before the
        workflow is saved.
      </p>
      <WorkflowUploadWizard />
    </div>
  );
}
