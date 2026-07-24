"use client";

import Link from "next/link";
import { useState } from "react";
import { Music, Trash2, ExternalLink } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useCatalog, useDeleteTrack } from "@/lib/queries";
import type { Track } from "@dejavu-audio-dedup/shared";

function fmtDuration(seconds: number | null) {
  if (seconds === null) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function StatusBadge({ track }: { track: Track }) {
  if (track.canonical_status === "duplicate") {
    return <Badge variant="destructive">Duplicate</Badge>;
  }
  if (track.fingerprint_status === "fingerprinted") {
    return <Badge variant="secondary">Fingerprinted</Badge>;
  }
  return <Badge variant="outline">Pending</Badge>;
}

export function CatalogTable() {
  const { data: tracks = [], isLoading, error, refetch } = useCatalog();
  const deleteMutation = useDeleteTrack();
  const [deleteTarget, setDeleteTarget] = useState<Track | null>(null);

  const confirmDelete = () => {
    if (!deleteTarget) return;
    const target = deleteTarget;
    deleteMutation.mutate(target.key, {
      onSuccess: () => toast.success(`${target.title || target.filename} deleted`),
      onError: (err) => toast.error(err instanceof Error ? err.message : "Delete failed"),
      onSettled: () => setDeleteTarget(null),
    });
  };

  return (
    <>
      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title">Catalog Tracks</CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          {isLoading ? (
            <div className="space-y-2 p-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState error={error} title="Couldn't load the catalog" onRetry={() => refetch()} />
          ) : tracks.length === 0 ? (
            <EmptyState
              icon={Music}
              title="No tracks in the catalog"
              description="Ingest a WAV or MP3 to fingerprint it and add it here."
            />
          ) : (
            <ul className="space-y-2">
              {tracks.map((track) => (
                <li
                  key={track.key}
                  className="rounded-lg border border-border p-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="truncate font-medium">
                        {track.title || track.filename}
                      </span>
                      <StatusBadge track={track} />
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      {track.artist ? `${track.artist} · ` : ""}
                      {fmtDuration(track.duration_seconds)} ·{" "}
                      {track.fingerprint_count.toLocaleString()} fingerprints
                    </div>
                    {track.audio_url && (
                      <audio
                        controls
                        preload="none"
                        src={track.audio_url}
                        className="h-8 w-full max-w-sm"
                      >
                        <track kind="captions" />
                      </audio>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Button asChild variant="outline" size="sm" className="h-8">
                      <Link href={`/catalog/${encodeURIComponent(track.filename)}`}>
                        <ExternalLink className="h-3.5 w-3.5" />
                        Details
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      aria-label={`Delete ${track.title || track.filename}`}
                      onClick={() => setDeleteTarget(track)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete track?</AlertDialogTitle>
            <AlertDialogDescription className="break-words">
              This removes{" "}
              <strong className="break-all font-semibold text-foreground">
                {deleteTarget?.title || deleteTarget?.filename}
              </strong>{" "}
              from B2 and drops its fingerprints from the index. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
              className={buttonVariants({ variant: "destructive" })}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
