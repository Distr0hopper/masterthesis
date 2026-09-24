import { useMemo } from 'react';
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { compatibilityService } from './service';
import type { ConnectionCheckDto, ConnectionDto } from './types';

/** Stable identity of a connection - how verdicts are looked up. */
export const connectionKey = (c: ConnectionDto) =>
  `${c.sourceComponentId}:${c.sourcePort}->${c.targetComponentId}:${c.targetPort}`;

export const compatibilityKeys = {
  all: ['compatibility'] as const,
  connection: (c: ConnectionDto) => [...compatibilityKeys.all, 'connection', connectionKey(c)] as const,
  batch: (connections: ConnectionDto[]) =>
    [...compatibilityKeys.all, 'batch', connections.map(connectionKey).sort()] as const,
};

/**
 * The backend's verdict for one connection - what `onConnect` awaits before drawing an edge.
 * Cached per connection, so re-drawing a deleted edge costs no request.
 */
export function checkConnection(queryClient: QueryClient, connection: ConnectionDto): Promise<ConnectionCheckDto> {
  return queryClient.fetchQuery({
    queryKey: compatibilityKeys.connection(connection),
    queryFn: async () => (await compatibilityService.check([connection])).results[0],
    staleTime: Infinity,
  });
}

/**
 * Verdicts for every edge on the canvas, as a Map by {@link connectionKey}.
 *
 * Shares the per-connection cache with {@link checkConnection}: only edges without a cached
 * verdict are sent (in one batch), and each answer is stored under its own connection's key.
 * So drawing an edge costs exactly the one request `onConnect` makes, deleting one costs
 * nothing, and restoring a draft checks all its edges in a single request. Components don't
 * change under a canvas, so a verdict never goes stale.
 */
export function useConnectionChecks(connections: ConnectionDto[]): Map<string, ConnectionCheckDto> {
  const queryClient = useQueryClient();
  const cached = (c: ConnectionDto) =>
    queryClient.getQueryData<ConnectionCheckDto>(compatibilityKeys.connection(c));

  const missing = connections.filter((c) => cached(c) === undefined);
  // changes exactly when verdicts arrive (or edges change) - not dataUpdatedAt, which drops
  // back to 0 once the landed batch leaves nothing missing and the key switches
  const missingKey = missing.map(connectionKey).join('|');
  useQuery({
    queryKey: compatibilityKeys.batch(missing),
    queryFn: async () => {
      const { results } = await compatibilityService.check(missing);
      missing.forEach((c, i) => queryClient.setQueryData(compatibilityKeys.connection(c), results[i]));
      return true;
    },
    enabled: missing.length > 0,
    staleTime: Infinity,
  });

  // rebuilt when the edges change or a batch lands - the verdicts themselves live in the
  // per-connection cache entries read here
  return useMemo(
    () =>
      new Map(
        connections.flatMap((c) => {
          const check = cached(c);
          return check ? [[connectionKey(c), check] as const] : [];
        }),
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [connections, missingKey],
  );
}
