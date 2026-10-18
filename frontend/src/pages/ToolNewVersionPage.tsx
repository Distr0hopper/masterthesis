import { Link, useParams } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { useComponent, useComponentVersions } from '@/api/components';
import { canAddVersion, canRepackage } from '@/api/permissions';
import { ManualUploadWizard } from '@/components/tool-upload/organisms/ManualUploadWizard';
import { PackageFromGitHubWizard } from '@/components/tool-upload/organisms/PackageFromGitHubWizard';
import { ROUTES } from '@/lib/routes';

/**
 * The next version of a tool's lineage. A tool packaged from GitHub gets it from its repo
 * (reviewed in the packaging wizard), any other from an uploaded CWL. Either way it builds
 * on the lineage's newest version, whichever version's page this was opened from.
 */
export default function ToolNewVersionPage() {
  const { id = '' } = useParams<{ id: string }>();
  const { data: versions, isLoading: versionsLoading, error: versionsError } = useComponentVersions(id);
  const headId = versions?.reduce((head, v) => (v.version > head.version ? v : head), versions[0])?.id ?? '';
  const { data: head, isLoading: headLoading, error: headError } = useComponent(headId);

  const back = (
    <Link to={ROUTES.toolDetail(id)} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
      <ChevronLeft className="h-4 w-4" /> Back to the tool
    </Link>
  );

  if (versionsLoading || headLoading) {
    return <p className="text-slate-500">Loading...</p>;
  }

  if (versionsError || headError || !head || head.kind !== 'tool') {
    return (
      <div>
        {back}
        <p className="mt-4 text-slate-500">Tool not found.</p>
      </div>
    );
  }

  const repoUrl = canRepackage(head._links) ? head.repoUrl : null;
  const fromUpload = canAddVersion(head._links);

  return (
    <div>
      {back}
      <h1 className="mt-4 text-2xl font-semibold text-slate-900">New version of {head.name}</h1>
      {(repoUrl || fromUpload) && (
        <p className="mt-1 text-slate-500">
          {repoUrl
            ? `Package the repository again - this creates version ${head.version + 1} from its latest commit.`
            : `Upload a changed CWL file - this creates version ${head.version + 1}.`}{' '}
          The new version starts as a draft, only visible to you until you publish it.
        </p>
      )}

      <div className="mt-6">
        {repoUrl ? (
          <PackageFromGitHubWizard initialRepoUrl={repoUrl} lockRepoUrl />
        ) : fromUpload ? (
          <ManualUploadWizard parent={head} />
        ) : (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Only the owner of this tool can add new versions to it.
          </p>
        )}
      </div>
    </div>
  );
}
