import { Badge } from '@/components/ui/badge.tsx';
import { getDomainBadgeStyle, getDomainLabel, useDomains } from '@/api/components';
import { cn } from '@/lib/utils';

interface DomainBadgesProps {
  domains: string[];
  className?: string;
}

/** One tinted badge per domain. A component or workflow can span several. */
export function DomainBadges({ domains, className }: DomainBadgesProps) {
  const { data: allDomains } = useDomains();

  return (
    <>
      {domains.map((domain) => (
        <Badge
          key={domain}
          variant="outline"
          className={cn('w-fit', className)}
          style={allDomains ? getDomainBadgeStyle(domain, allDomains) : undefined}
        >
          {getDomainLabel(domain)}
        </Badge>
      ))}
    </>
  );
}
