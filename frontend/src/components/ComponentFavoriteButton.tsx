import { toast } from 'sonner';
import { FavoriteButton } from './FavoriteButton';
import { useToggleFavorite } from '@/api/components';
import { getLink } from '@/api/permissions';
import type { HateoasLinks } from '@/api/types';
import { getErrorMessage } from '@/lib/errors';

interface ComponentFavoriteButtonProps {
  links: HateoasLinks;
  isFavorite: boolean;
  className?: string;
}

export function ComponentFavoriteButton({ links, isFavorite, className }: ComponentFavoriteButtonProps) {
  const { mutate: toggleFavorite, isPending } = useToggleFavorite();

  const handleToggle = () => {
    const link = getLink(links, isFavorite ? 'unfavorite' : 'favorite')!;
    toggleFavorite({ link, isFavorite }, { onError: (error) => toast.error(getErrorMessage(error)) });
  };

  return (
    <FavoriteButton isFavorite={isFavorite} isPending={isPending} onToggle={handleToggle} className={className} />
  );
}
