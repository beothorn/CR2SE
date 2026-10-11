# Acceptance test guide

These are implementation-agnostic acceptance specifications expressed as
pseudocode. Translate the actions to an implementation's public contract ports;
no method name, test framework, database layout, scheduler or process structure
is mandated. They complement the [module contracts](./ModuleContracts.md),
module specifications and existing canonical vectors. The specifications remain
authoritative; tests do not introduce wire fields or stronger replay guarantees.

This repository contains test instructions, not executable CR2SE tests. Passing
documentation checks does not demonstrate a working protocol implementation.

## Suite index and coverage

| Suite | Required coverage |
|---|---|
| [Identity](./modules/identity/acceptanceTests/README.md) | Keys, ID/text/contact formats, key authority and recovery. |
| [Cryptography](./modules/cryptography/acceptanceTests/README.md) | Canonical vectors, signatures, binding, envelopes, tampering and secret lifecycle. |
| [Transport](./modules/transport/acceptanceTests/README.md) | Handshake, exact frames, streams, integrity, partial I/O, shutdown and bounds. |
| [Peer Control](./modules/peer-protocol/acceptanceTests/README.md) | Records, values, metadata, quotes, bodies, wanted roles and ledger controls. |
| [Ledger](./modules/ledger/acceptanceTests/README.md) | All payment modes, reservations, trust, transfer/claim replay and crash recovery. |
| [Board](./modules/board/acceptanceTests/README.md) | Exact JSON, offerings, compatibility, snapshots and publication races. |
| [Services](./modules/services/acceptanceTests/README.md) | Schemas, dispatch, authority, pricing, checks and coordination fault matrix. |
| [Storage](./modules/storage/acceptanceTests/README.md) | All lease operations, exact prices, byte checks, expiration and durability. |
| [Node API](./modules/node-api/acceptanceTests/README.md) | Authentication, framing, every operation, blobs, budgets and session loss. |
| [Computation](./modules/computation/acceptanceTests/README.md) | Runtime selection, timing, all outcomes, metering, limits and independent checks. |
| [Messaging](./modules/messaging/acceptanceTests/README.md) | All placement operations, signed/encrypted payloads, receipts, replay and release credits. |
| [Discovery](./modules/discovery/acceptanceTests/README.md) | Every record/query type, canonicalization, indexing, ties, pagination and bounded lookup. |
| [Public File Sharing](./modules/file-sharing/acceptanceTests/README.md) | Manifest, catalog, pieces, resumption, extraction and independent hosting. |
| [Public Feeds](./modules/public-feeds/acceptanceTests/README.md) | Signed publication, attachments, selectors, ordering, bounds and aggregation. |
| [Static Pages](./modules/pages/acceptanceTests/README.md) | Publication, paths, media, bounded snapshots, checks and asset spending. |

Minimum-profile conformance uses the eight required suites and core integration
cases. Full-feature coverage includes every suite and integration case. An
optional module absent from a minimum deployment is recorded as not implemented,
not passed. If advertised, its complete supported contract must pass. Policy
choices (for example refusing third-party credits) have explicit refusal tests;
report supported and unsupported choices separately. Testing a codec subset
does not establish conformance of a complete provider or node.

## Pseudocode and harness conventions

Each module owns its `acceptanceTests/` suite; these tests can be implemented
independently against its published inputs and outputs. The root cross-module
cases complement the module suites. Each `TEST` starts with fresh fixtures. Every row of `FOR EACH` that mutates state
also starts fresh unless the code explicitly describes a sequence or race.
`ACT` calls the system under test; `ASSERT` compares an observable result to an
independent expected value. `REJECT` means a structured non-success under the
specified contract, not a required diagnostic string. Match exact error codes
only where the specification fixes them. `ABSENT` differs from null and empty.

| Harness capability | Meaning |
|---|---|
| `fixture(...)` | Test-owned valid inputs, keys, schemas, signed bytes and controlled dependency responses. It does not call the tested encoder to create its own expected result. |
| `oracle...` | Independent reference arithmetic/encoding/verification from the specification or pinned vectors, never a second call to the same production helper. |
| `observe(...)` | Contract result, emitted command, wire bytes, privileged local query or test-owned dependency trace. No required access to private tables. |
| `clock.set/advance` | Controlled wall/monotonic time at the relevant port. No real sleeps or accidental billing of network/queue time. |
| `deliver/split/drop` | Controlled wire or IPC delivery, including short reads/writes, truncation and lost acknowledgements. |
| `crash/restart` | Discard volatile state, retain only acknowledged durable writes, reconstruct the module with its persistent state and contract adapters. |
| `race` | Hold both operations at a specified shared-state boundary, then exercise both possible serialization orders. Assert permitted outcomes rather than a chosen winner. |
| `chargeDelta(op)` | Correlated successful local debit/issuance for that invocation; excludes reservations and unrelated calls. Provider-issued fixtures make it a simple debit. |
| `noEffects` | No successful service charge, new durable resource, execution, or unauthorized external action from this rejected attempt; bounded diagnostics/rate counters are allowed. |

`A`, `B`, `C`, `U` are distinct reproducible test identities (U is unauthorized).
Provider B trusts A at 1 and recognizes 1,000 B credits for A unless a test
overrides it; A's matching owned balance is 1,000. Issuance budgets are finite.
All default local policies allow the valid fixture operation and have sufficient
capacity. Otherwise a refusal could mask a broken positive path. Same-identity
cases use one coordinated identity writer, not two uncoordinated balance copies.
Local caller capabilities are explicitly granted by the fixture.

Default wall time is `t = 1000` Unix seconds. Monotonic time is independently
controlled. `bytes(n,x)` means n repetitions of byte x; `id(n)` is a 32-byte
big-endian test identifier for opaque IDs, **not** a fabricated authenticated
identity. `U64_MAX = 18446744073709551615`, `U32_MAX = 4294967295`.
Public cryptographic vector keys are test-only. Complete real-key integration
uses actual cryptography, not an always-valid signature stub.

Use complete valid offerings/definitions from each specification, replacing
placeholder identity text with actual IDs. Each suite states price/limit
overrides. Derived expected numeric prices are literal values or independent
exact rational arithmetic. Fault fixtures change one relevant property at a
time; unrelated fields remain valid. `malformed(field)` covers missing required
field, wrong type, null, wrong fixed length, out-of-range integer and forbidden
operation-specific fields where applicable. Unknown optional fields retain the
owning contract's forward-compatibility behavior.

Large-bound tests use synthetic length/stream ports rather than allocating
uint64-sized objects. Assert rejection before proportional allocation or work.
Use declared resource budgets, not a prescribed number of heap bytes. Resource
limits that are local policy must be explicitly configured in the fixture.
Do not require unsupported host-language/runtime facilities or a universal
sandbox policy where the protocol leaves them implementation-defined.

## Common contract cases

Every module suite incorporates AT-C01..C04 where the named ports apply;
nonapplicability must be recorded with its reason (for example a pure codec has
no durable commit). Family suites also incorporate Services' coordination cases.

```text
TEST AT-C01 boundary substitution and authority
  FOR EACH supported binding IN [direct, serialized adapter]:
    connect module only to declared ports; supply equivalent fixture values
    ACT valid operation
    ASSERT logical result, exact byte output and effects equal the fixture oracle
    ACT same command from ungranted local caller or with forged peer context
    ASSERT REJECT; ASSERT no unauthorized signing, spending or publication
  ASSERT no required peer wire field contains a process pointer or file path

TEST AT-C02 limits, exactness and dependency failure
  FOR EACH bounded field: ACT valid boundary and one-outside-boundary inputs
    ASSERT boundary accepted when remaining fixture permits it
    ASSERT outside boundary rejected before excessive allocation or effects
  ACT dependency unavailable before acceptance
  ASSERT no fabricated success; ASSERT noEffects
  ACT lose dependency reply after possible commitment
  ASSERT unknown/pending until recoverable status, not assumed rollback
  ASSERT no automatic new peer invocation or external execution

TEST AT-C03 owned state and immutable results
  ACT obtain snapshot/result reference; change later mutable publication
  ASSERT prior accepted terms and pinned bytes remain unchanged
  ACT unauthorized access or access after handle lifetime ends
  ASSERT REJECT; ASSERT other owner's data not exposed
  ACT restart with acknowledged durable state
  ASSERT committed obligations and replay guards remain; transient handles are not authority

TEST AT-C04 output discipline
  ACT invalid, truncated and cancelled input at each relevant boundary
  ASSERT terminal success only after the required complete validated result
  ASSERT progress is not completion; diagnostics do not contain fixture secrets
  ASSERT provider check evidence does not dictate requester outcome or refund
  ASSERT absent optional dependencies do not cause hidden network calls
```

These are parameterized contract checks, not a requirement to build every
deployment layout. Exercise each adapter the implementation claims to support;
at least one serialized adapter is needed before claiming process separation.

## End-to-end acceptance

These cases use real modules and real peer bytes, with controlled fault/clock
ports only. Repeat with independently implemented codecs/peers before claiming
interoperability. They exercise relationships that isolated tests cannot prove.

```text
TEST AT-E01 minimum useful node
  start A and B with only eight required modules, configured contacts and finite grants
  ACT authenticate B; read Board and definition; accept paid store of ASCII("abc")
  ASSERT result hash = hex("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
  save lease/contact/hash/expiry; restart B
  ACT paid retrieve, renew, byte check and remove under current terms
  ASSERT retrieved bytes = ASCII("abc"); check.outcome = pass
  ASSERT each successful paid operation has one exact local charge
  ASSERT removed lease is unavailable; optional provided offerings are absent

TEST AT-E02 contribution and wanted-role reversal
  A publishes wanted Storage paid in A credits; B has zero A credits
  B explicitly trusts A; A authorizes object and finite issuance
  ACT B offers, A proposes, B quotes, A accepts, B stores
  ASSERT requester = A; provider = B; issuer = A despite stream opened by B
  ASSERT B owns exactly the price in A credits, with no fictitious A self-balance
  A grants nonzero trust to B and publishes a provided offering
  ACT B spends the earned A credits; ASSERT both corresponding local views agree

TEST AT-E03 replacement-device recovery and independent replicas
  A encrypts object to its persistent key; buys separate leases from B and C
  save keys and catalog independently; destroy A's local data; stop B
  ACT restore A with same keys/catalog; retrieve from C; hash/authenticate/decrypt
  ASSERT plaintext equals original; no B response needed
  ASSERT two leases at B alone never count as two independent providers
  ACT restore replica target with another identity
  ASSERT count increases only after its complete independent successful store result

TEST AT-E04 local crash versus remote uncertainty
  FOR EACH durable coordination cut in Services SV-09:
    ACT paid store with crash/restart at cut and, separately, lost remote result
    ASSERT local lease/accounting state resolves consistently and applies at most once
    ASSERT lost remote result is outcome_unknown when commitment is possible
    ASSERT client creates no replacement store without explicit new authorization

TEST AT-E05 optional capabilities and shared formats
  run Files without Discovery runtime; run Messaging without calling Storage service
  ACT catalog and signed message recovery
  ASSERT catalog share records verify; message signatures and payload verify
  ACT requests to absent Computation/Feeds/Pages handlers in minimum node
  ASSERT unsupported/missing-offering failure before acceptance and no charge
  ACT disable new Messaging offerings while accepted placements remain
  ASSERT required retained recovery/status/replay data is preserved

TEST AT-E06 issuer-mediated settlement
  A buys a successful service from B using C credits with exact fee 2 and price 7
  C recognizes 100 credits owned by A and 0 by B
  ACT authorized transfer of 9; B queries C directly
  ASSERT C recognizes A=91, B=7; fee=2; B marks this invocation settled once
  FOR EACH [C refuses, response lost, forged forwarded receipt, reused payment ID]:
    ACT separate fresh scenario
    ASSERT no false settled state; service is not re-executed to repair payment

TEST AT-E07 full family workflow
  ACT index signed addresses/share record; locate host; authenticate and fetch Files manifest/pieces
  ASSERT exact hashes, discovery keys and independent host authentication
  ACT publish/read a feed and static root plus asset; place/discover/recover a signed message
  ASSERT verified signatures, selector/path matches and per-operation charges
  ACT bounded computation with result, language-error and time-limit fixtures
  ASSERT exact completion shapes and bounded metered settlement
  ASSERT neither descriptions nor returned content authorize extra spending

TEST AT-E08 standard application interface (when Node API supplied)
  use two authenticated client sessions with separate permissions and blobs
  ACT full Storage exchange through Node API; drop session after remote commit
  ASSERT durable provider obligation and accounting survive temporary blob cleanup
  ASSERT other client cannot access first client's blobs or bypass its budget
  ASSERT exact uint64 values and public wire bytes survive the local adapter
```

## Completion evidence

Record each test ID, matrix rows, applicable profile, adapter, implementation
version, fixture/vector revision, assertion outcomes and any unsupported policy
choice. Full-feature evidence includes every module operation, documented
validation/error class, durable-state transition, price model and check mode,
plus the integration cases. Link failures to the violated contract. Count a
matrix row as passed only if its assertions ran; a scenario description alone
is not execution evidence. Passing these suites guides implementation coverage;
it is not proof of security, performance or availability under every failure.
