"use client";

import { useState } from "react";
import { ScanSearch, CheckCircle2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCatalog } from "@/lib/queries";
import { runDedup } from "@/lib/api-client";
import type { DedupResult } from "@dejavu-audio-dedup/shared";

export function DedupView() {
  const { data: tracks = [] } = useCatalog();
  const [source, setSource] = useState<"upload" | "existing">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [existingKey, setExistingKey] = useState("");
  const [sensitivity, setSensitivity] = useState("balanced");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<DedupResult | null>(null);

  const onRun = async () => {
    if (source === "upload" && !file) {
      toast.error("Choose a WAV or MP3 candidate.");
      return;
    }
    if (source === "existing" && !existingKey) {
      toast.error("Pick a catalog track to check.");
      return;
    }
    setRunning(true);
    setResult(null);
    try {
      const res = await runDedup({
        file: source === "upload" ? file ?? undefined : undefined,
        existingKey: source === "existing" ? existingKey : undefined,
        sensitivity,
      });
      setResult(res);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Dedup failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title">Check a candidate</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5 p-5">
          <div className="space-y-2">
            <Label>Candidate source</Label>
            <Select value={source} onValueChange={(v) => setSource(v as "upload" | "existing")}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="upload">Upload a file</SelectItem>
                <SelectItem value="existing">Pick a catalog track</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {source === "upload" ? (
            <div className="space-y-2">
              <Label htmlFor="cand-file">Candidate file</Label>
              <Input
                id="cand-file"
                type="file"
                accept="audio/wav,audio/mpeg,.wav,.mp3"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <p className="text-sm text-muted-foreground">
                WAV or MP3. It is matched against the live index but not ingested.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Catalog track</Label>
              <Select value={existingKey} onValueChange={setExistingKey}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a track…" />
                </SelectTrigger>
                <SelectContent>
                  {tracks.map((t) => (
                    <SelectItem key={t.key} value={t.key}>
                      {t.title || t.filename}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <Label>Match sensitivity</Label>
            <Select value={sensitivity} onValueChange={setSensitivity}>
              <SelectTrigger className="w-60">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="strict">Strict</SelectItem>
                <SelectItem value="balanced">Balanced</SelectItem>
                <SelectItem value="loose">Loose</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button onClick={onRun} disabled={running}>
            <ScanSearch className="h-4 w-4" />
            {running ? "Matching..." : "Run dedup"}
          </Button>
        </CardContent>
      </Card>

      <ResultPanel result={result} />
    </div>
  );
}

function ResultPanel({ result }: { result: DedupResult | null }) {
  if (!result) {
    return (
      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title">Result</CardTitle>
        </CardHeader>
        <CardContent className="p-5 text-sm text-muted-foreground">
          Run a check to see whether the candidate already exists in the catalog.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="border-b border-border px-5 py-4">
        <CardTitle className="card-title">Result</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center gap-2">
          {result.is_duplicate ? (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3.5 w-3.5" /> Duplicate
            </Badge>
          ) : (
            <Badge variant="secondary" className="gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" /> No duplicate
            </Badge>
          )}
          <span className="text-xs text-muted-foreground">
            sensitivity: {result.sensitivity} · threshold {result.threshold}
          </span>
        </div>

        {result.is_duplicate && result.top_match && (
          <div className="space-y-2 rounded-lg border border-border p-3">
            <div className="text-sm font-medium">
              {result.matched_title || result.matched_key}
            </div>
            <div className="text-xs text-muted-foreground">
              confidence {(result.top_match.confidence * 100).toFixed(1)}% · offset{" "}
              {result.top_match.offset_seconds.toFixed(1)}s ·{" "}
              {result.top_match.hashes_matched.toLocaleString()} hashes matched
            </div>
            {result.matched_audio_url && (
              <audio controls preload="none" src={result.matched_audio_url} className="w-full">
                <track kind="captions" />
              </audio>
            )}
          </div>
        )}

        {result.matches.length > 0 && (
          <>
            <Separator />
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              All matches
            </p>
            <ul className="space-y-1.5 text-sm">
              {result.matches.map((m, i) => (
                <li key={`${m.track_name}-${i}`} className="flex items-center justify-between gap-2">
                  <span className="truncate">{m.title || m.track_name}</span>
                  <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                    {(m.confidence * 100).toFixed(1)}%
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        {result.result_key && (
          <p className="text-xs text-muted-foreground">
            Logged to B2: <code className="break-all">{result.result_key}</code>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
