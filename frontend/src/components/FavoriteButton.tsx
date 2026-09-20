import type { MouseEvent } from 'react';
import { Star } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { cn } from '@/lib/utils';

interface FavoriteButtonProps {
  isFavorite: boolean;
  isPending: boolean;
  onToggle: () => void;
  className?: string;
}

export function FavoriteButton({ isFavorite, isPending, onToggle, className }: FavoriteButtonProps) {
  const handleClick = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onToggle();
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
