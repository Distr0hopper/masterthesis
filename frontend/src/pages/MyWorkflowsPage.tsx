import { Link } from 'react-router-dom';
import { useMyWorkflows } from '@/api/workflows';
import { WorkflowSection } from '@/components/workflow-mine/organisms/WorkflowSection';
import { Pagination } from '@/components/common/Pagination';
import { usePageParams } from '@/lib/usePageParams';
import { ROUTES } from '@/lib/routes';

export default function MyWorkflowsPage() {
  const pending = usePageParams({ offsetKey: 'pendingOffset' });
  const published = usePageParams({ offsetKey: 'publishedOffset' });

  const { data, isLoading } = useMyWorkflows({
    limit: published.limit, // both instances read the same shared `limit` key
    publishedOffset: published.offset,
    pendingOffset: pending.offset,
  });

  const publishedTotal = data?.published.total ?? 0;
  const pendingTotal = data?.pending.total ?? 0;
  const isEmpty = publishedTotal === 0 && pendingTotal === 0;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Workflows</h1>
      <p className="mt-1 text-slate-500">Workflows you've uploaded, including those still pending validation.</p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading workflows...</p>
      ) : isEmpty ? (
        <p className="mt-8 text-slate-500">
          You haven't uploaded any workflows yet.{' '}
          <Link to={ROUTES.workflowUpload} className="font-semibold text-jmu-blue-800 hover:underline">
            Upload one
          </Link>
          .
        </p>
      ) : (
        <>
          {pendingTotal > 0 && (
            <>
              <WorkflowSection title="Unpublished Workflows" workflows={data?.pending.items ?? []} total={pendingTotal} />
              <Pagination
                totalItems={pendingTotal}
                itemsPerPage={pending.limit}
                currentPage={Math.floor(pending.offset / pending.limit) + 1}
                onPageChange={(page) => pending.setOffset((page - 1) * pending.limit)}
              />
            </>
          )}

          {publishedTotal > 0 && (
            <>
              <WorkflowSection title="Published Workflows" workflows={data?.published.items ?? []} total={publishedTotal} />
              <Pagination
                totalItems={publishedTotal}
                itemsPerPage={published.limit}
                currentPage={Math.floor(published.offset / published.limit) + 1}
                onPageChange={(page) => published.setOffset((page - 1) * published.limit)}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
