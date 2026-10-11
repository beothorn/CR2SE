# Independent module contracts

This document defines the local boundaries for all [modules](./README.md#modules).
Together with each module's `inputs/README.md` and `outputs/README.md`, these
are normative contracts for independently implementing and composing modules.
The module specification remains authoritative for its algorithms, service
semantics, canonical bytes, prices, and peer-visible behavior. These boundaries
add no peer messages and do not change version 1 wire encodings.

## Required and optional capabilities

**Required** means part of the minimum useful CR2SE node profile. It does not
mean a separately deployed executable, nor a dependency of every other module.
**Optional** means a node can omit that capability and still implement the
minimum profile. Once a capability is advertised, all requirements of that
service/version apply; optional does not mean partially implementing a contract.

| Module | Minimum profile | Why / scope |
|---|---|---|
| [Cryptography](./modules/cryptography/README.md) | Required | Hashing, signatures, key agreement, integrity and encryption formats. |
| [Identity](./modules/identity/README.md) | Required | Stable identity, protected credentials and key authority. |
| [Transport](./modules/transport/README.md) | Required | Authenticated bidirectional TCP streams. |
| [Peer Control / Peer Protocol](./modules/peer-protocol/README.md) | Required | Shared metadata, quote, invocation, check and ledger-control binding. |
| [Ledger](./modules/ledger/README.md) | Required | Trust, bounded credit authority, reservations and durable settlement. |
| [Board](./modules/board/README.md) | Required | Publish and retrieve consistent offerings and definitions. |
| [Services](./modules/services/README.md) | Required | Typed contracts, handler dispatch, authorization and invocation lifecycle used by Storage. |
| [Storage](./modules/storage/README.md) | Required | One useful resource service: immutable paid retention and recovery. |
| [Node API](./modules/node-api/README.md) | Optional | Standard application-facing embedded/loopback interface. Other authorized local control is sufficient. |
| [Computation](./modules/computation/README.md) | Optional | Bounded remote evaluation. |
| [Messaging](./modules/messaging/README.md) | Optional | Signed message placements and recipient recovery. |
| [Discovery](./modules/discovery/README.md) | Optional | Paid indexing and lookup; configured contacts can bootstrap the core. |
| [Public File Sharing](./modules/file-sharing/README.md) | Optional | Public manifests, catalogs and piece retrieval. |
| [Public Feeds](./modules/public-feeds/README.md) | Optional | Signed publication and paid feed reads. |
| [Static Pages](./modules/pages/README.md) | Optional | Paid static resource retrieval. |

The minimum node implements requester and provider behavior for Storage version
1, including store, retrieve, renew, remove and the paid byte check. It can
configure a provided offering, initiate a request to a configured peer, and
preserve accepted leases across restart. Temporary refusal for capacity or
policy is allowed; a permanently unusable placeholder does not satisfy this
profile. Empty Boards are valid documents, but two permanently empty Boards
alone do not demonstrate a useful deployment.

Bootstrap needs a reachable contact, explicit nonzero trust for providing work,
and finite credits or issuance authority. These can be configured locally;
neither Discovery nor Node API is needed. The core must demonstrate an accepted
paid store followed by verified retrieval after restart. Encrypted recovery and
independent replicas build on the same modules. The full-feature PoC adds every
optional family; it is a different claim from minimum-profile conformance.

A requester-only application, codec library, or isolated module may implement
a subset. Describe it as that subset rather than as the complete minimum node.
Third-party credit acceptance, particular runtimes and implementation hints
remain policy/capability choices as specified by their owning modules.

## Independence and deployment

Independent implementation means that a module can be built and verified using
only its specification, the contracts it consumes, and substitutes for those
dependencies. It must not require another module's source, database schema,
private objects, locks, or execution environment. Independence does not mean
that every module offers a useful network service in isolation.

The same logical contracts support:

- A monolith using direct calls and one database with explicit ownership.
- Separate libraries, packages or components connected through adapters.
- Separate processes with authenticated IPC/RPC and independent durable stores.

Names such as `reserve`, `prepare` and `invoke` below describe logical operations,
not mandatory method names, classes, transport endpoints, or programming
languages. An adapter may map them to calls, messages or events while preserving
the types, ordering, authority and failure semantics. Internal protocol selection
is an implementation choice; it must not silently change the public peer wire
protocol or Node API when that API is provided.

Shared **formats** are dependencies on definitions, not on running services.
For example, File Sharing requires the Discovery share-record codec for its
catalog, but does not require an indexer, Discovery process or paid lookup.
Cryptography may use the ID derivation formula without invoking Identity.
Board may validate the Services schema vocabulary without invoking its runtime.

## Ownership and composition

Each state item has one authoritative owner. Other modules obtain immutable
snapshots or issue authorized commands. A shared database is permitted, but its
tables are not the inter-module contract.

| Owner | State | Consumers through contracts |
|---|---|---|
| Identity | Persistent key handles, public credentials, configured contacts | Transport, Ledger, service clients and signing providers |
| Cryptography | Temporary secrets and optional protected primitive key handles | Identity, Transport, Ledger and family codecs |
| Transport | Sockets, authenticated sessions, stream state, counters and session keys | Peer Control and local connection control |
| Peer Control | Record parsing, exchange/quote state, detached body transfer | Board, Services, Ledger and local callers |
| Board | Atomic offering/definition snapshots and attributed remote caches | Peer Control, Services and local callers |
| Services | Handler registry, accepted invocation context and coordination journal | Peer Control, local callers and family handlers |
| Ledger | Trust, balances, reservations, issuance limits, claims and transfer replay | Services, Peer Control and authorized administration |
| Each service family | Its resources, accepted obligations, results and service replay guards | Services and authorized local publication/check clients |
| Node API, if enabled | Client sessions, tokens, blob handles and request correlation | Authorized local applications |
| Requester application | Spending policy, verified results, check expectations and recovery catalog | Service clients; no implicit provider-side recovery catalog |

Local persistent storage, clock, random source, socket I/O, protected key store,
execution runtime and local administrator authority are **platform ports**.
An implementation supplies them independently or through adapters. In particular,
the paid Storage module is not the database used by Ledger, Board, Identity or
Messaging. Their persistence must be available without invoking paid Storage.
Sharing a storage engine does not merge ownership or service obligations.

Composition supplies the module registry and routes calls. It is application
wiring, not a new required protocol module. At startup it resolves each declared
capability and compatible local contract version, then exposes only usable
offerings. There is no new peer capability-negotiation message: peers use
Transport protocol/version selection, Boards and definitions.

An omitted optional module has no provided offering and receives no dispatch.
A wanted offering may request work from a remote provider without installing a
local provider, but its publisher still needs a compatible requester codec,
validator and authorized source of input. Unsupported requests fail before
acceptance with the existing `unsupported` or missing-offering failure; they
must not be silently routed to a different service. Do not make already accepted
obligations optional: disabling a handler stops new work and must retain the
ability to honor leases, results and replay records until their required end.

## Common input types and expectations

These logical types apply to every boundary. A local binding documents its
representation and negotiates/rejects incompatible contract versions before
dispatch. The contracts in this revision are local contract version **1**;
this is separate from service and wire versions.

| Value | Required meaning |
|---|---|
| Identity / hash | Exact 32 bytes; textual IDs are parsed only at an explicit text boundary. |
| Integer / time | Exact declared width; uint64 never passes through a lossy number type. Unix times are whole seconds unless explicitly milliseconds. Use checked arithmetic. |
| Bytes / text | Length-bounded immutable value or scoped stream handle with declared byte length. Text is valid UTF-8; no implicit normalization. |
| Call context | Local correlation ID, authenticated local caller authority, deadline/cancellation, resource limits and relevant local contract version. It is not peer-controlled metadata. |
| Peer context | Local identity, authenticated peer ID, connection instance and stream instance supplied by Transport through Peer Control. A payload field cannot override them. |
| Invocation context | Durable local operation key, requester/provider/publisher IDs, service/version, mode, selected definition, immutable accepted offering and quote bytes/hash, issuer, price/bound, and reservation reference. |
| Result reference | Owner-issued immutable bytes/metadata or authorized read handle, with length and lifetime. A raw file path or process pointer is not a portable reference. |

The local operation key identifies one accepted attempt; include the caller
identity and connection/stream instance in its association. A reconnect creates
a new attempt unless the service explicitly supplies a replay key. Local IPC
retries reuse the original key and exact parameters; they must not turn into a
second peer invocation. Persist its binding to terms and result before relying
on it for recovery. Conflicting reuse fails with `conflict`.

Callers validate what they send; receivers independently check shape, bounds,
authority and state before effects. Authentication context across processes must
come over an authenticated, authorized channel. Arbitrary peers cannot invoke
local administrative, signing, reservation or commit ports. Keep secret-bearing
IPC confidential, and do not expose raw persistent keys in general results.

Streams must preserve bytes, per-stream order, explicit end/error, bounded
buffering and backpressure. A receiver checks exact declared length; it must
not publish provisional bytes as a complete result. Ownership and lifetime of
handles must survive all authorized consumers; accepted durable results cannot
depend solely on an expiring Node API session blob. Cancellation requests end
future work when possible, not already committed obligations.

## Common outputs and failures

Every call resolves to a typed success or structured failure. Async bindings
correlate responses and distinguish progress from terminal output. Report local
dependency loss separately from a peer's explicit rejection. Map peer-facing
errors to the existing [Peer Protocol codes](./modules/peer-protocol/README.md#input-result-and-failure).

Before acceptance, malformed input, unsupported capability, denied authority,
stale terms, insufficient credits and capacity refusal have no service charge.
After acceptance, distinguish an explicit uncommitted service failure from
`outcome_unknown`: a deadline, IPC disconnect, cancellation or lost response
does not establish rollback. A completed service result and its payment state
are separate; third-party settlement may remain unsettled. Neither connection
completion nor delivery of an internal event proves remote receipt.

Diagnostic text is bounded and contains no secrets. Missing-resource and
authorization errors must not disclose protected resource existence. Checks
return `pass`, `fail`, or `inconclusive` to the requester; a provider emits only
the defined evidence. A negative business result can be a charged success
(for example an empty Discovery page or Computation `executionError`).

## Common service-handler boundary

Each family implements the following logical ports for Services. The exact
operation inputs and results are defined in that family's inputs and outputs.

| Input from Services | Output from handler | Expectation |
|---|---|---|
| `describe(service, version)` | Definition/schema and supported modes | Exact contract; no remote code loading. |
| `assess(peer context, selection, input metadata, limits)` | Validated metadata, price factors/provider sizes, capacity decision | No work or settlement; bounded preparation may pin a snapshot. Release pins on rejection/timeout. |
| `execute(invocation context, complete input)` | Validated result, final price, result reference and proposed state effects, or explicit failure/unknown outcome | Only after accepted terms and reservation. Full content validation precedes durable acceptance. |
| `prepare/commit/abort/status(operation key, effect reference)` | Durable participant status | Recoverable protocol below; these are local lifecycle calls, not peer operations. |
| `evidence(context, check input)` | Defined remote evidence | Only for remotely callable checks, under included entitlement or accepted check price. |
| `verify(original input, terms, complete result/evidence, local expectations)` | Local check outcome | No unsolicited spending, refunds or changes to trust. |

Requester codecs and verifiers may be implemented separately from provider
handlers. Services provides the invocation path; handlers do not open sockets,
read Board internals or directly adjust Ledger balances. They supply price and
effect data to Services, which obtains Ledger authorization. When pseudocode
shows such a helper directly, it denotes this contract call through composition.

## Durable effects across process boundaries

For a monolith, one local transaction may cover a service effect and its Ledger
effect. Independent stores need equivalent recoverable coordination. The
following logical protocol is sufficient; another implementation must preserve
the same invariants. This is local node coordination, not atomic exchange
between independent peers.

1. Services durably binds an operation key to exact accepted terms, handler,
   reservation, input identity and result/effect references. Ledger reserves
   finite capacity before execution. Neither an IPC timeout nor a retry creates
   a fresh reservation for that key.
2. The handler stages durable state and result bytes under that key; Ledger
   prepares the exact charge and any separately authorized adjustment. Each
   `prepare(key, effect)` returns a durable opaque token bound to its owner,
   key and exact effect. Repeating it returns the same status; conflicting
   data is rejected. Holds, exclusivity and service replay guards survive
   restart. Staged state is not reported as a successful obligation.
3. After every required participant is prepared, the coordinator durably records
   one immutable decision: commit or abort. Commit is allowed only with valid
   complete input/result, finite reservation and all required preparations.
   The decision and referenced data must survive ordinary restart.
4. Deliver that decision using `commit(key, token)` or `abort(key, token)`.
   Participants apply it at most once and retain enough status to answer
   `status(key) -> absent | prepared | committed | aborted` after response loss.
   A participant cannot abort after a commit decision, or decide to abort just
   because a deadline elapsed. An absent coordinator decision is resolved by
   recovering that coordinator, not by guessing at a participant.
5. The coordinator retries delivery of its recorded decision, never execution.
   Report success only after all required local effects and result retention
   are durable. Gate conflicting reads/writes while effects are incomplete so
   another request cannot spend reserved funds or observe a lease as available
   while its settlement may still abort. Recovery can block work on affected
   resources until a participant returns; safety takes priority over availability.
6. Abort releases prepared resources/reservations without a charge when no
   successful commitment exists. A lost acknowledgement after commit remains
   pending/unknown to the caller until status is recovered. Retain decision and
   deduplication records until participants have finalized and all service retry
   and accounting obligations permit compaction; lifetime replay guards remain
   for claims, transfers and Messaging removal as their contracts require.

External execution effects (such as Computation code affecting another system)
cannot be rolled back by this protocol. Persist the execution attempt before
starting it; never restart it because an internal response was lost. Use a
durably recoverable completion if available, otherwise report uncertainty.
Likewise, a local commit is not evidence that the remote peer received output.
Peer Control applies its existing result/end and outcome-unknown rules.

## Independent verification and integration

Every module has an `acceptanceTests/README.md` suite with expected results. A
module can run it with contract-compatible fakes for dependencies and platform ports. Test
invalid input as well as normal input, exact values at boundaries, authority,
dependency timeout, and restart where state is durable. Existing canonical
vectors remain unchanged and authoritative for byte interoperability.

To verify a composition, run the same meaningful cases through direct-call and
serialized adapters. Verify authentication context cannot be forged, bytes and
uint64 values survive serialization, slow consumers remain bounded, and a
lost local reply cannot duplicate a durable effect. Exercise crashes between
each journal step and verify recovery before serving affected resources.
These are acceptance obligations for implementations, not a claim that this
documentation repository contains executable modules or proves conformance.
