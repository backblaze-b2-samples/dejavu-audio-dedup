import { TrackDetail } from "@/components/catalog/track-detail";

// Catalog keys are flat (`catalog/<filename>`), so the URL carries just the
// filename segment and we re-add the prefix to form the real object key.
export default async function TrackDetailPage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  const trackKey = `catalog/${decodeURIComponent(key)}`;
  return <TrackDetail trackKey={trackKey} />;
}
