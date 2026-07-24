export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Audio stream properties (populated for audio/* uploads via mutagen)
  duration_seconds: number | null;
  sample_rate: number | null;
  channels: number | null;
  bitrate: number | null;
  codec: string | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Audio-dedup domain types ---

export type Sensitivity = "strict" | "balanced" | "loose";
export type CanonicalStatus = "canonical" | "duplicate";
export type FingerprintStatus = "fingerprinted" | "pending";

export interface Track {
  key: string;
  filename: string;
  title: string | null;
  artist: string | null;
  size_bytes: number;
  size_human: string;
  duration_seconds: number | null;
  uploaded_at: string;
  fingerprint_status: FingerprintStatus;
  fingerprint_count: number;
  canonical_status: CanonicalStatus;
  audio_url: string | null;
}

export interface TrackDetail extends Track {
  track_id: number | null;
  sample_rate: number | null;
  channels: number | null;
  bitrate: number | null;
  codec: string | null;
  notes: string | null;
  duplicate_of: string | null;
  sensitivity: Sensitivity;
  md5: string | null;
}

export interface TrackUpdate {
  title?: string | null;
  artist?: string | null;
  notes?: string | null;
  canonical_status?: CanonicalStatus | null;
  duplicate_of?: string | null;
}

export interface IngestResponse {
  key: string;
  track_id: number | null;
  fingerprint_count: number;
  duration_seconds: number | null;
  is_duplicate: boolean;
  matched_key: string | null;
  matched_title: string | null;
  confidence: number | null;
  message: string;
}

export interface CatalogStats {
  tracks_in_catalog: number;
  fingerprints_indexed: number;
  duplicates_detected: number;
  duplicate_pct: number;
  total_audio_bytes: number;
  total_audio_human: string;
}

export interface DailyIngestCount {
  date: string;
  ingests: number;
}

export interface DedupMatch {
  track_id: number | null;
  track_name: string;
  key: string | null;
  title: string | null;
  confidence: number;
  offset_seconds: number;
  hashes_matched: number;
}

export interface DedupResult {
  candidate_name: string;
  candidate_key: string | null;
  is_duplicate: boolean;
  sensitivity: string;
  threshold: number;
  top_match: DedupMatch | null;
  matches: DedupMatch[];
  matched_key: string | null;
  matched_title: string | null;
  matched_audio_url: string | null;
  created_at: string;
  result_key: string | null;
}
