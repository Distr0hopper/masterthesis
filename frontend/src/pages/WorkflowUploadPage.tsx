import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { FileDropzone } from '@/components/common/FileDropzone';
import { DomainMultiSelect } from '@/components/workflow-upload/common/DomainMultiSelect';
import { DomainSelect } from '@/components/component-upload/common/DomainSelect';
import { useCreateWorkflow, useParseWorkflow, type ParseWorkflowResponseDto } from '@/api/workflows';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

export default function WorkflowUploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const parseMutation = useParseWorkflow();
  const createMutation = useCreateWorkflow();

  const [name, setName] = useState('');
  const [domains, setDomains] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [componentDomain, setComponentDomain] = useState('');
  const [componentNames, setComponentNames] = useState<Record<string, string>>({});

  const handleFile = (selected: File | null) => {
    setFile(selected);
    parseMutation.reset();
    createMutation.reset();
  };

  const handleParse = () => {
    if (!file) return;
    parseMutation.mutate(file, {
      onSuccess: (result: ParseWorkflowResponseDto) => {
        setName(result.workflowName ?? '');
        setDomains([]);
        setDescription('');
        setComponentDomain('');
        setComponentNames(
          Object.fromEntries(result.extractedComponents.map((c) => [c.stepId, c.suggestedName])),
        );
      },
    });
  };

  const parsed = parseMutation.data;
  const hasBlockingIssues = Boolean(
    parsed && (parsed.missingExternalRefs.length > 0 || parsed.unsupportedInlineSteps.length > 0),
  );
  const hasExtractedComponents = Boolean(parsed && parsed.extractedComponents.length > 0);

  const canSave =
    !!parsed &&
    !hasBlockingIssues &&
    !!file &&
    name.trim().length > 0 &&
    domains.length > 0 &&
    (!hasExtractedComponents || componentDomain.length > 0);

  const handleSave = () => {
    if (!file || !parsed) return;
    createMutation.mutate(
      {
        file,
        dto: {
          name,
          domains,
          description: description || null,
          componentDomain: hasExtractedComponents ? componentDomain : null,
          componentOverrides: parsed.extractedComponents.map((c) => ({
            stepId: c.stepId,
            name: componentNames[c.stepId] ?? c.suggestedName,
          })),
        },
      },
      {
        onSuccess: (created) => navigate(ROUTES.workflowDetail(created.id)),
      },
    );
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Upload Workflow</h1>
      <p className="mt-1 text-slate-500">
        Upload a .zip archive (with a pipeline CWL file and the step CWL files it references), or a single
        self-contained .cwl file with its steps embedded inline.
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
            disabled={!file || parseMutation.isPending}
            className="w-fit bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {parseMutation.isPending ? 'Parsing...' : 'Parse'}
          </Button>
          {parseMutation.error && (
            <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
              {getErrorMessage(parseMutation.error, 'Could not parse this file.')}
            </p>
          )}
        </CardContent>
      </Card>

      {parsed && (
        <Card className="mt-6">
          <CardContent className="flex flex-col gap-4 pt-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{parsed.stepCount} step(s)</Badge>
              {parsed.isSelfContained && <Badge variant="secondary">Self-contained</Badge>}
              {hasExtractedComponents && (
                <Badge variant="secondary">{parsed.extractedComponents.length} inline component(s)</Badge>
              )}
            </div>

            {parsed.missingExternalRefs.length > 0 && (
              <div className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Missing referenced file(s) in the archive: {parsed.missingExternalRefs.join(', ')}. Fix the
                  archive and re-parse before saving.
                </span>
              </div>
            )}
            {parsed.unsupportedInlineSteps.length > 0 && (
              <div className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Step(s) with an unsupported inline definition (not a CommandLineTool):{' '}
                  {parsed.unsupportedInlineSteps.join(', ')}. These cannot be saved yet.
                </span>
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Label htmlFor="workflow-name">Name</Label>
              <Input id="workflow-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>

            <DomainMultiSelect value={domains} onChange={setDomains} />

            <div className="flex flex-col gap-2">
              <Label htmlFor="workflow-description">Description</Label>
              <Textarea
                id="workflow-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            {hasExtractedComponents && (
              <div className="flex flex-col gap-4 rounded-md border border-input p-4">
                <p className="text-sm font-medium text-slate-900">Extracted components</p>
                <DomainSelect value={componentDomain} onChange={setComponentDomain} />
                <div className="flex flex-col gap-3">
                  {parsed.extractedComponents.map((c) => (
                    <div key={c.stepId} className="flex flex-col gap-1">
                      <Label htmlFor={`component-name-${c.stepId}`}>{c.stepId}</Label>
                      <Input
                        id={`component-name-${c.stepId}`}
                        value={componentNames[c.stepId] ?? ''}
                        onChange={(e) => setComponentNames((prev) => ({ ...prev, [c.stepId]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {createMutation.error && (
              <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
                {getErrorMessage(createMutation.error, 'Could not save this workflow.')}
              </p>
            )}

            <Button
              onClick={handleSave}
              disabled={!canSave || createMutation.isPending}
              className="w-fit bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {createMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
