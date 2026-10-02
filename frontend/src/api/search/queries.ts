import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { componentsService, type ComponentKind } from '@/api/components';
import type { ToolListItemDto } from '@/api/tools';
import type { WorkflowListItemDto } from '@/api/workflows';

/** hits per kind in the dropdown - "Show all" leads to the full list */
const HITS_PER_KIND = 5;

export interface SearchGroup<T> {
  items: T[];
  total: number;
}

export interface GlobalSearchResult {
  tools: SearchGroup<ToolListItemDto>;
  workflows: SearchGroup<WorkflowListItemDto>;
  isFetching: boolean;
  /** true once both groups have answered for the current term */
  isReady: boolean;
}

const empty = { items: [], total: 0 };

function useKindSearch(search: string, kind: ComponentKind) {
  return useQuery({
    queryKey: ['search', kind, search] as const,
    queryFn: () => componentsService.getAll({ kind, search, limit: HITS_PER_KIND }),
    enabled: search.length > 0,
    placeholderData: keepPreviousData,
  });
}

/**
 * The navbar search: the polymorphic component list, once per kind and capped to a few
 * hits - one query per kind rather than one mixed one, so each group knows its own total
 * for "Show all". Idle (no requests) while `term` is blank.
 */
export function useGlobalSearch(term: string): GlobalSearchResult {
  const search = term.trim();
  const tools = useKindSearch(search, 'tool');
  const workflows = useKindSearch(search, 'workflow');

  return {
    tools: tools.data
      ? { items: tools.data.content.filter((c): c is ToolListItemDto => c.kind === 'tool'), total: tools.data.totalElements }
      : empty,
    workflows: workflows.data
      ? {
          items: workflows.data.content.filter((c): c is WorkflowListItemDto => c.kind === 'workflow'),
          total: workflows.data.totalElements,
        }
      : empty,
    isFetching: tools.isFetching || workflows.isFetching,
    isReady: search.length > 0 && tools.isSuccess && workflows.isSuccess,
  };
}
