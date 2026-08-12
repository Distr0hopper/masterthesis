import type { MouseEvent } from 'react';
import { Star } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button.tsx';
import { useFavoriteComponent, useUnfavoriteComponent } from '@/api/components';
import { getErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';

interface FavoriteButtonProps {
  componentId: string;
  isFavorite: boolean;
  className?: string;
}

export function FavoriteButton({ componentId, isFavorite, className }: FavoriteButtonProps) {
  const { mutate: favorite, isPending: isFavoriting } = useFavoriteComponent();
  const { mutate: unfavorite, isPending: isUnfavoriting } = useUnfavoriteComponent();

  const handleClick = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const mutate = isFavorite ? unfavorite : favorite;
    mutate(componentId, { onError: (error) => toast.error(getErrorMessage(error)) });
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={handleClick}
      disabled={isFavoriting || isUnfavoriting}
      aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
      className={cn('h-8 w-8', className)}
    >
      <Star className={cn('h-4 w-4', isFavorite ? 'fill-amber-400 text-amber-400' : 'text-slate-400')} />
    </Button>
  );
}
