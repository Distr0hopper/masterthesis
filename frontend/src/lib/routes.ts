import type { ComponentKind } from '@/api/components/types';

// Single source of truth for every frontend route path - App.tsx's <Route path>
// declarations and every <Link to>/navigate()/<Navigate to> call site should reference
// this instead of a hardcoded string literal.
export const ROUTES = {
  home: '/',
  tools: '/tools',
  myTools: '/my-tools',
  toolUpload: '/tools/upload',
  toolDetail: (id: string) => `/tools/${id}`,
  workflows: '/workflows',
  myWorkflows: '/my-workflows',
  workflowUpload: '/workflows/upload',
  workflowDetail: (id: string) => `/workflows/${id}`,
  /**
   * A component's detail page when its kind is not known here - it resolves the kind and
   * redirects. Also what old /components/:id links and bookmarks land on.
   */
  componentDetail: (id: string) => `/components/${id}`,
  /** old paths from before tools were split from components - they redirect */
  legacyBrowse: '/browse',
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

/** The routes of one kind of component. */
export interface KindRoutes {
  browse: string;
  mine: string;
  upload: string;
  detail: (id: string) => string;
}

export const KIND_ROUTES: Record<ComponentKind, KindRoutes> = {
  tool: { browse: ROUTES.tools, mine: ROUTES.myTools, upload: ROUTES.toolUpload, detail: ROUTES.toolDetail },
  workflow: {
    browse: ROUTES.workflows,
    mine: ROUTES.myWorkflows,
    upload: ROUTES.workflowUpload,
    detail: ROUTES.workflowDetail,
  },
};

/** The detail page of a component whose kind is known. */
export function componentDetailRoute(kind: ComponentKind, id: string): string {
  return KIND_ROUTES[kind].detail(id);
}
