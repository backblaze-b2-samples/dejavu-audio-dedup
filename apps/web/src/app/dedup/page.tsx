import { DedupView } from "@/components/dedup/dedup-view";

export default function DedupPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Deduplicate</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Fingerprint a candidate track and match it against the live index
          before you ingest it. Every run is logged to B2 under <code>results/</code>.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <DedupView />
      </div>
    </div>
  );
}
