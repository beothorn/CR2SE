# CR2SE pseudocode

This folder translates CR2SE's normative wire and service contracts into
implementation-neutral algorithms. It defines required state transitions,
validation, I/O behavior, and observable outcomes without prescribing classes,
threads, async runtimes, or language-specific APIs.

The specification documents remain authoritative. Pseudocode must not add a
wire behavior that the corresponding specification does not define.

## Components

- [Network](./Network.md) — TCP framing, connection authentication and
  integrity, stream multiplexing, lifecycle, errors, and shutdown.
- [Network version 1 test vectors](./NetworkTestVectors.md) — deterministic
  identity, handshake, key-derivation, and integrity-tag interoperability data.
- [Identity](./Identity.md) — identity generation, ID derivation, public-key
  validation, textual and QR forms, proof helpers, and private-key lifecycle.
- [Encryption](./Encryption.md) — persistent encryption-key binding, exact
  identity-encryption KDF and envelope, authenticated encryption, large-data
  units, and content-encryption boundaries.
- [Board](./Board.md) — bounded JSON decoding, version and offering validation,
  pricing and precondition capability checks, publication state, caching,
  service-definition consistency, and stale-selection handling.
- [Computation](./Computation.md) — runtime and offering validation,
  maximum-price authorization, metered execution, completion settlement,
  independent checks, and security boundaries.
- [Storage](./Storage.md) — exact rational pricing, durable immutable leases,
  authorized range retrieval, renewal, removal, byte challenges, and expiry.
- [Node API](./NodeApi.md) — local IPC framing, request dispatch, connection
  control, remote metadata retrieval, and service invocation.
- [Ledger](./Ledger.md) — atomic owned/issued balances, transfers, claims,
  reservations, persistence, and local trust policy.
- [Services](./Services.md) — definition and schema validation, invocation
  agreement, settlement, checks, and extension boundaries.
- [Public File Sharing](./PublicFileSharing.md) — canonical manifests, share
  identifiers, paid piece retrieval, catalogs, and content verification.
- [Messaging](./Messaging.md) — signed placement, discovery, recipient
  recovery, status, renewal, removal, and optional payload encryption.
- [Open Social Messaging](./OpenSocialMessaging.md) — signed public feeds,
  cursors, publication, verification, and deterministic feed merging.
- [Page](./Page.md) — canonical static-resource lookup, fixed-price retrieval,
  snapshot consistency, and local verification.
- [Discovery](./Discovery.md) — signed records, indexing, resolution, lookup,
  pagination, iterative search, and verification.
