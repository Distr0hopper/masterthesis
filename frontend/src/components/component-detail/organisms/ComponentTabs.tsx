import type { ComponentType } from 'react';
import { Container, Eye, FileCode, SlidersHorizontal, type LucideProps } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.tsx';
import { componentsService } from '@/api/components';
import type { ComponentDetailDisplayModel } from '@/api/components';
import { cn } from '@/lib/utils';
import { CodeBlock } from '@/components/common/CodeBlock';
import { ParameterTable } from '../common/ParameterTable';
import { ComponentOverview } from './ComponentOverview';

const TABS_LIST_CLASSNAME = 'w-full justify-start gap-6 rounded-none border-b bg-transparent p-0';
const TAB_TRIGGER_CLASSNAME =
  'gap-1.5 rounded-none border-b-2 border-transparent px-1 pb-3 data-[state=active]:border-jmu-blue-800 data-[state=active]:bg-transparent data-[state=active]:shadow-none';

interface TabConfig {
  value: string;
  label: string;
  icon: ComponentType<LucideProps>;
  badge?: number;
}

interface ComponentTabsProps {
  model: ComponentDetailDisplayModel;
  /**
   * Render a component that isn't persisted yet (a workflow-upload preview). Its `id` is
   * a placeholder, so the CWL tab downloads the in-memory content as a client-side blob
   * instead of pointing at a component download endpoint that would 404.
   */
  isPreview?: boolean;
}

export function ComponentTabs({ model, isPreview = false }: ComponentTabsProps) {
  const tabs: TabConfig[] = [
    { value: 'overview', label: 'Overview', icon: Eye },
    { value: 'cwl', label: 'CWL Definition', icon: FileCode },
    { value: 'dockerfile', label: 'Dockerfile', icon: Container },
    { value: 'parameters', label: 'Parameters', icon: SlidersHorizontal, badge: model.parameters.length },
  ];

  return (
    <Card className="mt-6">
      <CardContent className="pt-6">
        <Tabs defaultValue="overview">
          <TabsList className={TABS_LIST_CLASSNAME}>
            {tabs.map(({ value, label, icon: Icon, badge }) => (
              <TabsTrigger key={value} value={value} className={cn(TAB_TRIGGER_CLASSNAME, badge !== undefined && 'gap-2')}>
                <Icon className="h-4 w-4" /> {label}
                {badge !== undefined && <Badge variant="secondary">{badge}</Badge>}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview" className="pt-4">
            <ComponentOverview model={model} />
          </TabsContent>

          <TabsContent value="cwl" className="pt-4">
            <CodeBlock
              title={`${model.name}.cwl`}
              content={model.cwlContent}
              {...(isPreview
                ? { downloadFilename: `${model.name}.cwl` }
                : { downloadUrl: componentsService.getDownloadUrl(model.id) })}
            />
          </TabsContent>

          <TabsContent value="dockerfile" className="pt-4">
            {model.dockerfileContent ? (
              <CodeBlock title="Dockerfile" content={model.dockerfileContent} downloadFilename="Dockerfile" />
            ) : model.dockerPullReference ? (
              <a
                href={model.dockerPullUrl ?? undefined}
                target="_blank"
                rel="noreferrer"
                className="flex items-baseline gap-2 hover:underline"
              >
                <span className="font-mono text-sm font-semibold text-slate-900">{model.dockerPullReference}</span>
              </a>
            ) : (
              <p className="text-sm text-slate-500">No Dockerfile available for this component.</p>
            )}
          </TabsContent>

          <TabsContent value="parameters" className="pt-4">
            <ParameterTable parameters={model.parameters} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
