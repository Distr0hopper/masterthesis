import type { ComponentDisplayModel } from '@/api/components';
import type { WorkflowDisplayModel } from '@/api/workflows';
import { ROUTES } from '@/lib/routes';

export interface LatestAdditionItem {
  id: string;
  name: string;
  subtitle: string;
  href: string;
  badgeLabel: 'Component' | 'Workflow';
}

export function toLatestAdditionItems(
  components: ComponentDisplayModel[],
  workflows: WorkflowDisplayModel[],
  limit: number,
): LatestAdditionItem[] {
  const items = [
    ...components.map((c) => ({
      id: c.id,
      name: c.name,
      subtitle: `${c.domainsDisplay.join(', ')} · ${c.createdAtDisplay}`,
      href: ROUTES.componentDetail(c.id),
      badgeLabel: 'Component' as const,
      createdAt: c.createdAt,
    })),
    ...workflows.map((w) => ({
      id: w.id,
      name: w.name,
      subtitle: `${w.domainsDisplay.join(', ')} · ${w.createdAtDisplay}`,
      href: ROUTES.workflowDetail(w.id),
      badgeLabel: 'Workflow' as const,
      createdAt: w.createdAt,
    })),
  ];
  return items.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime()).slice(0, limit);
}
