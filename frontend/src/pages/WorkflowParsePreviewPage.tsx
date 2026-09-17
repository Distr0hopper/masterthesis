import { useState } from 'react';
import { AlertTriangle, FileArchive, FileCode } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { FileDropzone } from '@/components/common/FileDropzone';
import { useParseWorkflow, type ExtractedComponentDto } from '@/api/workflows';
import { getErrorMessage } from '@/lib/errors';

/**
 * Temporary verification tool for POST /workflows/parse - detection/classification only,
 * nothing here is ever saved. Exists to check the endpoint's behaviour across all 3
 * upload shapes (pure-external zip, self-contained .cwl, mixed zip) before the real
 * confirm-and-create flow is built on top of it. Remove once that flow replaces this page.
 */
export default function WorkflowParsePreviewPage() {
  const [file, setFile] = useState<File | null>(null);
  const { mutate, data, error, isPending, reset } = useParseWorkflow();

  const handleFile = (selected: File | null) => {
    setFile(selected);
    reset();
  };

  const handleParse = () => {
    if (file) mutate(file);
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Parse Workflow (Preview)</h1>
      <p className="mt-1 text-slate-500">
        Upload a workflow <code className="font-mono text-sm">.zip</code> or a bare{' '}
        <code className="font-mono text-sm">.cwl</code> file to see how it gets classified - self-contained,
        external-only, or mixed. This calls <code className="font-mono text-sm">POST /workflows/parse</code>{' '}
        only; nothing is created or saved.
      </p>

      <Card className="mt-6">
        <CardContent className="flex flex-col gap-4 pt-6">
          <FileDropzone
            value={file}
            onChange={handleFile}
            accept=".zip,.cwl"
            label="Workflow file"
            helperText="A .zip archive or a bare .cwl file, or click to browse"
          />

          <Button
            onClick={handleParse}
            disabled={!file || isPending}
            className="w-fit bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {isPending ? 'Parsing...' : 'Parse'}
          </Button>

          {error && (
            <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
              {getErrorMessage(error, 'Could not parse this file.')}
            </p>
          )}
        </CardContent>
      </Card>

      {data && (
        <div className="mt-6 flex flex-col gap-4">
          <Card>
            <CardContent className="flex flex-col gap-3 pt-6">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="gap-1">
                  {data.isZip ? <FileArchive className="h-3 w-3" /> : <FileCode className="h-3 w-3" />}
                  {data.isZip ? 'ZIP archive' : 'Bare .cwl file'}
                </Badge>
                <Badge variant={data.isSelfContained ? 'default' : 'secondary'}>
                  {data.isSelfContained ? 'Self-contained (has inline tools)' : 'External references only'}
                </Badge>
                <Badge variant="outline">{data.stepCount} step(s)</Badge>
              </div>

              <div className="text-sm text-slate-700">
                <span className="text-slate-500">Workflow name: </span>
                {data.workflowName ?? <span className="text-slate-400">(none - no label:/filename found)</span>}
              </div>

              {data.missingExternalRefs.length > 0 && (
                <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    Referenced but missing from the archive:{' '}
                    <span className="font-mono">{data.missingExternalRefs.join(', ')}</span>
                  </span>
                </div>
              )}

              {data.unsupportedInlineSteps.length > 0 && (
                <div className="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                  <span>
                    Inline but not a CommandLineTool (e.g. an ExpressionTool), counted in step_count but not
                    extracted: <span className="font-mono">{data.unsupportedInlineSteps.join(', ')}</span>
                  </span>
                </div>
              )}

              {data.externalRefs.length > 0 && (
                <div className="text-sm text-slate-700">
                  <span className="text-slate-500">External refs: </span>
                  <span className="font-mono">{data.externalRefs.join(', ')}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {data.extractedComponents.length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Extracted components ({data.extractedComponents.length})
              </h2>
              {data.extractedComponents.map((component) => (
                <ExtractedComponentCard key={component.stepId} component={component} />
              ))}
            </div>
          )}

          <details className="rounded-md border border-slate-200 p-3">
            <summary className="cursor-pointer text-sm font-medium text-slate-700">Raw response</summary>
            <pre className="mt-2 overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
              {JSON.stringify(data, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

function ExtractedComponentCard({ component }: { component: ExtractedComponentDto }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 pt-6">
        <div className="flex items-center justify-between gap-2">
          <span className="break-all font-mono text-sm font-semibold text-slate-900">
            {component.suggestedName}
          </span>
          <span className="shrink-0 text-xs text-slate-400">from step "{component.stepId}"</span>
        </div>

        <p className="text-sm text-slate-500">
          {component.inputCount} input(s) &middot; {component.outputCount} output(s)
        </p>

        {component.description && <p className="text-sm text-slate-700">{component.description}</p>}

        <details>
          <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-900">
            View extracted CWL
          </summary>
          <pre className="mt-2 overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
            {component.cwlContent}
          </pre>
        </details>
      </CardContent>
    </Card>
  );
}
