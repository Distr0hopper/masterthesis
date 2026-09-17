import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { WorkflowUploadForm } from '@/components/workflow-upload/organisms/WorkflowUploadForm';
import { ROUTES } from '@/lib/routes';

export default function WorkflowUploadPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Upload Workflow</h1>
      <p className="mt-1 text-slate-500">
        Upload a zip archive containing the pipeline CWL file and the step CWL files it references.
      </p>
      <p className="mt-1 text-sm text-slate-400">
        Only external step references are supported here.{' '}
        <Link to={ROUTES.workflowParsePreview} className="text-jmu-blue-800 hover:underline">
          Try the experimental parser
        </Link>{' '}
        to preview self-contained or mixed workflows (nothing is saved yet).
      </p>

      <Card className="mt-6">
        <CardContent className="pt-6">
          <WorkflowUploadForm />
        </CardContent>
      </Card>
    </div>
  );
}
