"use client";

import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Music, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import { useQueryClient } from "@tanstack/react-query";
import { ingestTrack } from "@/lib/api-client";
import { qk } from "@/lib/queries";

type IngestValues = { title: string; artist: string; sensitivity: string };

export function IngestForm() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const form = useForm<IngestValues>({
    defaultValues: { title: "", artist: "", sensitivity: "balanced" },
  });

  const reset = () => {
    form.reset({ title: "", artist: "", sensitivity: "balanced" });
    setFile(null);
    if (fileInput.current) fileInput.current.value = "";
  };

  const onSubmit = async (values: IngestValues) => {
    if (!file) {
      toast.error("Choose a WAV or MP3 file to ingest.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await ingestTrack(file, values);
      if (res.is_duplicate) {
        toast.warning(`Likely duplicate of ${res.matched_title || res.matched_key}`, {
          description: `Ingested and flagged (${res.fingerprint_count} fingerprints).`,
        });
      } else {
        toast.success("Track ingested", { description: res.message });
      }
      qc.invalidateQueries({ queryKey: qk.all });
      setOpen(false);
      reset();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm" className="h-8">
          <Music className="h-3.5 w-3.5" />
          Ingest track
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Ingest a track</DialogTitle>
          <DialogDescription>
            Store the audio on B2 and fingerprint it into the live index. A
            match against an existing track is flagged automatically.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="audio-file">Audio file</Label>
              <Input
                id="audio-file"
                ref={fileInput}
                type="file"
                accept="audio/wav,audio/mpeg,.wav,.mp3"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <p className="text-sm text-muted-foreground">
                WAV or MP3, up to 100 MB. MP3 needs ffmpeg on the API host.
              </p>
            </div>

            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Aphex Twin – Xtal" {...field} />
                  </FormControl>
                  <FormDescription>
                    e.g. Artist – Track Name (used as the catalog display label).
                  </FormDescription>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="artist"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Artist</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Aphex Twin (optional)" {...field} />
                  </FormControl>
                  <FormDescription>Optional — stored in the manifest.</FormDescription>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="sensitivity"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Match sensitivity</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-60">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="strict">Strict</SelectItem>
                      <SelectItem value="balanced">Balanced</SelectItem>
                      <SelectItem value="loose">Loose</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Balanced fits most catalogs; Strict flags only near-identical
                    masters; Loose catches weaker matches.
                  </FormDescription>
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="submit" disabled={submitting}>
                {submitting ? (
                  "Fingerprinting..."
                ) : (
                  <>
                    <Upload className="h-3.5 w-3.5" />
                    Ingest &amp; fingerprint
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
