import { useState } from 'react';
import { componentTransformer, useComponents, useDomains } from '@/api/components';
import { ComponentCard } from '@/components/component-browser/ComponentCard';
import { ComponentFilters } from '@/components/component-browser/ComponentFilters';

export default function ComponentsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('');

  const { data: domains } = useDomains();
  const { data: components, isLoading } = useComponents(selectedDomain || undefined);

  const models = componentTransformer.toListDisplayModels(components ?? []);
  const term = searchTerm.trim().toLowerCase();
  const displayModels = term ? models.filter((c) => c.name.toLowerCase().includes(term)) : models;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Browse Repository</h1>

      <ComponentFilters
        searchTerm={searchTerm}
        selectedDomain={selectedDomain}
        domains={domains ?? []}
        onSearchTermChange={setSearchTerm}
        onDomainChange={setSelectedDomain}
      />

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading components...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{displayModels.length} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">No components found.</p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {displayModels.map((component) => (
                <ComponentCard key={component.id} component={component} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
