import { componentTransformer, useLatestComponents } from '@/api/components';
import { useStats } from '@/api/stats';
import { HomeHero } from '@/components/home/HomeHero';
import { HomeStats } from '@/components/home/HomeStats';
import { LatestAdditions } from '@/components/home/LatestAdditions';
import { FindContent } from '@/components/home/FindContent';
import { HomeTags } from '@/components/home/HomeTags';
import { StandardsIntegrations } from '@/components/home/StandardsIntegrations';
import { HomeFooter } from '@/components/home/HomeFooter';

export default function HomePage() {
  const { data: stats } = useStats();
  const { data: latest, isLoading: isLoadingLatest } = useLatestComponents(6);
  const latestDisplayModels = componentTransformer.toListDisplayModels(latest ?? []);

  return (
    <div className="-mx-4 -mt-8">
      <HomeHero />

      <div className="mx-auto max-w-6xl px-4 py-8">
        <HomeStats stats={stats} />

        <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LatestAdditions components={latestDisplayModels} isLoading={isLoadingLatest} />
          </div>

          <div className="flex flex-col gap-6">
            <FindContent />
            <HomeTags />
          </div>
        </div>

        <StandardsIntegrations />
        <HomeFooter />
      </div>
    </div>
  );
}
