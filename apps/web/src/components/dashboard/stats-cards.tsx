"use client";

import { Music, Fingerprint, CopyCheck, HardDrive } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useCatalogStats } from "@/lib/queries";

export function StatsCards() {
  const { data: stats, isLoading, error, refetch } = useCatalogStats();

  // Surface fetch failures inline rather than rendering zeros — a zeroed card
  // lies about the catalog state when the API is really just unreachable.
  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const dupLabel =
    stats === undefined
      ? "0"
      : `${stats.duplicates_detected} (${stats.duplicate_pct}%)`;

  const cards = [
    { title: "Tracks in Catalog", value: stats?.tracks_in_catalog ?? 0, icon: Music },
    { title: "Fingerprints Indexed", value: stats?.fingerprints_indexed ?? 0, icon: Fingerprint },
    { title: "Duplicates Detected", value: dupLabel, icon: CopyCheck },
    { title: "Audio on B2", value: stats?.total_audio_human ?? "0 B", icon: HardDrive },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
