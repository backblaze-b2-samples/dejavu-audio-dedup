"use client";

import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import { useUpdateTrack } from "@/lib/queries";
import type { CanonicalStatus, TrackDetail } from "@dejavu-audio-dedup/shared";

interface EditValues {
  title: string;
  artist: string;
  notes: string;
  canonical_status: CanonicalStatus;
  duplicate_of: string;
}

export function EditTrackForm({ track }: { track: TrackDetail }) {
  const update = useUpdateTrack();
  const form = useForm<EditValues>({
    // Pre-filled from the real track — an edit form, so no default hints.
    defaultValues: {
      title: track.title ?? "",
      artist: track.artist ?? "",
      notes: track.notes ?? "",
      canonical_status: track.canonical_status,
      duplicate_of: track.duplicate_of ?? "",
    },
  });

  const status = useWatch({ control: form.control, name: "canonical_status" });

  const onSubmit = (values: EditValues) => {
    update.mutate(
      {
        key: track.key,
        update: {
          title: values.title,
          artist: values.artist,
          notes: values.notes,
          canonical_status: values.canonical_status,
          duplicate_of:
            values.canonical_status === "duplicate" ? values.duplicate_of || null : null,
        },
      },
      {
        onSuccess: () => toast.success("Track metadata updated"),
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Update failed"),
      }
    );
  };

  return (
    <Card>
      <CardHeader className="border-b border-border px-5 py-4">
        <CardTitle className="card-title">Edit metadata</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
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
                    <Input {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes</FormLabel>
                  <FormControl>
                    <Textarea className="resize-none" {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="canonical_status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Canonical status</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-60">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="canonical">Canonical</SelectItem>
                      <SelectItem value="duplicate">Duplicate of…</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Mark a track as the canonical master or a duplicate of another.
                  </FormDescription>
                </FormItem>
              )}
            />
            {status === "duplicate" && (
              <FormField
                control={form.control}
                name="duplicate_of"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Duplicate of (catalog key)</FormLabel>
                    <FormControl>
                      <Input placeholder="catalog/original.wav" {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />
            )}
            <div className="flex justify-end">
              <Button type="submit" disabled={update.isPending}>
                {update.isPending ? "Saving..." : "Save changes"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
