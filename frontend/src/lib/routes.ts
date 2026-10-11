import type { ComponentKind } from '@/api/components/types';

// Single source of truth for every frontend route path - App.tsx's <Route path>
// declarations and every <Link to>/navigate()/<Navigate to> call site should reference
// this instead of a hardcoded string literal.
export const ROUTES = {
  home: '/',
  /** the one public list of both kinds - `?kind=` narrows it, see browseRoute */
  browse: '/browse',
  myTools: '/my-tools',
  toolUpload: '/tools/upload',
  toolDetail: (id: string) => `/tools/${id}`,
  myWorkflows: '/my-workflows',
  workflowUpload: '/workflows/upload',
  workflowDetail: (id: string) => `/workflows/${id}`,
  /**
   * A component's detail page when its kind is not known here - it resolves the kind and
   * redirects. Also what old /components/:id links and bookmarks land on.
   */
  componentDetail: (id: string) => `/components/${id}`,
  /** old paths - the per-kind lists from before /browse, and from before tools were
   *  split from components - they redirect */
  legacyTools: '/tools',
  legacyWorkflows: '/workflows',
  legacyComponents: '/components',
  legacyMyComponents: '/my-components',
  legacyComponentUpload: '/components/upload',
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

/** The routes of one kind of component. */
export interface KindRoutes {
  browse: string;
  mine: string;
  upload: string;
  detail: (id: string) => string;
}

export const KIND_ROUTES: Record<ComponentKind, KindRoutes> = {
  tool: { browse: browseRoute({ kind: 'tool' }), mine: ROUTES.myTools, upload: ROUTES.toolUpload, detail: ROUTES.toolDetail },
  workflow: {
    browse: browseRoute({ kind: 'workflow' }),
    mine: ROUTES.myWorkflows,
    upload: ROUTES.workflowUpload,
    detail: ROUTES.workflowDetail,
  },
};

/** The detail page of a component whose kind is known. */
export function componentDetailRoute(kind: ComponentKind, id: string): string {
  return KIND_ROUTES[kind].detail(id);
}
