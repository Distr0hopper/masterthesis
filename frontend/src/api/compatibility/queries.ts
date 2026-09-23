import { useMemo } from 'react';
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { compatibilityService } from './service';
import type { FormatPairDto, FormatPairResultDto } from './types';

/** the backend's per-request cap (MAX_COMPATIBILITY_PAIRS) */
const MAX_PAIRS_PER_REQUEST = 200;

const pairKey = (pair: FormatPairDto) => `${pair.ontologyUrl}|${pair.actualFormat}|${pair.expectedFormat}`;

export const compatibilityKeys = {
  all: ['compatibility'] as const,
  pair: (pair: FormatPairDto) => [...compatibilityKeys.all, pairKey(pair)] as const,
};

/** Answer for a pair as the builder reads it: undefined while unknown or uncheckable. */
export type CompatibilityLookup = (pair: FormatPairDto) => boolean | undefined;

async function fetchResults(pairs: FormatPairDto[]): Promise<FormatPairResultDto[]> {
  const results: FormatPairResultDto[] = [];
  for (let i = 0; i < pairs.length; i += MAX_PAIRS_PER_REQUEST) {
    const response = await compatibilityService.check(pairs.slice(i, i + MAX_PAIRS_PER_REQUEST));
    results.push(...response.results);
  }
  return results;
}

/**
 * Asks the backend about every pair not already answered, and caches each answer under its
 * own key - so the palette's batch and a later single connection share one cache. A
 * format's place in an ontology never changes, hence no staleness.
 */
async function ensureAnswered(queryClient: QueryClient, pairs: FormatPairDto[]): Promise<void> {
  const missing = pairs.filter((pair) => queryClient.getQueryData(compatibilityKeys.pair(pair)) === undefined);
  if (missing.length === 0) return;
  for (const result of await fetchResults(missing)) {
    // null (service down / unknown ontology) is not cached - the next ask retries it
    if (result.compatible !== null) {
      queryClient.setQueryData(compatibilityKeys.pair(result), result.compatible);
    }
  }
}

/** A lookup over the answers cached so far - for code outside React's render (event handlers). */
export function readCompatibility(queryClient: QueryClient): CompatibilityLookup {
  return (pair) => queryClient.getQueryData<boolean>(compatibilityKeys.pair(pair));
}

/** Blocking variant for the connect handler: resolves once `pairs` are answered (or failed). */
export async function fetchCompatibility(queryClient: QueryClient, pairs: FormatPairDto[]): Promise<void> {
  try {
    await ensureAnswered(queryClient, pairs);
  } catch {
    // an unreachable backend leaves the pairs unanswered -> unverified, never blocking
  }
}

/**
 * Background variant for the palette ranking: answers `pairs` without ever blocking, and
 * hands back a lookup that reflects whatever is known so far. Re-renders when the batch lands.
 */
export function useFormatCompatibility(pairs: FormatPairDto[]): CompatibilityLookup {
  const queryClient = useQueryClient();
  const keys = useMemo(() => pairs.map(pairKey).sort(), [pairs]);
  const { dataUpdatedAt } = useQuery({
    queryKey: [...compatibilityKeys.all, 'batch', keys],
    queryFn: async () => {
      await ensureAnswered(queryClient, pairs);
      return true;
    },
    enabled: pairs.length > 0,
    staleTime: Infinity,
    retry: false,
  });

  // dataUpdatedAt: a new identity once a batch lands, so memoised consumers recompute
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => readCompatibility(queryClient), [queryClient, dataUpdatedAt]);
}
