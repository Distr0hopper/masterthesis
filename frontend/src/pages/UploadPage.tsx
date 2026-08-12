import { Card, CardContent } from '@/components/ui/card.tsx';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.tsx';
import { ManualUploadForm } from '@/components/component-upload/organisms/ManualUploadForm';
import { PackageFromGitHubForm } from '@/components/component-upload/organisms/PackageFromGitHubForm';

const TABS_LIST_CLASSNAME = 'w-full justify-start gap-6 rounded-none border-b bg-transparent p-0';
const TAB_TRIGGER_CLASSNAME =
  'rounded-none border-b-2 border-transparent px-1 pb-3 data-[state=active]:border-jmu-blue-800 data-[state=active]:bg-transparent data-[state=active]:shadow-none';

export default function UploadPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Upload Component</h1>
      <p className="mt-1 text-slate-500">Package a CWL CommandLineTool manually or from a MoveApps GitHub repository.</p>

      <Card className="mt-6">
        <CardContent className="pt-6">
          <Tabs defaultValue="manual">
            <TabsList className={TABS_LIST_CLASSNAME}>
              <TabsTrigger value="manual" className={TAB_TRIGGER_CLASSNAME}>
                Manual Upload
              </TabsTrigger>
              <TabsTrigger value="github" className={TAB_TRIGGER_CLASSNAME}>
                Package from GitHub
              </TabsTrigger>
            </TabsList>

            <TabsContent value="manual" className="pt-6">
              <ManualUploadForm />
            </TabsContent>

            <TabsContent value="github" className="pt-6">
              <PackageFromGitHubForm />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
