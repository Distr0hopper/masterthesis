import type { ComponentKind } from '@/api/components/types';

// Single source of truth for every frontend route path - App.tsx's <Route path>
// declarations and every <Link to>/navigate()/<Navigate to> call site should reference
// this instead of a hardcoded string literal.
export const ROUTES = {
  home: '/',
  /** the one public list of both kinds - `?kind=` narrows it, see browseRoute */
  browse: '/browse',
  toolUpload: '/tools/upload',
  toolDetail: (id: string) => `/tools/${id}`,
  toolNewVersion: (id: string) => `/tools/${id}/new-version`,
  /** the caller's own components of both kinds - `?kind=` narrows it, see myComponentsRoute */
  myComponents: '/my-components',
  workflowUpload: '/workflows/upload',
  workflowDetail: (id: string) => `/workflows/${id}`,
  workflowNewVersion: (id: string) => `/workflows/${id}/new-version`,
  about: '/about',
  builder: '/builder',
  builderNew: '/builder/new',
  builderWorkflow: (id: string) => `/builder/${id}`,
  profile: '/profile',
  login: '/login',
} as const;

/** The browse list, optionally pre-filtered to one kind and/or a search term. */
export function browseRoute({ kind, search }: { kind?: ComponentKind; search?: string } = {}): string {
  const params = new URLSearchParams();
  if (kind) params.set('kind', kind);
  if (search) params.set('search', search);
  const query = params.toString();
  return query ? `${ROUTES.browse}?${query}` : ROUTES.browse;
}

/** The caller's own components, optionally pre-filtered to one kind. */
export function myComponentsRoute({ kind }: { kind?: ComponentKind } = {}): string {
  return kind ? `${ROUTES.myComponents}?kind=${kind}` : ROUTES.myComponents;
}

/** The routes of one kind of component. */
export interface KindRoutes {
  browse: string;
  upload: string;
  detail: (id: string) => string;
}

export const KIND_ROUTES: Record<ComponentKind, KindRoutes> = {
  tool: { browse: browseRoute({ kind: 'tool' }), upload: ROUTES.toolUpload, detail: ROUTES.toolDetail },
  workflow: {
    browse: browseRoute({ kind: 'workflow' }),
    upload: ROUTES.workflowUpload,
    detail: ROUTES.workflowDetail,
  },
};

/** The detail page of a component whose kind is known. */
export function componentDetailRoute(kind: ComponentKind, id: string): string {
  return KIND_ROUTES[kind].detail(id);
}
