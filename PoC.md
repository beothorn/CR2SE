# First proof of concept

Build the implementation in a separate project. The goal is an observable
exchange between independent nodes, followed by recovery on replacement
hardware. This guide does not require a particular programming language,
database, operating system, or UI framework.

## Minimum useful profile

The [required modules](./ModuleContracts.md#required-and-optional-capabilities)
are Identity, Cryptography, Transport, Peer Control / Peer Protocol, Ledger,
Board, Services and Storage. A minimum implementation can use authorized local
calls, configured peer contacts and finite trust/credit grants. It needs neither
Node API nor the six optional service families. This profile is a useful paid
storage node, not just a handshake or empty Board demonstration.

Verify it with two separately operated identities:

1. Authenticate a configured contact and retrieve a consistent Storage offering
   and definition using Peer Control.
2. Reserve finite credits, agree the price and store a nonempty object. Retain
   the lease ID, provider contact, hash, expiration and encryption metadata.
3. Restart the provider and retrieve/verify the object with a new paid request.
4. Exercise renewal, paid byte check and removal, including unauthorized access,
   stale expiration, concurrent reservations and uncertain output delivery.
5. Run with Node API and every optional family absent. Unsupported offerings
   must not appear as provided capabilities or be silently dispatched elsewhere.

Before integration, implement each module against its `inputs/` and `outputs/`
contracts with substitutes for dependencies. Compare direct-call behavior with
serialized adapters for exact integers, scoped authority, byte streaming and
failures. For a process-separated composition, inject lost replies/restarts at
the prepare, decision and commit boundaries and verify one local effect without
re-executing accepted work. Existing cryptographic/wire vectors stay unchanged.

The topology, stages and full matrix below describe the **full-feature PoC**.
They remain useful additional coverage; they do not make optional modules
mandatory for every CR2SE node. Report minimum-profile and full-feature results
separately. Independent replicas require a third identity and retained recovery
metadata as in the story below.

## Topology and initial policy

Use three identities: Alice, Bob, and Carol. Run each with its own keys, durable
state, and controllable clock. Alice exposes a reachable TCP endpoint; Bob
initiates an outbound connection. Carol supplies an independent replica and
later exercises third-party credit transfers. Use one active writer per identity.

Configure a finite bootstrap grant, explicit nonzero trust where needed, and
per-client spending limits. Also test earning credits by fulfilling a wanted
offering. Do not hide bootstrap behind unlimited balances or automatic trust.
Keep test identity keys separate from real identities.

## Implementation order

| Stage | Deliverable | Observable completion criterion |
|---|---|---|
| 1. Primitives | Identity, Cryptography, exact integer/byte codecs | Existing deterministic vectors match byte for byte. |
| 2. Connections | Transport handshake, integrity, stream state | Both peers can initiate streams on one connection; malformed tags close it. |
| 3. Common exchange | Board, Services, Peer Protocol, Ledger | Fetch a definition, accept a quote, stream input, return output, settle once locally. |
| 4. Client boundary | Authorized embedded control; optional standard Node API | A client uses explicit issuer/spending bounds; the full PoC also tests authenticated IPC and blobs. |
| 5. Cooperative storage | Wanted work, paid leases, encrypted replicas | Earn credits, place two copies, then recover with one provider offline. |
| 6. Remaining families | Computation, Messaging, Discovery, Files, Feeds, Pages | Exercise every operation and check in the feature matrix below. |
| 7. Failure and portability | Journaling, retry guards, independent codec/client | Restart after injected failures and restore application data on a fresh node. |

For the minimum profile, complete the applicable core stages and minimum
demonstration above. For the full-feature PoC, early stages are development
milestones: do not claim full draft coverage until the complete feature matrix
passes. An optional Computation runtime may initially advertise one exact
supported language/version;
other node and client implementation languages remain unrestricted.

## End-to-end story

1. Bob reads Alice's Board and offers a bounded wanted service. Alice authorizes
   the input; Bob completes the work; Alice issues credits to Bob. Alice chooses
   nonzero trust in Bob after checking the contribution.
2. Bob encrypts a test object to his persistent encryption key. He hashes the
   resulting bytes and creates independent paid leases at Alice and Carol.
3. Bob backs up his keys and recovery catalog, including both provider IDs,
   endpoints, lease IDs, hashes, encryption format, and expiration times.
4. Perform paid random byte checks and a renewal with `expectedExpiresAt`.
5. Shut down Bob's original node and Alice. Restore Bob's identity and catalog
   on a fresh node with no copy of the original data.
6. Authenticate Carol, accept the current retrieval price, retrieve ranges,
   verify the stored hash, authenticate/decrypt, and compare the original file.
7. Restore redundancy at another usable provider. Log issuer-specific balances
   and agreed prices without logging private keys or plaintext secrets.

This demonstrates portable recovery, not recovery from lost keys or from loss
of every replica and catalog.

## Full feature matrix

| Module | Demonstrations required for full-feature coverage |
|---|---|
| Identity | Creation; binary/text round trip; case normalization; contact QR; expected-ID mismatch; same-identity connection. |
| Cryptography | Key binding; generic self/recipient encryption; tampered header/tag rejection; no plaintext before authentication. |
| Transport | Fragmented/coalesced reads; parity and exact stream sequence; half-close; cancel; GOAWAY; resource limits; replay/tag failure. |
| Peer Protocol | Metadata requests; quote hash; fixed and metered bounds; detached bytes/text; malformed offsets; wanted-role reversal; failure versus unknown outcome. |
| Board and Services | Provided/wanted offerings; separately retrieved definitions; field descriptions; unknown optional metadata; unsupported required semantics; stale terms. |
| Ledger | Spend provider credits; issue requester credits; independent issuer balances; transfer quote/fee/signature/replay; encrypted claim redemption; finite bootstrap; concurrent reservations. |
| Node API | Token/version rejection; JSON-line limits; out-of-order responses; session-owned blobs; cancellation; spending/issuer bounds; no cross-session handle access. |
| Storage | Store; partial/full retrieve; renewal guard; removal; paid byte check; expiry; hash mismatch; authorization; independent replicas. |
| Computation | Result; language error; time-limit completion; exact ceiling price; maximum reservation; unsupported runtime; local independent check. |
| Messaging | Plain/encrypted placement; recipient-only discovery/recovery; sender signature; both recovery signatures; same-ID retry; pending/recovered renewal; release-credit quote and idempotent removal; status; byte check; replicas. |
| Discovery | All three signed record kinds; paid atomic index; resolveIdentity; locateShare; findTrust; listIdentities; three-field listTrust cursor; included retention check; tied equivocation; bounded iterative lookup. |
| Public Files | Canonical multi-file manifest; signed catalog; paid manifest and piece ranges; multi-host resumption; piece/file hash validation; safe paths. |
| Public Feeds | Signed publication; attachments; latest/since/interval reads; exclusive cursor; response-byte bounds; empty paid page; merged local feed. |
| Static Pages | Local root publication; path/media validation; fixed-price bounded retrieval; immutable response snapshot; local hash check; separately paid assets. |

## Crash and abuse cases

Inject a crash or connection loss before acceptance, during input, before local
commit, after commit but before response, and during result transfer. After
restart verify that balances cannot underflow, claims and transfers cannot apply
twice, accepted leases survive, and an uncertain result is not silently retried.

Repeat Messaging recovery/removal with the original ID and with a conflicting
ID. Repeat renewal using a stale expiration. Interleave two spends that each
fit individually but exceed the available balance together. Test uint64 maxima,
price overflow, invalid Base64, duplicate JSON fields, malformed schemas, and
large lengths before allocation.

Reject unauthorized lease/message IDs without revealing whether they exist.
Run arbitrary computation only inside an explicitly configured local execution
boundary suitable for the PoC. A peer's description or model output must not
change that boundary or authorize further actions.

## Interoperability evidence

Start with the [transport vectors](./modules/transport/pseudocode/TestVectors.md)
and the fixed vector in [Cryptography pseudocode](./modules/cryptography/pseudocode/README.md).
The Discovery, Public File Sharing, and Public Feeds specifications also contain
canonical vectors. Reproduce these in at least two independently written codecs
or implementations before claiming interoperability.

The [Peer Protocol encoding vectors](./modules/peer-protocol/pseudocode/TestVectors.md)
cover initial control/body records and exact numeric value representations.

Capture golden fixtures for the new Peer Protocol records, all typed values,
large bodies crossing frame boundaries, quotes, failures, transfer/claim controls,
and Node API blob exchanges. Compare bytes, logical results, and balance changes.
Use exact values such as `18446744073709551615`, signed 64-bit minima, empty bytes,
UTF-8 multibyte strings, and signed-zero floats. Do not compare only formatted JSON.

The PoC report should record implemented service versions, runtime pairs, passed
matrix rows, known limits, failure-injection results, and a reproducible restore
procedure. Production performance, security review, larger network behavior,
and stronger storage proofs remain separate validation work.
