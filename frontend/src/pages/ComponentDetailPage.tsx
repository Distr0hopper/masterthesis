import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { toast } from 'sonner';
import {
  ChevronLeft,
  Container,
  Copy,
  Download,
  ExternalLink,
  Eye,
  FileCode,
  SlidersHorizontal,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.tsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table.tsx';
import {
  componentTransformer,
  componentsService,
  useComponent,
  type ParameterDisplayModel,
} from '@/api/components';
import { ParameterDirection } from '@/api/components/types';
import { cn } from '@/lib/utils';

function downloadTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function copyToClipboard(content: string) {
  navigator.clipboard
    .writeText(content)
    .then(() => toast.success('Copied to clipboard'))
    .catch(() => toast.error('Could not copy to clipboard'));
}

function CodeBlock({
  title,
  content,
  onCopy,
  onDownload,
}: {
  title: string;
  content: string;
  onCopy: () => void;
  onDownload: () => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="flex items-center justify-between border-b bg-slate-50 px-4 py-2">
        <span className="font-mono text-sm text-slate-500">{title}</span>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={onCopy}>
            <Copy className="mr-1 h-4 w-4" /> Copy
          </Button>
          <Button variant="ghost" size="sm" onClick={onDownload}>
            <Download className="mr-1 h-4 w-4" /> Download
          </Button>
        </div>
      </div>
      <pre className="max-h-[600px] overflow-auto bg-slate-900 p-4 text-sm text-slate-100">
        <code>{content}</code>
      </pre>
    </div>
  );
}

function ParameterList({ title, parameters }: { title: string; parameters: ParameterDisplayModel[] }) {
  return (
    <div>
      <h4 className="text-xs font-semibold tracking-wide text-slate-500">{title}</h4>
      <div className="mt-2 flex flex-col gap-1">
        {parameters.map((parameter) => (
          <div key={parameter.id} className="text-sm">
            <span className="font-mono font-semibold text-slate-900">{parameter.name}</span>{' '}
            <span className="text-slate-500">{parameter.cwlType}</span>
            {parameter.defaultValue !== null && (
              <span className="text-slate-400"> = {parameter.defaultValue}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

const tabsListClassName = 'w-full justify-start gap-6 rounded-none border-b bg-transparent p-0';
const tabsTriggerClassName =
  'gap-1.5 rounded-none border-b-2 border-transparent px-1 pb-3 data-[state=active]:border-jmu-blue-800 data-[state=active]:bg-transparent data-[state=active]:shadow-none';

export default function ComponentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: component, isLoading, error } = useComponent(id ?? '');
  const [activeTab, setActiveTab] = useState('overview');

  if (isLoading) {
    return <p className="text-slate-500">Loading component...</p>;
  }

  if (isAxiosError(error) && error.response?.status === 404) {
    return (
      <div>
        <p className="text-slate-500">Component not found.</p>
        <Link to="/browse" className="mt-4 inline-flex items-center gap-1 text-sm text-jmu-blue-800 hover:underline">
          <ChevronLeft className="h-4 w-4" /> Back to Browse
        </Link>
      </div>
    );
  }

  if (error || !component) {
    return <p className="text-slate-500">Something went wrong loading this component.</p>;
  }

  const model = componentTransformer.toDetailDisplayModel(component);

  return (
    <div>
      <Link to="/browse" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ChevronLeft className="h-4 w-4" /> Back to Browse
      </Link>

      <Card className="mt-4">
        <CardContent className="flex flex-col gap-3 pt-6">
          <Badge variant="outline" className="w-fit">
            {model.domainDisplay}
          </Badge>

          <h1 className="font-mono text-2xl font-bold text-slate-900">{model.name}</h1>

          {model.description && <p className="text-slate-600">{model.description}</p>}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3 text-sm text-slate-500">
            <span>{model.authorDisplay}</span>
            <span>Created {model.createdAtDisplay}</span>
            <span>Updated {model.updatedAtDisplay}</span>
            {model.repoUrl && (
              <a
                href={model.repoUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-jmu-blue-800 hover:underline"
              >
                <ExternalLink className="h-4 w-4" /> GitHub
              </a>
            )}
            {model.repoCommitShaShort && (
              <Badge variant="secondary" className="font-mono">
                {model.repoCommitShaShort}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardContent className="pt-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className={tabsListClassName}>
              <TabsTrigger value="overview" className={tabsTriggerClassName}>
                <Eye className="h-4 w-4" /> Overview
              </TabsTrigger>
              <TabsTrigger value="cwl" className={tabsTriggerClassName}>
                <FileCode className="h-4 w-4" /> CWL Definition
              </TabsTrigger>
              <TabsTrigger value="dockerfile" className={tabsTriggerClassName}>
                <Container className="h-4 w-4" /> Dockerfile
              </TabsTrigger>
              <TabsTrigger value="parameters" className={cn(tabsTriggerClassName, 'gap-2')}>
                <SlidersHorizontal className="h-4 w-4" /> Parameters
                <Badge variant="secondary">{model.parameters.length}</Badge>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="flex flex-col gap-6 pt-4">
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <Card>
                  <CardContent className="pt-6">
                    <p className="text-sm text-slate-500">CWL Type</p>
                    <p className="font-mono font-bold text-slate-900">{model.cwlType ?? '—'}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <p className="text-sm text-slate-500">Parameters</p>
                    <p className="text-xl font-bold text-slate-900">{model.parameters.length}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <p className="text-sm text-slate-500">Inputs</p>
                    <p className="text-xl font-bold text-slate-900">{model.inputs.length}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <p className="text-sm text-slate-500">Outputs</p>
                    <p className="text-xl font-bold text-slate-900">{model.outputs.length}</p>
                  </CardContent>
                </Card>
              </div>

              {model.description && (
                <div>
                  <h3 className="font-semibold text-slate-900">Description</h3>
                  <p className="mt-1 text-sm text-slate-600">{model.description}</p>
                </div>
              )}

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <ParameterList title="INPUTS" parameters={model.inputs} />
                <ParameterList title="OUTPUTS" parameters={model.outputs} />
              </div>
            </TabsContent>

            <TabsContent value="cwl" className="pt-4">
              <CodeBlock
                title={`${model.name}.cwl`}
                content={model.cwlContent}
                onCopy={() => copyToClipboard(model.cwlContent)}
                onDownload={() => {
                  window.location.href = componentsService.getDownloadUrl(model.id);
                }}
              />
            </TabsContent>

            <TabsContent value="dockerfile" className="pt-4">
              {model.dockerfileContent ? (
                <CodeBlock
                  title="Dockerfile"
                  content={model.dockerfileContent}
                  onCopy={() => copyToClipboard(model.dockerfileContent!)}
                  onDownload={() => downloadTextFile('Dockerfile', model.dockerfileContent!)}
                />
              ) : (
                <p className="text-sm text-slate-500">No Dockerfile available for this component.</p>
              )}
            </TabsContent>

            <TabsContent value="parameters" className="pt-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Direction</TableHead>
                    <TableHead>Default</TableHead>
                    <TableHead>Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {model.parameters.map((parameter) => (
                    <TableRow key={parameter.id}>
                      <TableCell className="font-mono font-semibold">{parameter.name}</TableCell>
                      <TableCell className="font-mono text-slate-500">{parameter.cwlType}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            parameter.direction === ParameterDirection.INPUT
                              ? 'border-blue-300 text-blue-700'
                              : 'border-green-300 text-green-700'
                          }
                        >
                          {parameter.directionDisplay}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500">{parameter.defaultValue ?? '—'}</TableCell>
                      <TableCell className="text-slate-500">{parameter.description ?? '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardContent className="pt-6">
          <h3 className="font-semibold text-slate-900">Related Components</h3>
          <p className="mt-1 text-sm italic text-slate-500">
            Components in the same domain will appear here. — Coming in a future release.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
