import { Card, CardContent } from '@/components/ui/card.tsx';
import { WorkflowUploadForm } from '@/components/workflow-upload/organisms/WorkflowUploadForm';

export default function WorkflowUploadPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Upload Workflow</h1>
      <p className="mt-1 text-slate-500">
        Upload a zip archive containing the pipeline CWL file and the step CWL files it references.
      </p>

      <Card className="mt-6">
        <CardContent className="pt-6">
          <WorkflowUploadForm />
        </CardContent>
      </Card>
    </div>
  );
}
