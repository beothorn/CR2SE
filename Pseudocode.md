# CR2SE pseudocode guide

The module pseudocode translates CR2SE's normative wire and service contracts into
implementation-neutral algorithms. It defines required state transitions,
validation, I/O behavior, and observable outcomes without prescribing classes,
threads, async runtimes, or language-specific APIs.

The specification documents remain authoritative. Pseudocode must not add a
wire behavior that the corresponding specification does not define.

## Modules

- [Transport](./modules/transport/pseudocode/README.md) — TCP framing, connection authentication and
  integrity, stream multiplexing, lifecycle, errors, and shutdown.
- [Transport version 1 test vectors](./modules/transport/pseudocode/TestVectors.md) — deterministic
  identity, handshake, key-derivation, and integrity-tag interoperability data.
- [Identity](./modules/identity/pseudocode/README.md) — identity generation, ID derivation, public-key
  validation, textual and QR forms, proof helpers, and private-key lifecycle.
- [Cryptography](./modules/cryptography/pseudocode/README.md) — persistent encryption-key binding, exact
  identity-encryption KDF and envelope, authenticated encryption, large-data
  units, and content-encryption boundaries.
- [Board](./modules/board/pseudocode/README.md) — bounded JSON decoding, version and offering validation,
  pricing and precondition capability checks, publication state, caching,
  service-definition consistency, and stale-selection handling.
- [Computation](./modules/computation/pseudocode/README.md) — runtime and offering validation,
  maximum-price authorization, metered execution, completion settlement,
  independent checks, and security boundaries.
- [Storage](./modules/storage/pseudocode/README.md) — exact rational pricing, durable immutable leases,
  authorized range retrieval, renewal, removal, byte challenges, and expiry.
- [Node API](./modules/node-api/pseudocode/README.md) — local IPC framing, request dispatch, connection
  control, remote metadata retrieval, and service invocation.
- [Ledger](./modules/ledger/pseudocode/README.md) — atomic owned/issued balances, transfers, claims,
  reservations, persistence, and local trust policy.
- [Services](./modules/services/pseudocode/README.md) — definition and schema validation, invocation
  agreement, settlement, checks, and extension boundaries.
- [Public File Sharing](./modules/file-sharing/pseudocode/README.md) — canonical manifests, share
  identifiers, paid piece retrieval, catalogs, and content verification.
- [Messaging](./modules/messaging/pseudocode/README.md) — signed placement, discovery, recipient
  recovery, status, renewal, removal, and optional payload encryption.
- [Public Feeds](./modules/public-feeds/pseudocode/README.md) — signed public feeds,
  cursors, publication, verification, and deterministic feed merging.
- [Static Pages](./modules/pages/pseudocode/README.md) — canonical static-resource lookup, fixed-price retrieval,
  snapshot consistency, and local verification.
- [Discovery](./modules/discovery/pseudocode/README.md) — signed records, indexing, resolution, lookup,
  pagination, iterative search, and verification.
- [Peer Protocol](./modules/peer-protocol/pseudocode/README.md) — bounded records,
  quote acceptance, typed value binding, streaming, and wanted-service roles.

`transaction` means an atomic durable local change, not a distributed database
transaction. `reserveCharge` and similar helpers delegate to Ledger's settlement
mode: spending provider credits, issuing requester credits, or arranging an
issuer-mediated transfer. An included check or recognized retransmission uses
its existing entitlement. `returnAndCommitExactly` is shorthand for validated
result production and a recoverable local settlement journal; it cannot make a
socket write atomic with a database commit.

Service-specific pseudocode describes logical values after wire decoding.
Peer Protocol handles quote agreement, body framing, completion markers, and
interruption before or after durable commitment. A helper returning a value is
not proof that the remote application received it. Apply the unknown-outcome
rules and only the replay guarantees explicitly defined by the service.
