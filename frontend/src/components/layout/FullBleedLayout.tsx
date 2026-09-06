import { Outlet } from 'react-router-dom';

/**
 * Shell for pages that need the whole viewport below the Header instead of the centred
 * ContainerLayout - currently only the Workflow Builder. The explicit height (rather
 * than h-full) is what lets React Flow size its canvas: it measures its container, and
 * a percentage height would resolve against an auto-height ancestor chain.
 */
export function FullBleedLayout() {
  return (
    <main className="mt-14 h-[calc(100vh-3.5rem)] overflow-hidden">
      <Outlet />
    </main>
  );
}
