import type { MouseEvent } from 'react';
import { Star } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button.tsx';
import { useToggleFavorite } from '@/api/components';
import { getLink } from '@/api/permissions';
import type { HateoasLinks } from '@/api/types';
import { getErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';

interface FavoriteButtonProps {
  links: HateoasLinks;
  isFavorite: boolean;
  className?: string;
}

export function FavoriteButton({ links, isFavorite, className }: FavoriteButtonProps) {
  const { mutate: toggleFavorite, isPending } = useToggleFavorite();

  const handleClick = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const link = getLink(links, isFavorite ? 'unfavorite' : 'favorite')!;
    toggleFavorite(link, { onError: (error) => toast.error(getErrorMessage(error)) });
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={handleClick}
      disabled={isPending}
      aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
      className={cn('h-8 w-8', className)}
    >
      <Star className={cn('h-4 w-4', isFavorite ? 'fill-amber-400 text-amber-400' : 'text-slate-400')} />
    </Button>
  );
}
