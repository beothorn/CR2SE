# Peer Protocol

This module binds Boards, service definitions, invocations, checks, and ledger
control to Transport streams. Without a shared binding, matching service schemas
would still produce incompatible clients. This specification is language-neutral.

Open a [Transport](../transport/README.md) stream with protocol ID
`cr2se.peer` and protocol version `1`. One stream carries one exchange; different
exchanges use different streams. Do not allocate new Transport frame types.

See [pseudocode](./pseudocode/README.md) and [diagrams](./diagrams/README.md).

## Records and limits

Concatenate DATA payloads in each direction and parse these records:

```text
kind:   uint8
length: uint32 big-endian
body:   exactly length bytes
```

| Kind | Body |
|---:|---|
| `0x01` | One UTF-8 JSON control object. |
| `0x02` | `bodyId:uint32be || offset:uint64be || data:bytes`. |

Control bodies are `1..1,048,576` bytes. Binary bodies contain `1..65,536` data
bytes, so their record length is `13..65,548`. Validate length before allocation.
Records may span any number of Transport frames. Frame boundaries do not delimit
records. Unknown kinds, malformed JSON, duplicate members, trailing JSON,
invalid UTF-8, or illegal message order terminate this stream with
`PROTOCOL_ERROR`. Bound parsing depth to 32 and active transfers by local policy.

Receivers must support the stated maximum control size. Larger metadata needs a
different protocol version; it is not silently truncated. Boards and complete
definitions must each fit inside their control response. Publishers must
ensure this when advertising offerings. Large service values use bodies below.

All JSON objects have a `type` string. Numbers in control fields are unsigned
32-bit integers unless this document specifies another type. Every control
field described here is required unless marked optional. Unknown optional
members may be ignored; they cannot alter a version 1 operation. JSON null is
not a substitute for omission. Error text is diagnostic, never control logic.

## Value binding

Service values are decoded using their retrieved schema:

| Logical type | JSON metadata representation |
|---|---|
| `bool`, `string` | JSON boolean or string; a large string may use `$text`. |
| `int32`, `uint32` | Exact JSON integer number, without fraction/exponent. |
| `int64`, `uint64` | Canonical decimal string, without `+`, leading zeros, or negative zero. |
| `float`, `double` | Object `{"$float":"hhhhhhhh"}` or `{"$double":"hhhhhhhhhhhhhhhh"}`. |
| `bytes` | Object `{"$base64":"..."}` or detached `$bytes` descriptor. |
| `object`, `array` | JSON object or ordered array, recursively bound by schema. |

Float hex is lowercase and encodes IEEE 754 bits in big-endian order, preserving
signed zero. Infinity and NaN are allowed only if the contract permits them;
encode NaN as `7fc00000` or `7ff8000000000000`. Reject other NaN spellings.
Base64 uses the RFC 4648 standard alphabet, required padding, no whitespace,
and zero unused bits. Inline byte values contain at most 4,096 decoded bytes.

Detached descriptors have exactly these members:

```json
{"$bytes":0,"length":"1048576"}
```

For large strings replace `$bytes` with `$text`; length is UTF-8 bytes. IDs are
uint32, assigned from zero in traversal order: object fields sorted by unsigned
UTF-8 name bytes, arrays in index order. Each descriptor appears once. Bodies
are sent in ID order, with offset starting at zero and contiguous chunks. Reject
unknown IDs, overlaps, gaps, excess bytes, and missing bytes. Empty values are
inline. Text must validate as UTF-8 before successful acceptance. Receivers may
stream to bounded temporary storage, not necessarily memory.

This binding does not alter canonical signed objects. Discovery records,
manifests, signatures, and encryption envelopes remain the exact byte strings
defined by their own modules. Decode the byte value before hashing or signing.

Boards and service **definitions** are JSON documents, not schema-bound service
values. Their numeric fields retain the exact numeric form shown in their
specifications, including uint64. Use a lossless JSON parser for these documents;
never parse through binary64 and then try to recover a rounded integer.

Within ordinary peer control objects, identity IDs use canonical textual form.
Other fixed byte identifiers and hashes use padded Base64 strings. Prices,
lengths, and times named as uint64 use canonical decimal strings. These control
representations are distinct from the schema-bound service value above.

## Metadata exchanges

The stream opener sends one of:

```json
{"type":"board.get"}
```

```json
{"type":"service.get","offeringId":"storage-standard"}
```

The publisher replies with `{"type":"board","board":{...}}` or
`{"type":"definition","definition":{...}}`. A missing offering returns
`failure`. These messages have no binary bodies. Each endpoint sends END after
its final message. The response must come from the authenticated publisher;
forwarded documents have no implied publisher authentication.

These exchanges are uncharged, bounded control traffic. Providers may refuse,
rate-limit, or close abusive connections. They are not a free lookup or content
service. A definition request exposes only a current offering.

## Invocation proposal and quote

For a provided offering, the opener is the requester and first sends:

```text
type:             "propose"
offeringId:       string
publisherId:      identity (provider in this case)
service:          string
serviceVersion:   uint32
mode:             "invoke" or "check"
input:            schema-bound metadata, with no detached body data yet
creditIssuer:     identity expected by the requester
maximumPrice:     uint64, requester's explicit spending bound
transferId:       optional 16-byte Base64 ID; required for third-party credits
transferFee:      optional uint64; required for third-party credits
```

The provider validates identities, current terms, metadata, trust, resource
bounds, and price arithmetic. Lengths in body descriptors let it price a large
upload before receiving it. Validation requiring full content happens later.
The provider may reject without charging. Otherwise it sends:

```text
type:             "quote"
quoteId:          32 random bytes, Base64
offering:         complete current Board offering JSON
creditIssuer:     identity
priceMode:        "fixed" or "metered"
maximumPrice:     uint64 (exact price when fixed)
pricingInputs:    object; the extra uint64 values listed below, or empty
releaseCredits:   optional uint64, required only for Messaging remove
transferId:       the proposal's ID, only for third-party credits
transferFee:      the proposal's exact fee, only for third-party credits
```

The quote applies only on this stream. `priceMode` is metered only for
Computation. Recalculate the quote, validate the offering and issuer, and reject
any price above the requester's bound. Do not execute until the requester sends:

```text
type:      "accept"
quoteId:   the quoted ID
quoteHash: Base64 SHA-256 of the exact quote JSON body bytes received
```

This accepts the full quoted snapshot, including release credits and limits.
If the quote changed the selected contract's identifier/version/description,
reject it and fetch a new definition on another stream. Price changes within
the same supported contract still need explicit acceptance. A quote is not a
reservation guarantee until accepted; capacity may be refused at acceptance.
After acceptance its terms cannot be repriced.

Here, acceptance authorizes the bounded exchange and reserves payment capacity.
It does not assert that an uploaded object is valid or that a lease already
exists. Service-specific acceptance happens after complete input validation
and, where required, durable storage. Invalid bodies fail without creating a
successful service result.

For third-party credits, the requester chooses a fresh transfer ID and an exact
issuer fee before proposing work. It can obtain a fee quote on a separate
`ledger.transfer` stream without accepting that transfer. The provider binds
`(issuer, requester, transferId)` to this one invocation and must not reuse an
already bound payment for another invocation. Reserve `quoted maximumPrice +
transferFee`; this sum must fit uint64 and not exceed the proposal's spending
bound. With a participating requester/provider issuer, omit both transfer fields.

After valid output, the requester submits a transfer using that ID, with amount
`finalPrice + transferFee` and the provider as new owner. The provider queries
the issuer using `ledger.transfer.get` and verifies ID, owner, new owner, gross
amount, fee, and net `finalPrice` before recognizing payment once. The query uses
another authenticated connection/stream; the original invocation has ended.
No forwarded requester receipt or previously used transfer can settle the work.
If the issuer changes its fee, refuses, or remains unreachable, settlement is
unsettled/unknown; do not silently accept a different fee or claim success.
This risk is accepted explicitly before third-party-funded work begins.

Provider-dependent `pricingInputs` are:

| Operation | Fields |
|---|---|
| File Sharing `manifest` | `manifestBytes` |
| File Sharing `download` | `downloadBytes` |
| Storage `renew` | `sizeBytes` |
| Messaging `recover`, `renew` | `payloadSize` |
| Other operations | Empty object |

Each value is a uint64 decimal string. Validate it against retained original
metadata, a verified manifest, or the completed response. Missing prior evidence
does not allow an unbounded price: enforce `maximumPrice` and the service limits.
The output must match quoted sizes. The service's formula remains authoritative.

## Input, result, and failure

After acceptance, the requester sends the detached input bodies, followed by
`{"type":"input.end"}` and Transport END. No binary bytes may precede acceptance.
The provider validates complete input and performs the operation. It replies:

```text
type:        "result"
output:      schema-bound output metadata
finalPrice:  uint64
```

Then it sends detached output bodies, `{"type":"result.end"}`, and END. A
successful result requires all metadata, exact bodies, the terminal marker, and
normal stream completion. Do not expose provisional bytes as a successful
service result. Cryptographic plaintext also requires its authentication check.

For fixed-price work, `finalPrice` equals the accepted price. For Computation,
recalculate it from the completion record and accepted formula. If the service
output contains `price` or `finalPrice`, that field must equal the envelope
price. The envelope supplies the price for outputs without a price field, such
as Messaging recovery. A later local check is not required to allow charging.

A provider may instead send:

```text
type:    "failure"
code:    machine-readable string from the table below
message: optional diagnostic UTF-8 string, at most 1,024 bytes
```

Then END. A failure is uncharged and cannot follow `result.end`. A provider
detecting a failure during body transmission sends failure instead of
`result.end`; discard the provisional output. Release uncommitted reservations.
Committed side effects whose response may have been lost are outcome unknown,
not a claim of rollback. The [service interruption rules](../services/README.md)
and service-specific retry guards apply.

| Code | Meaning |
|---|---|
| `invalid_request` | Malformed fields, invalid value, or forbidden operation. |
| `unsupported` | Unsupported service, version, mode, or settlement choice. |
| `not_available` | Missing resource, inactive lease, or concealed authorization failure. |
| `not_authorized` | Refused access where this does not leak resource existence. |
| `terms_changed` | Offering no longer matches the selected contract or quote. |
| `price_rejected` | Price exceeds the bound or exact agreement failed. |
| `insufficient_credits` | Spendable credits or finite issuance budget insufficient. |
| `resource_limit` | Size, concurrency, time, or capacity limit reached. |
| `conflict` | Stale expiration or conflicting replay ID. |
| `internal_error` | Provider failed without successful output. |

Unknown failure codes are generic service failures; do not retry automatically.
Transport CANCEL ends the exchange, not already committed work. Socket loss or
truncation after acceptance is outcome unknown. There is no generic remote
job-status or invocation-resumption operation.

## Wanted offerings

A prospective provider opens a stream to the wanted-offering publisher and
sends `{"type":"offer","offeringId":"...","service":"...","serviceVersion":1}`.
This is a bounded control proposal, not a command to perform work.

The publisher may refuse, or become requester by sending `propose` on the same
stream. Its `publisherId` is its own ID. The prospective provider verifies the
wanted offering and returns `quote`. The requester sends `accept`, input bodies,
`input.end`, and END; the provider sends the result and END. Thus application
roles are independent of the stream opener. The publisher obtains input from a
locally authorized application; an incoming offer cannot fabricate that input
or compel spending. Current terms and credit direction follow Board rules.

## Check binding and retries

Use `mode:"check"` only for remote checks. The proposal input follows the
service's `check.input`. Storage and Messaging return their byte evidence,
without a provider-computed `outcome`. Discovery returns `indexId`, `recordId`,
and `record` (exact retained bytes). The requester builds the logical check
output and computes pass/fail/inconclusive locally.

The evidence value uses these schemas: IDs and record/value fields are `bytes`;
offset is `uint64`. Require the exact fixed lengths from the service specification.
Discovery's one included retention check quotes price zero, bound to an active
placement owned by this requester. It consumes that placement's allowance only
on a complete evidence response. Storage and Messaging quote the current
`checkPrice`. Local-only checks are not callable remotely; use local validation.
The byte-check response deadline begins at `input.end`.

A service-defined idempotent Messaging recovery/removal retry is recognized
before checking new prices, current balance, or pending state. Validate the
original caller and all original request fields. Return `result` directly with
the identical cached service output and original price, then `result.end` and
END. This is allowed only after a matching `propose`; no quote, new body, or new
charge occurs. The requester ends its direction when it receives this result.
The original payment is applied locally at most once using recovery/removal ID,
even if the original response was lost. Never treat an unrelated early result
as an accepted invocation.

## Ledger control

Ledger controls use the same records and `failure` format, on independent
streams. They are bounded, rate-limited prerequisites; transfer fees may be zero.
They do not implement a free general resource service.

| First message | Required fields | Successful response |
|---|---|---|
| `ledger.balance` | None | `ledger.balance.result`, `balance` uint64 issued to the authenticated caller. |
| `ledger.transfer` | `order` Base64 121 bytes, `ownerPublicKey` Base64 32 bytes, `signature` Base64 64 bytes, `maximumFee` uint64 | Fee quote, acceptance, then transfer result. |
| `ledger.transfer.get` | `ownerId` identity, `transferId` Base64 16 bytes | Stored transfer result, for original or new owner only. |
| `ledger.claim.redeem` | `envelope` Base64 generic encrypted claim-redemption object | `ledger.claim.result`, `claimId` Base64 32 bytes, `amount` uint64. |

For a new transfer the issuer sends `{"type":"ledger.transfer.quote",
"transferId":"...","fee":"..."}`. The owner accepts with
`{"type":"ledger.transfer.accept","transferId":"...","fee":"..."}`.
Require exact equality and `fee <= maximumFee`. Recheck available balance
under lock before commitment. A stored accepted retry returns its original
result directly and does not requote.

The transfer result has `type:"ledger.transfer.result"`, `ownerId`, `newOwnerId`,
`transferId`, `amount`, `fee`, and `receivedAmount`; all amounts are uint64.
The issuer is the authenticated responder. `receivedAmount = amount - fee`.
Never accept a requester-forwarded JSON result as proof of issuer commitment;
the provider queries the issuer directly. A failure changes no balance.

Control request senders may half-close after their last message; transfer owners
must wait until fee acceptance before END. Responders END after the final result
or failure. Claim retries return the original amount to the original redeemer.
Granting credits, creating claims, and changing trust are local administrator
operations, not unsolicited peer commands.

## Reachability and scope

TCP connections are bidirectional: a node behind NAT can initiate a connection
to a reachable community peer and serve requests over that same connection.
Keep useful connections alive within local limits. Discovery advertisements
do not open firewall ports or make a private endpoint public.

Version 1 does not define transparent relaying, hole punching, onion routing,
global broadcast, or automatic third-party spending along a discovery route.
Private-to-private peers need an already usable route or a reachable deployment
endpoint; a relay would require its own future paid service contract. Stored
Messaging placements let recipients collect messages later without being
online when the sender places them.
