# Product

## Register

product

## Users

Data and metadata engineers at music streaming platforms and podcast networks who
build ingest pipelines for large raw audio libraries. Their context: before adding a
recording to the catalog they need to know whether it already exists — an exact or
near-duplicate master, a re-upload, a re-encode. They want a working reference for the
pattern "fingerprint locally, store everything durably on B2, dedup before ingest."

## Product Purpose

A full-stack reference app for audio-catalog deduplication at scale. It uses Dejavu
(open-source acoustic fingerprinting) as a fully local matching engine and Backblaze B2
as the durable storage layer for the raw audio and every derived artifact (the portable
SQL fingerprint dump, the per-track manifest, and dedup result logs). MySQL is the live,
queryable index; B2 is the source of truth it can always be re-seeded from. Success = an
engineer can clone it, ingest a track, and see a re-upload flagged as a duplicate — with
every input and artifact visible in their own B2 bucket.

## Brand Personality

Confident, precise, quietly professional. Voice is direct and free of hype. The interface
should feel like a modern developer/data tool — considered, calm, trustworthy — not a
marketing showpiece. The audio-dedup domain is treated concretely: fingerprint status,
confidence, time-offset, and the two-index model are shown honestly rather than hidden
behind a magic "is this a duplicate?" button.

## Anti-references

- **Generic AI/SaaS slop.** No gradient text, hero-metric templates, identical icon-card
  grids, tracked uppercase eyebrows, or decorative glassmorphism.
- **Over-branded / loud.** No heavy brand-color drenching, decorative motion, or flashy
  effects.
- **Toy / prototype feel.** No missing states, inconsistent components, or placeholder
  polish. Must read as production-grade.
- **Enterprise-drab.** No Bootstrap-era gray boxes or dense-but-lifeless admin-panel look.
  Considered, like modern dev tools (Linear, GitHub Primer, Stripe).

## Design Principles

- **Practice what you preach.** The app models the production quality it demonstrates.
- **Show the mechanism honestly.** Fingerprint status, confidence, offset, and the
  MySQL-live-index vs B2-durable-copy distinction are surfaced, not hidden.
- **Earned familiarity over novelty.** Standard affordances (top bar + side nav, command
  palette, data tables, inline audio players). The tool disappears into the task.
- **Every state is designed.** Default, hover, focus, active, disabled, loading (skeleton),
  empty (teaches the interface), and error (says what's wrong + offers retry).
- **Consistency is the feature.** One button vocabulary, one form-control set, one icon
  style across every screen.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**. Body text ≥ 4.5:1, large/bold text ≥ 3:1, visible focus indicators
on every interactive element, full keyboard navigation, correct semantic landmarks and
heading order, labelled form controls, native `<audio>` controls for playback, and a
`prefers-reduced-motion` alternative for every animation. Full light and dark theme parity.
