import { Link } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { useDomains } from '@/api/components';
import { useWorkflows } from '@/api/workflows';
import { WorkflowCard } from '@/components/workflow-browse/WorkflowCard';
import { WorkflowFilters } from '@/components/workflow-browse/WorkflowFilters';
import { Pagination } from '@/components/common/Pagination';
import { Button } from '@/components/ui/button.tsx';
import { useAuthStore } from '@/store/auth.store';
import { usePageParams } from '@/lib/usePageParams';
import { ROUTES } from '@/lib/routes';

export default function WorkflowsPage() {
  const { limit, offset, setOffset, getFilter, setFilter } = usePageParams();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  const searchTerm = getFilter('search');
  const selectedDomain = getFilter('domain');

  const { data: domains } = useDomains();
  const { data, isLoading } = useWorkflows({
    domain: selectedDomain || undefined,
    search: searchTerm || undefined,
    limit,
    offset,
  });

  const displayModels = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Browse Workflows</h1>
          <p className="mt-1 text-slate-500">Pipelines composed of chained Components.</p>
        </div>

        {isAuthenticated && (
          <Button asChild className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link to={ROUTES.workflowUpload}>
              <Upload size={14} />
              Upload Workflow
            </Link>
          </Button>
        )}
      </div>

      <WorkflowFilters
        searchTerm={searchTerm}
        selectedDomain={selectedDomain}
        domains={domains ?? []}
        onSearchTermChange={(value) => setFilter('search', value)}
        onDomainChange={(value) => setFilter('domain', value)}
      />

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading workflows...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{total} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">No workflows found.</p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {displayModels.map((workflow) => (
                <WorkflowCard key={workflow.id} workflow={workflow} />
              ))}
            </div>
          )}

          <Pagination
            totalItems={total}
            itemsPerPage={limit}
            currentPage={Math.floor(offset / limit) + 1}
            onPageChange={(page) => setOffset((page - 1) * limit)}
          />
        </>
      )}
    </div>
  );
}
