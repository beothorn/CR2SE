# CR2SE

CR2SE is a peer-to-peer protocol for communities that exchange storage,
computation, messages, and information through mutual contribution. Each
identity issues its own credits. Useful work earns access to that identity's
resources; reaching more peers requires more relationships and resources.

[Motivation.md](./Motivation.md) is the project's guiding statement and remains
unchanged. The protocol supports people, organizations, software agents, and
networks of LLMs without treating any of them as a special identity type.

## Start here

1. Read the [motivation](./Motivation.md) and [architecture](./Architecture.md).
2. Use the [glossary](./Glossary.md) for shared terms.
3. Follow the [PoC implementation guide](./PoC.md) in a separate project.
4. Read the module specifications below, then their pseudocode and diagrams.
5. Review [design decisions](./Decisions.md) for clarified rules and limits.

This repository specifies a **draft version 1** protocol. It is not a working
implementation or a claim of production security. Requirements are concrete
enough to implement and test; the PoC must still validate them in practice.

## Modules

Each module has a `README.md` specification, a `pseudocode/` folder, and a
`diagrams/` folder. “Module” describes a protocol responsibility, not a required
process, package, class, or programming language.

| Module | Responsibility |
|---|---|
| [Identity](./modules/identity/README.md) | Stable IDs, key ownership, contacts, and recovery boundaries. |
| [Cryptography](./modules/cryptography/README.md) | Exact signing, key binding, and encryption formats. |
| [Transport](./modules/transport/README.md) | Authenticated TCP, protected frames, and multiplexed streams. |
| [Peer Protocol](./modules/peer-protocol/README.md) | Shared control messages, quotes, value encoding, and streaming. |
| [Ledger](./modules/ledger/README.md) | Issuer-specific credits, settlement, transfers, claims, and trust. |
| [Board](./modules/board/README.md) | Compact provided/wanted offerings and current terms. |
| [Services](./modules/services/README.md) | Contracts, schemas, invocation lifecycle, and verification. |
| [Node API](./modules/node-api/README.md) | Embedded control and authenticated local IPC for clients. |
| [Storage](./modules/storage/README.md) | Immutable leases, ranges, renewal, removal, and paid checks. |
| [Computation](./modules/computation/README.md) | Bounded runtime evaluation and metered completion. |
| [Messaging](./modules/messaging/README.md) | Signed placements, recipient recovery, receipts, and release credits. |
| [Discovery](./modules/discovery/README.md) | Paid indexing and lookup of signed addresses, shares, and trust. |
| [Public File Sharing](./modules/file-sharing/README.md) | Canonical manifests, catalogs, and verified piece retrieval. |
| [Public Feeds](./modules/public-feeds/README.md) | Signed public messages and client-side feed aggregation. |
| [Static Pages](./modules/pages/README.md) | Paid retrieval of static HTML and associated resources. |

The [pseudocode index](./Pseudocode.md) links algorithms and existing test vectors.
The architecture explains layers and dependencies; each module contains focused
sequence diagrams. Diagrams use fenced Mermaid blocks following
[GitHub's diagram format](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams).

## Rules that hold across modules

- Identity proves key control, not trust. Unknown peers start with zero trust.
- Each issuer's credits have separate balances and locally accepted value.
- Every new service operation has a positive price; bounded control exchanges,
  included checks, and original-result retransmissions are explicit exceptions.
- Agree an issuer and price before work. Computation agrees a formula and maximum.
- Preserve exact integers, canonical bytes, bounded resource use, and durable state.
- Replication and independent recovery metadata make data portable. One lease is
  not redundancy, and possession of a key alone does not locate stored data.
- Descriptions and returned content are untrusted input, including for agents.

Module specifications define required behavior. **Must** is required, **must
not** is forbidden, **should** is a recommendation, and **may** is optional.
Pseudocode and diagrams explain those rules; they do not add new wire formats.
Service-specific rules define the operation; Peer Protocol defines its encoding;
Transport defines frames. Local implementation policy may refuse new work, but
must not silently alter accepted terms or canonical formats.
