import { ComponentCard } from '@/components/component-browser/ComponentCard';
import { MineSection } from '@/components/common/MineSection';
import { MyComponentCardActions } from './MyComponentCardActions';
import type { ComponentDisplayModel } from '@/api/components';
import { ROUTES } from '@/lib/routes';

interface ComponentSectionProps {
  title: string;
  components: ComponentDisplayModel[];
  total: number;
}

export function ComponentSection({ title, components, total }: ComponentSectionProps) {
  return (
    <MineSection title={title} total={total}>
      {components.map((component) => (
        <ComponentCard
          key={component.id}
          component={component}
          backTo={ROUTES.myComponents}
          actions={<MyComponentCardActions component={component} />}
        />
      ))}
    </MineSection>
  );
}
