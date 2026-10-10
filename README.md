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
3. Read the [independent module contracts and minimum profile](./ModuleContracts.md).
4. Follow the [PoC implementation guide](./PoC.md) in a separate project.
5. Read each module's specification, inputs, outputs, pseudocode and diagrams.
6. Review [design decisions](./Decisions.md) for clarified rules and limits.

This repository specifies a **draft version 1** protocol. It is not a working
implementation or a claim of production security. Requirements are concrete
enough to implement and test; the PoC must still validate them in practice.

## Modules

Each module has a `README.md` specification, `inputs/` and `outputs/` contracts,
`pseudocode/`, and `diagrams/`. A module is independently implementable against
its contracts and declared dependencies. Implementations may compose modules
as a monolith, separate logical components, or separate processes. No particular
package, class, database or programming language is prescribed.

| Module | Minimum profile | Responsibility |
|---|---|---|
| [Identity](./modules/identity/README.md) | Required | Stable IDs, key ownership, contacts and recovery boundaries. |
| [Cryptography](./modules/cryptography/README.md) | Required | Signing, key binding, hashing and encryption formats. |
| [Transport](./modules/transport/README.md) | Required | Authenticated TCP, protected frames and multiplexed streams. |
| [Peer Control / Peer Protocol](./modules/peer-protocol/README.md) | Required | Shared control messages, quotes, values and streaming. |
| [Ledger](./modules/ledger/README.md) | Required | Credits, reservations, settlement, transfers, claims and trust. |
| [Board](./modules/board/README.md) | Required | Consistent compact offerings and separately retrieved definitions. |
| [Services](./modules/services/README.md) | Required | Typed contracts, invocation lifecycle and verification for all families. |
| [Storage](./modules/storage/README.md) | Required | Immutable leases, ranges, renewal, removal and paid checks. |
| [Node API](./modules/node-api/README.md) | Optional | Standard embedded/local IPC interface for applications. |
| [Computation](./modules/computation/README.md) | Optional | Bounded runtime evaluation and metered completion. |
| [Messaging](./modules/messaging/README.md) | Optional | Signed placements, recovery, receipts and release credits. |
| [Discovery](./modules/discovery/README.md) | Optional | Paid indexing and lookup of signed records. |
| [Public File Sharing](./modules/file-sharing/README.md) | Optional | Canonical manifests, catalogs and verified piece retrieval. |
| [Public Feeds](./modules/public-feeds/README.md) | Optional | Signed public messages and local feed aggregation. |
| [Static Pages](./modules/pages/README.md) | Optional | Paid retrieval of static HTML and assets. |

The minimum profile can store and recover paid immutable data with configured
contacts and finite trust/credit policy. Services is required because Storage
needs its contract and invocation rules. Optional capabilities are omitted from
provided offerings when unavailable; once advertised, their full versioned
contracts apply. [Module contracts](./ModuleContracts.md) define deployment,
state ownership, dependency handling, failure and recovery expectations.

[Redundancy](./Redundancy.md) defines the cross-module rule that one provider is
one copy and applications must verify independent replica agreements.

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

Module specifications and input/output contracts define required behavior for
implemented capabilities. **Must** is required, **must
not** is forbidden, **should** is a recommendation, and **may** is optional.
Pseudocode and diagrams explain those rules; they do not add new wire formats.
Service-specific rules define the operation; Peer Protocol defines its encoding;
Transport defines frames. Local implementation policy may refuse new work, but
must not silently alter accepted terms or canonical formats.
