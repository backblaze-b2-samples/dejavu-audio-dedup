"use client";

import { DatabaseBackup } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useExportIndex } from "@/lib/queries";

// Triggers the "Fingerprint Index Export" capability from the UI: dumps the
// MySQL fingerprint index to `index/fingerprints.sql` on B2 (and re-saves the
// manifest) so the portable copy can re-seed a fresh MySQL. Composes the shared
// Button primitive and routes through the useExportIndex mutation hook.
export function ExportIndexButton() {
  const exportMutation = useExportIndex();

  const onExport = () => {
    exportMutation.mutate(undefined, {
      onSuccess: (res) =>
        toast.success("Fingerprint index exported to B2", {
          description: `Wrote ${res.sql_dump_key} (${res.fingerprints.toLocaleString()} fingerprints across ${res.tracks} tracks).`,
        }),
      onError: (err) =>
        toast.error(err instanceof Error ? err.message : "Index export failed"),
    });
  };

  return (
    <Button
      variant="outline"
      size="sm"
      className="h-8"
      onClick={onExport}
      disabled={exportMutation.isPending}
    >
      <DatabaseBackup className="h-3.5 w-3.5" />
      {exportMutation.isPending ? "Exporting…" : "Export SQL dump"}
    </Button>
  );
}
