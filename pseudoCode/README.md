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
