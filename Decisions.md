# Design decisions

This revision organizes and completes the existing draft. It leaves
[Motivation.md](./Motivation.md) unchanged and preserves the standard service
identifiers, cryptographic byte layouts, and existing deterministic vectors.

| Decision | Reason and effect |
|---|---|
| Use modules with specifications, inputs, outputs, pseudocode and diagrams | Explicit boundaries support independent implementation and monolith, component or process composition. |
| Define a minimum useful node profile | Identity, Cryptography, Transport, Peer Control, Ledger, Board, Services and Storage provide paid retention/recovery; Node API and other families are optional. |
| Require Services alongside Storage | Schema, invocation, check and settlement coordination are necessary to use the required resource service. |
| Separate local persistence from the paid Storage service | Ledger, keys and other family stores can start and recover without buying leases or creating circular dependencies. |
| Distinguish shared codecs from optional runtimes | File catalogs use Discovery's share-record format without needing an indexer; configured contacts suffice for core bootstrap. |
| Define recoverable local coordination across stores | Split processes preserve service/accounting invariants through prepared effects, durable decisions and idempotent status/commit ports. No generic peer replay or atomic fair exchange is added. |
| Rename Network to Transport and Encryption to Cryptography | The former handles streams; the latter also signs and hashes. |
| Rename Open Social Messaging to Public Feeds and Page to Static Pages | Clearer documentation names; wire identifiers stay unchanged. |
| Add Peer Protocol | Defines previously missing metadata, invocation, streaming, quote, check, and ledger-control messages. |
| Keep the seven service families separate | Their ownership, addressing, persistence, and verification rules differ. |
| Keep issuer-specific credits and local trust | Preserves mutual contribution without a global currency or reputation authority. |
| Specify spending versus issuing credits | Wanted work can pay with requester-issued credits without a fictitious self-balance. |
| Keep one 121-byte transfer layout | Resolves contradictory transfer layouts and removes invented expiry/nonce fields from pseudocode. |
| Permit metering only for Computation | Reconciles its bounded final charge with the common pre-agreed-price rule. |
| Distinguish rejection from uncertain completion | Lost responses cannot safely imply rollback of a durable remote operation. |
| Define local authentication, versioning, and blob handles | Removes Node API placeholders without coupling clients to filesystem paths or one language. |
| Treat metadata exchanges as bounded control traffic | Makes bootstrap possible while keeping resource services priced. |
| Correct Discovery and Messaging pseudocode | Aligns record hashes, cursors, included checks, renewal, receipts, and release credits with the service specifications. |

This is a draft revision, not a claim of compatibility with an already deployed
version 1 implementation. The new peer binding and completed local API need
independent interoperability testing before a stable release is declared.

## Deliberate boundaries

- There is no global consensus, automatic arbitration, or atomic fair exchange
  across two or three peers. Third-party settlement can remain unsettled.
- There is no transparent identity recovery or rotation. Backups are necessary.
- There is no automatic lease replication, free broadcast, or guaranteed discovery.
- There is no generic NAT traversal or relay service in version 1. An already
  usable TCP route is required.
- Computation selects an explicit language/version and its evaluation semantics.
  This does not select the language used to implement a node or client. A
  different result convention, such as captured stdout, needs a custom contract.
- Public content stays public. Paid access limits participation and resource use;
  it cannot stop an authorized reader from copying the bytes elsewhere.
- Key portability alone is insufficient for data recovery. Lease references and
  encryption metadata must survive too.

These boundaries are stated so a PoC can test the intended features without
depending on mechanisms the protocol has not defined.
