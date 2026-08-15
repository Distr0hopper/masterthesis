import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { useDomains } from '@/api/components';
import { useWorkflows } from '@/api/workflows';
import { WorkflowCard } from '@/components/workflow-browse/WorkflowCard';
import { WorkflowFilters } from '@/components/workflow-browse/WorkflowFilters';
import { Button } from '@/components/ui/button.tsx';
import { useAuthStore } from '@/store/auth.store';

export default function WorkflowsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('');
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  const { data: domains } = useDomains();
  const { data: workflows, isLoading } = useWorkflows(selectedDomain || undefined);

  const models = workflows ?? [];
  const term = searchTerm.trim().toLowerCase();
  const displayModels = term ? models.filter((w) => w.name.toLowerCase().includes(term)) : models;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Browse Workflows</h1>
          <p className="mt-1 text-slate-500">Pipelines composed of chained Components.</p>
        </div>

        {isAuthenticated && (
          <Button asChild className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link to="/workflows/upload">
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
        onSearchTermChange={setSearchTerm}
        onDomainChange={setSelectedDomain}
      />

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading workflows...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{displayModels.length} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">No workflows found.</p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {displayModels.map((workflow) => (
                <WorkflowCard key={workflow.id} workflow={workflow} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
