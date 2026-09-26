// Single source of truth for every frontend route path - App.tsx's <Route path>
// declarations and every <Link to>/navigate()/<Navigate to> call site should reference
// this instead of a hardcoded string literal.
export const ROUTES = {
  home: '/',
  components: '/components',
  /** old path of the Components page - redirects, so existing links and bookmarks keep working */
  legacyBrowse: '/browse',
  about: '/about',
  builder: '/builder',
  builderNew: '/builder/new',
  builderWorkflow: (id: string) => `/builder/${id}`,
  profile: '/profile',
  login: '/login',
  myComponents: '/my-components',
  componentUpload: '/components/upload',
  componentDetail: (id: string) => `/components/${id}`,
  workflows: '/workflows',
  myWorkflows: '/my-workflows',
  workflowUpload: '/workflows/upload',
  workflowDetail: (id: string) => `/workflows/${id}`,
} as const;
