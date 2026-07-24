import { IngestForm } from "@/components/catalog/ingest-form";
import { CatalogTable } from "@/components/catalog/catalog-table";

export default function CatalogPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Catalog</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Ingested tracks under the <code>catalog/</code> prefix, with
            fingerprint status and inline playback.
          </p>
        </div>
        <IngestForm />
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CatalogTable />
      </div>
    </div>
  );
}
