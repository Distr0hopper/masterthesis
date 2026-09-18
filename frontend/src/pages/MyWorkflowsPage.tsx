import { Link } from 'react-router-dom';
import { useMyWorkflows } from '@/api/workflows';
import { WorkflowSection } from '@/components/workflow-mine/organisms/WorkflowSection';
import { Pagination } from '@/components/common/Pagination';
import { useSplitPageParams } from '@/lib/useSplitPageParams';
import { ROUTES } from '@/lib/routes';

export default function MyWorkflowsPage() {
  const { limit, published, unpublished } = useSplitPageParams();

  const { data, isLoading } = useMyWorkflows({
    limit,
    publishedOffset: published.offset,
    unpublishedOffset: unpublished.offset,
  });

  const publishedTotal = data?.published.total ?? 0;
  const unpublishedTotal = data?.unpublished.total ?? 0;
  const isEmpty = publishedTotal === 0 && unpublishedTotal === 0;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Workflows</h1>
      <p className="mt-1 text-slate-500">
        Workflows you've uploaded or published from the Workflow Builder, including those still pending
        validation.
      </p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading workflows...</p>
      ) : isEmpty ? (
        <p className="mt-8 text-slate-500">
          You don't have any workflows yet.{' '}
          <Link to={ROUTES.workflowUpload} className="font-semibold text-jmu-blue-800 hover:underline">
            Upload one
          </Link>{' '}
          or{' '}
          <Link to={ROUTES.builder} className="font-semibold text-jmu-blue-800 hover:underline">
            build one in the Workflow Builder
          </Link>
          .
        </p>
      ) : (
        <>
          {unpublishedTotal > 0 && (
            <>
              <WorkflowSection
                title="Unpublished Workflows"
                workflows={data?.unpublished.items ?? []}
                total={unpublishedTotal}
              />
              <Pagination
                totalItems={unpublishedTotal}
                itemsPerPage={limit}
                currentPage={unpublished.page}
                onPageChange={unpublished.goToPage}
              />
            </>
          )}

          {publishedTotal > 0 && (
            <>
              <WorkflowSection
                title="Published Workflows"
                workflows={data?.published.items ?? []}
                total={publishedTotal}
              />
              <Pagination
                totalItems={publishedTotal}
                itemsPerPage={limit}
                currentPage={published.page}
                onPageChange={published.goToPage}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
