import { toast } from 'sonner';
import { FavoriteButton } from './FavoriteButton';
import { useToggleWorkflowFavorite } from '@/api/workflows';
import { getLink } from '@/api/permissions';
import type { HateoasLinks } from '@/api/types';
import { getErrorMessage } from '@/lib/errors';

interface WorkflowFavoriteButtonProps {
  links: HateoasLinks;
  isFavorite: boolean;
  className?: string;
}

export function WorkflowFavoriteButton({ links, isFavorite, className }: WorkflowFavoriteButtonProps) {
  const { mutate: toggleFavorite, isPending } = useToggleWorkflowFavorite();

  const handleToggle = () => {
    const link = getLink(links, isFavorite ? 'unfavorite' : 'favorite')!;
    toggleFavorite({ link, isFavorite }, { onError: (error) => toast.error(getErrorMessage(error)) });
  };

  return (
    <FavoriteButton isFavorite={isFavorite} isPending={isPending} onToggle={handleToggle} className={className} />
  );
}
