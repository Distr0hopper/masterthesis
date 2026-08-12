import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import {
  componentTransformer,
  useComponents,
  useDomains,
  getDomainLabel,
  type ComponentDisplayModel
} from '@/api/components';

export default function ComponentsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('');

  const { data: domains } = useDomains();
  const { data: components, isLoading } = useComponents(selectedDomain || undefined);

  const displayModels: ComponentDisplayModel[] = useMemo(() => {
    const models = componentTransformer.toListDisplayModels(components ?? []);
    const term = searchTerm.trim().toLowerCase();
    return term ? models.filter((c) => c.name.toLowerCase().includes(term)) : models;
  }, [components, searchTerm]);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Browse Repository</h1>

      <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="flex flex-1 flex-col gap-2">
          <Label htmlFor="search">Search</Label>
          <Input
            id="search"
            placeholder="Search by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2 sm:w-56">
          <Label htmlFor="domain">Domain</Label>
          <select
            id="domain"
            value={selectedDomain}
            onChange={(e) => setSelectedDomain(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm"
          >
            <option value="">All Domains</option>
            {domains?.map((domain) => (
              <option key={domain} value={domain}>
                {getDomainLabel(domain)}
              </option>
            ))}
          </select>
        </div>
      </div>

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
                <Card key={component.id}>
                  <CardContent className="flex flex-col gap-3 pt-6">
                    <Badge variant="outline" className="w-fit">
                      {component.domainDisplay}
                    </Badge>

                    <h3 className="font-mono text-lg font-bold text-slate-900">{component.name}</h3>

                    {component.description && (
                      <p className="line-clamp-2 text-sm text-slate-500">{component.description}</p>
                    )}

                    <div className="flex items-center justify-between border-t pt-3 text-sm text-slate-500">
                      <span>{component.authorDisplay}</span>
                      <span>{component.createdAtDisplay}</span>
                    </div>

                    <Button asChild className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
                      <Link to={`/components/${component.id}`}>View</Link>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
