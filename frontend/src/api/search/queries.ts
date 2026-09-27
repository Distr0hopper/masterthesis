import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { componentsService, type ComponentListItemDto } from '@/api/components';
import { workflowsService, type WorkflowListItemDto } from '@/api/workflows';

/** hits per type in the dropdown - "Show all" leads to the full list */
const HITS_PER_TYPE = 5;

export interface SearchGroup<T> {
  items: T[];
  total: number;
}

export interface GlobalSearchResult {
  components: SearchGroup<ComponentListItemDto>;
  workflows: SearchGroup<WorkflowListItemDto>;
  isFetching: boolean;
  /** true once both groups have answered for the current term */
  isReady: boolean;
}

const empty = { items: [], total: 0 };

/**
 * The navbar search: the two existing list endpoints side by side, each capped to a few
 * hits - no dedicated search endpoint, since results are never ranked across types.
 * Idle (no requests) while `term` is blank.
 */
export function useGlobalSearch(term: string): GlobalSearchResult {
  const search = term.trim();
  const enabled = search.length > 0;

  const components = useQuery({
    queryKey: ['search', 'components', search] as const,
    queryFn: () => componentsService.getAll({ search, limit: HITS_PER_TYPE }),
    enabled,
    placeholderData: keepPreviousData,
  });
  const workflows = useQuery({
    queryKey: ['search', 'workflows', search] as const,
    queryFn: () => workflowsService.getAll({ search, limit: HITS_PER_TYPE }),
    enabled,
    placeholderData: keepPreviousData,
  });

  return {
    components: components.data ? { items: components.data.content, total: components.data.totalElements } : empty,
    workflows: workflows.data ? { items: workflows.data.content, total: workflows.data.totalElements } : empty,
    isFetching: components.isFetching || workflows.isFetching,
    isReady: enabled && components.isSuccess && workflows.isSuccess,
  };
}
