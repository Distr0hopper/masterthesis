import type { ComponentDisplayModel, ComponentKind } from '@/api/components';
import { componentDetailRoute } from '@/lib/routes';

export interface LatestAdditionItem {
  id: string;
  name: string;
  href: string;
  kind: ComponentKind;
  domains: string[];
  createdAtDisplay: string;
}

export function toLatestAdditionItems(components: ComponentDisplayModel[]): LatestAdditionItem[] {
  return components.map((c) => ({
    id: c.id,
    name: c.name,
    href: componentDetailRoute(c.kind, c.id),
    kind: c.kind,
    domains: c.domains,
    createdAtDisplay: c.createdAtDisplay,
  }));
}
