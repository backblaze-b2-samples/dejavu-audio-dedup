from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Backblaze B2 (S3-compatible). B2_REGION is the required, documented knob;
    # the S3 endpoint is derived from it (see `s3_endpoint`). No region literal
    # is hardcoded in source — it comes from the environment.
    b2_region: str = ""
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url_base: str = ""

    # MySQL fingerprint database (Dejavu's canonical backend). Separate,
    # non-B2 namespace — these are infra credentials, not object-storage keys.
    fp_db_host: str = "127.0.0.1"
    fp_db_port: int = 3306
    fp_db_user: str = "dejavu"
    fp_db_password: str = "dejavu"
    fp_db_name: str = "dejavu"

    # Match sensitivity → minimum Dejavu fingerprinted-confidence to call a
    # candidate a duplicate. Strict = fewer false duplicates (needs a strong
    # match); Loose = flags weaker matches too.
    dedup_threshold_strict: float = 0.20
    dedup_threshold_balanced: float = 0.05
    dedup_threshold_loose: float = 0.01

    api_port: int = 8000
    # Interactive API docs (/docs, /redoc, /openapi.json). On by default for
    # local dev and starter-kit exploration; set false to hide the full API
    # surface in production.
    enable_docs: bool = True
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Optional confinement for key-addressed reads/deletes. Empty by default so
    # the by-key routes accept any key shape (they deliberately support nested
    # folders and reserved-word segments). Point a fork at a bucket shared with
    # other data? Set to e.g. "uploads/" to restrict all key ops to app uploads.
    allowed_key_prefix: str = ""

    # Rate limiting (per client IP, per 60s window). In-process per replica —
    # documented in docs/RELIABILITY.md; horizontal scaling needs a shared
    # store (e.g. Redis). Writes/downloads get the tighter cap.
    rate_limit_per_minute: int = 120
    # Covers uploads, deletes, downloads and previews — kept generous enough
    # that a normal browsing/upload session doesn't trip it.
    rate_limit_write_per_minute: int = 60

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def s3_endpoint(self) -> str:
        """S3 endpoint for B2, derived from B2_REGION
        (`https://s3.<region>.backblazeb2.com`). No region string is baked into
        source — an unset region yields an obviously-invalid host that startup
        validation rejects before any B2 call is attempted."""
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def fp_db_config(self) -> dict:
        """Connection dict shared by the Dejavu engine and the repo-layer
        fingerprint-DB queries (counts, dump, deletes)."""
        return {
            "host": self.fp_db_host,
            "port": self.fp_db_port,
            "user": self.fp_db_user,
            "password": self.fp_db_password,
            "database": self.fp_db_name,
        }

    def threshold_for(self, sensitivity: str) -> float:
        """Map a match-sensitivity label to its confidence threshold."""
        return {
            "strict": self.dedup_threshold_strict,
            "balanced": self.dedup_threshold_balanced,
            "loose": self.dedup_threshold_loose,
        }.get(sensitivity, self.dedup_threshold_balanced)

    @property
    def cors_origins(self) -> list[str]:
        # Drop empties so a trailing comma or API_CORS_ORIGINS="" doesn't yield
        # a stray "" origin.
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


settings = Settings()
