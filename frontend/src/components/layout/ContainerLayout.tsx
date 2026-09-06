import { Outlet } from 'react-router-dom';

/**
 * Default page shell: the centred, padded container every route rendered inside it
 * inherits. `mt-14` clears the fixed h-14 Header.
 */
export function ContainerLayout() {
  return (
    <main className="container mx-auto mt-14 max-w-6xl px-4 py-8">
      <Outlet />
    </main>
  );
}
