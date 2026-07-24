"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { Separator } from "@/components/ui/separator";
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
import { EditTrackForm } from "./edit-track-form";
import { useDeleteTrack, useTrack } from "@/lib/queries";

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="grid grid-cols-[minmax(6rem,0.4fr)_minmax(0,1fr)] gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="break-all font-mono text-xs tabular-nums sm:text-sm">{value}</span>
    </div>
  );
}

export function TrackDetail({ trackKey }: { trackKey: string }) {
  const router = useRouter();
  const { data: track, isLoading, error, refetch } = useTrack(trackKey);
  const deleteMutation = useDeleteTrack();
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (error || !track) {
    return (
      <ErrorState
        error={error ?? new Error("Track not found")}
        title="Couldn't load this track"
        onRetry={() => refetch()}
      />
    );
  }

  const confirmDelete = () => {
    deleteMutation.mutate(track.key, {
      onSuccess: () => {
        toast.success(`${track.title || track.filename} deleted`);
        router.push("/catalog");
      },
      onError: (err) => toast.error(err instanceof Error ? err.message : "Delete failed"),
      onSettled: () => setConfirmOpen(false),
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-5">
        <div className="min-w-0">
          <Link
            href="/catalog"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Back to catalog
          </Link>
          <h1 className="page-title mt-1 flex items-center gap-2">
            <span className="truncate">{track.title || track.filename}</span>
            {track.canonical_status === "duplicate" ? (
              <Badge variant="destructive">Duplicate</Badge>
            ) : track.fingerprint_status === "fingerprinted" ? (
              <Badge variant="secondary">Fingerprinted</Badge>
            ) : (
              <Badge variant="outline">Pending</Badge>
            )}
          </h1>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-muted-foreground hover:text-destructive"
          onClick={() => setConfirmOpen(true)}
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b border-border px-5 py-4">
            <CardTitle className="card-title">Track details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 p-5">
            {track.audio_url && (
              <audio controls preload="none" src={track.audio_url} className="w-full">
                <track kind="captions" />
              </audio>
            )}
            <Separator />
            <Row label="Key" value={track.key} />
            <Row label="Artist" value={track.artist || "—"} />
            <Row
              label="Duration"
              value={track.duration_seconds !== null ? `${track.duration_seconds.toFixed(1)}s` : "—"}
            />
            {track.sample_rate && <Row label="Sample rate" value={`${track.sample_rate} Hz`} />}
            {track.channels && <Row label="Channels" value={track.channels} />}
            {track.codec && <Row label="Codec" value={track.codec} />}
            <Row label="Fingerprints" value={track.fingerprint_count.toLocaleString()} />
            {track.track_id !== null && <Row label="Index ID" value={track.track_id} />}
            {track.duplicate_of && <Row label="Duplicate of" value={track.duplicate_of} />}
            <Row label="Size" value={track.size_human} />
          </CardContent>
        </Card>

        <EditTrackForm track={track} />
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete track?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the object from B2 and drops its fingerprints from the
              index. This cannot be undone.
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
    </div>
  );
}
