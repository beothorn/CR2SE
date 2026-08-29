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
