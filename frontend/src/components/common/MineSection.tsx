import type { ReactNode } from 'react';

interface MineSectionProps {
  title: string;
  total: number;
  children: ReactNode;
}

export function MineSection({ title, total, children }: MineSectionProps) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-slate-900">
        {title} <span className="font-normal text-slate-500">({total})</span>
      </h2>
      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">{children}</div>
    </section>
  );
}
