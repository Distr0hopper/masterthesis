// Single source of truth for every frontend route path - App.tsx's <Route path>
// declarations and every <Link to>/navigate()/<Navigate to> call site should reference
// this instead of a hardcoded string literal, so renaming a route only requires a change
// here.
export const ROUTES = {
  home: '/',
  browse: '/browse',
  about: '/about',
  // the builder's own overview of locally-saved draft workflows; distinct from
  // `workflows` below, which browses published workflows from the backend
  builder: '/builder',
  // literal 'new' must be declared before the :id route in App.tsx, or the dynamic
  // segment swallows it; the editor creates the draft on first Save
  builderNew: '/builder/new',
  builderWorkflow: (id: string) => `/builder/${id}`,
  profile: '/profile',
  login: '/login',
  myComponents: '/my-components',
  componentUpload: '/components/upload',
  // parameterized routes are functions rather than plain strings - the same function is
  // also used to declare the <Route path> pattern in App.tsx by calling it with the
  // literal string ':id' (e.g. componentDetail(':id') -> '/components/:id'), so the
  // segment name only has to be written once, here
  componentDetail: (id: string) => `/components/${id}`,
  workflows: '/workflows',
  myWorkflows: '/my-workflows',
  workflowUpload: '/workflows/upload',
  workflowDetail: (id: string) => `/workflows/${id}`,
} as const;
