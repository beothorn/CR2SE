# CR2SE Storage

CR2SE Storage is a standard, paid service for retaining an immutable sequence of
bytes at another CR2SE identity for an agreed period.

The requester chooses the amount of data and the retention period within the
limits advertised by the provider. The price is calculated deterministically
from the advertised factors before the provider accepts the operation.

Storage implementations may use files, databases, object stores, erasure
coding, replication, compression, remote backing services, or another internal
design. Those choices are not observable parts of the contract. A conforming
implementation must nevertheless retain the exact stored bytes, return exact
bytes for an accepted retrieval, honor lease times, calculate prices as
specified, enforce authorization, and implement the defined checks.

Common terms such as **identity**, **service requester**, **service provider**,
**offering**, **credit issuer**, and **check** are defined in the
[CR2SE Glossary](./Glossary.md). The common service and pricing rules are defined
in [Services](./Services.md) and [Board](./Board.md).

---

## 1. Version 1 service

The version 1 Storage service is identified by:

```text
service:        cr2se.storage
serviceVersion: 1
pricing model:  cr2se.storage.v1
```

One Storage offering creates leases and supports the following operations on
those leases:

```text
store       create a lease and upload its bytes
retrieve    retrieve a byte range from an active lease
renew       extend an active lease
remove      end a lease early
check       challenge the provider for one stored byte
```

Using one service for these operations is intentional. Each charged operation
selects a current compatible offering and agrees its own price.

`store`, `retrieve`, `renew`, and `remove` are separately charged operations. A
check is charged according to the offering's `checkPrice` as described below.

All byte offsets and lengths are zero-based and measured in bytes. Storage does
not interpret text encodings, file formats, or the contents of stored data.

---

## 2. Lease model

A successful `store` operation creates one **storage lease** between the
requester identity and provider identity.

A lease contains at least:

```text
lease ID
requester identity
provider identity
offering ID and version
stored size
SHA-256 content hash
acceptance time
expiration time
price paid for the accepted store operation
lease state
```

The stored byte sequence is immutable. Changing even one byte requires a new
lease. A provider must not silently repair, replace, truncate, append to, or
otherwise change the logical byte sequence associated with a lease.

The same data may be stored in several independent leases, including leases at
different providers. CR2SE Storage version 1 does not create replicas
automatically and does not imply that one lease is redundant.

A lease is a retention commitment, not a promise that the provider is
continuously online or that future operations keep their previous prices. An
offline provider does not stop the lease clock. Availability and economic
behavior are evaluated by the requester through checks, attempted retrievals,
local trust, and the behavior of independent replicas.

### Lease states

Conceptually, a lease has these states:

```text
receiving -> active -> expired
                  \-> removed
```

`receiving` is not a completed lease and creates no storage obligation. A lease
becomes `active` only after the complete upload has been received, validated,
and durably accepted.

An active lease becomes expired at its expiration time unless it was renewed.
An active lease becomes removed when a valid `remove` operation succeeds.

The internal representation of these states is implementation-dependent.

---

## 3. Pricing representation and Board offering

CR2SE credits are unsigned integers; fractional credits do not exist. Storage
rates, however, often cost much less than one credit per byte or per byte-second.
One byte-second means retaining one byte for one second. A field containing only
an integer number of credits per byte could not express a practical rate such as
one credit per one million bytes.

Storage therefore represents every usage factor as an exact fraction:

```json
{
  "numerator": 1,
  "denominator": 1000000
}
```

The fields mean:

```text
numerator: uint64
    Number of credits in the rate. Range: 0 .. 2^64-1.

denominator: uint64
    Number of the applicable units covered by that rate.
    Range: 1 .. 2^64-1; zero is invalid.
```

The example represents exactly:

```text
1 credit / 1,000,000 applicable units
```

For `byteUsageFactor`, the applicable unit is one uploaded byte, so this means
one credit per one million uploaded bytes. A rate of three credits per one
million bytes is represented as:

```json
{
  "numerator": 3,
  "denominator": 1000000
}
```

The fraction is not itself a fractional credit transfer. It is an exact rate
used to calculate the complete operation price, which is then rounded upward to
an integer as defined in section 4.

This fraction representation is required instead of JSON decimal or
floating-point values. For example, the decimal `0.000001` cannot be relied on
to have exactly the same binary representation and rounding behavior in C,
Java, JavaScript, Rust, and other languages. Integer numerator-and-denominator
arithmetic produces the same result in every conforming implementation.

### Factor meanings

The applicable unit is fixed by the factor's field name:

```text
byteUsageFactor
    One-time store charge per byte uploaded.

byteStorageDurationFactor
    Initial retention charge per byte-second. One byte-second means retaining
    one byte for one second.

retrievalByteUsageFactor
    Retrieval charge per byte returned.

renewalByteStorageDurationFactor
    Renewal charge per added byte-second. Renewal does not charge
    byteUsageFactor again because it does not upload the object again.
```

A factor numerator may be zero. For example, a provider may charge for storage
duration without a separate per-uploaded-byte component.

`minimumPrice` is a `uint64` in the range `1 .. 2^64-1`. It is the minimum price
of each calculated `store`, `retrieve`, or `renew` operation, not an extra fee
added to the calculated price.

`removePrice` is a `uint64` in the range `1 .. 2^64-1` and is the exact price of
a successful `remove` operation.

`checkPrice` is the exact `uint64` price of one Storage check and is expressed
in credits issued by the offering's `creditIssuer`.

### Offering limits

Before seeing the complete offering, the fields in its `info` object mean:

```text
maximumBytes
    Largest size accepted by one store operation. Range: 1 .. 2^64-1.

minimumRetentionSeconds
    Smallest initial or renewal duration. Range: 1 .. 2^64-1.

maximumRetentionSeconds
    Largest duration accepted by one store or renew operation.

maximumTotalRetentionSeconds
    Current latest permitted renewal expiration relative to a lease's original
    acceptedAt. Advertising it does not promise that the same limit or renewal
    price will remain advertised later.

maximumRetrieveBytes
    Largest range returned by one retrieve operation. Range: 1 .. 2^64-1.

checkResponseSeconds
    Maximum requester-observed seconds allowed for one valid byte challenge.
    Range: 1 .. 2^64-1.
```

The following relations are required:

```text
minimumRetentionSeconds <= maximumRetentionSeconds
maximumRetentionSeconds <= maximumTotalRetentionSeconds
```

### Complete offering shape

With the pricing fields and limits now defined, a version 1 provided or wanted
Storage offering has this form:

```json
{
  "id": "storage-standard",
  "service": "cr2se.storage",
  "serviceVersion": 1,
  "description": "Store requester-selected data for a requester-selected period.",
  "creditIssuer": "PROVIDER_ID",
  "pricing": {
    "model": "cr2se.storage.v1",
    "minimumPrice": 1,
    "byteUsageFactor": {
      "numerator": 1,
      "denominator": 1000000
    },
    "byteStorageDurationFactor": {
      "numerator": 1,
      "denominator": 86400000000
    },
    "retrievalByteUsageFactor": {
      "numerator": 1,
      "denominator": 1000000
    },
    "renewalByteStorageDurationFactor": {
      "numerator": 1,
      "denominator": 86400000000
    },
    "removePrice": 1
  },
  "checkPrice": 1,
  "info": {
    "maximumBytes": 1000000000,
    "minimumRetentionSeconds": 3600,
    "maximumRetentionSeconds": 2592000,
    "maximumTotalRetentionSeconds": 31536000,
    "maximumRetrieveBytes": 1000000000,
    "checkResponseSeconds": 30
  },
  "preconditions": [
    "cr2se.identity"
  ]
}
```

The numeric values are illustrative. A provided offering states terms its
publisher will accept as provider. A wanted offering states terms its publisher
offers as requester. The other identity decides whether to accept those terms.

A version 1 Storage offering must use `pricing`; it must not use the fixed
`price` field. It must contain every pricing and `info` field shown above,
including `checkPrice`. Every Storage check is separately paid at the current
offering's check price.

It must also contain the `cr2se.identity` precondition. Storage lease
authorization cannot be implemented from an unauthenticated connection.

These are per-lease and per-operation limits. A provider may also apply local
capacity, trust, concurrency, and rate policies before accepting a new store.
It must not use such policy to avoid an already accepted lease obligation.

Changing or removing the offering does not shorten an already accepted lease or
change its bytes, hash, ownership, acceptance time, or expiration time. It may
change the price and limits of future retrieve, renew, remove, and paid check
operations. Each such operation selects a currently advertised compatible
Storage offering from the provider.

---

## 4. Price calculations

### Exact arithmetic

Let:

```text
S  = stored size in bytes
T  = requested initial retention in seconds
L  = requested retrieval length in bytes
A  = requested renewal extension in seconds

B.n / B.d = byteUsageFactor
X.n / X.d = byteStorageDurationFactor
R.n / R.d = retrievalByteUsageFactor
N.n / N.d = renewalByteStorageDurationFactor
M             = minimumPrice
```

In the formulas below, `ceil(value)` means the smallest integer greater than or
equal to `value`. `max(left, right)` selects the greater of its two arguments.

The prices are:

```text
storePrice = max(M, ceil(S*B.n/B.d + S*T*X.n/X.d))

retrievePrice = max(M, ceil(L*R.n/R.d))

renewPrice = max(M, ceil(S*A*N.n/N.d))

removePrice = the advertised removePrice value
```

The sum in `storePrice` is rounded upward once after its two exact rational
terms are added. Implementations must not round each term separately.

For example, with `S = 1000`, `T = 10`, `byteUsageFactor = 1/1000`,
`byteStorageDurationFactor = 1/10000`, and `minimumPrice = 1`:

```text
storePrice = max(1, ceil(1000/1000 + 1000*10/10000))
           = max(1, ceil(1 + 1))
           = 2 credits
```

The following vector distinguishes the required single rounding from incorrect
per-term rounding:

```text
S = 1, T = 1, B = 1/2, X = 1/2, M = 1

storePrice = max(1, ceil(1/2 + 1/2)) = 1 credit
```

Rounding each half upward first would incorrectly produce 2 credits.

All input values and final prices are unsigned integers. Implementations must
calculate with arbitrary-precision integers or an equivalent overflow-safe
algorithm. If the exact final price exceeds `2^64-1`, the operation is invalid
and must be rejected before acceptance. Floating-point arithmetic must not be
used to calculate a protocol price.

The prices obtained by substituting the advertised maxima into `storePrice`,
`retrievePrice`, and `renewPrice` must each fit in `uint64`. An offering that
permits an input whose calculated price cannot be represented is invalid; it
must not defer that discovery until a requester selects the input.

For positive integers, an implementation may calculate one rational term as:

```text
ceil(a / b) = (a + b - 1) div b
```

provided its intermediate arithmetic cannot overflow.

### Price agreement

Before transmitting a large upload or retrieval result, both peers must derive
the same price from the selected current offering and the validated
request metadata. The provider must reject the operation if the requester does
not accept that exact price.

The price is based on the declared and validated logical byte count, not on
frame overhead, encryption overhead outside the stored value, compression used
internally by the provider, or physical disk allocation.

### Prices of later operations

Only the price of an operation that both peers have accepted is fixed. Creating
a lease does not reserve future bandwidth or force the provider to maintain the
same retrieval, renewal, removal, or check prices.

An initial `store` may be arranged through a provided or wanted offering under
the common Board rules. Each later charged lease operation selects a current
provided offering from the lease's provider. A compatible follow-up offering
has:

```text
service = cr2se.storage
serviceVersion = 1
pricing.model = cr2se.storage.v1
```

It need not have the same offering ID or economic terms as the offering used to
create the lease. The selected current offering supplies the `creditIssuer`,
pricing factors, operation limits, and `checkPrice` for that operation. The
requester sees the new exact price and may accept or reject it before execution.

If the provider advertises no compatible offering, the later operation is
currently unavailable and must not be charged. Advertising a high price is not
itself a protocol failure: no operation has yet been accepted at another price.
The requester may treat price increases, withdrawn offerings, repeated refusal,
or poor availability as inputs to its local trust and provider-selection policy.

This flexibility is deliberate. Storage peers may be domestic machines with
changing electricity, disk, bandwidth, and opportunity costs. Requiring them to
guarantee future prices could make long leases economically unsafe to offer.
CR2SE addresses that risk through local trust, competition among peers, and
redundant leases rather than through permanent price controls.

---

## 5. Store

### Input

The logical `store` input is:

```text
operation:        "store"
sizeBytes:        uint64
retentionSeconds: uint64
contentHash:      bytes (exactly 32 bytes)
data:             bytes (exactly sizeBytes bytes)
```

`sizeBytes` must be at least 1 and no greater than `maximumBytes`.
`retentionSeconds` must be within the offering's minimum and maximum retention
limits. `contentHash` must equal:

```text
SHA-256(data)
```

The declared metadata is sent before, or otherwise independently of, the
possibly streamed `data` value so the provider can validate limits and agree on
the price before accepting the upload body. The transport binding may split
`data` across any number of bounded frames; frame boundaries are not part of the
stored value.

Zero-length objects are not supported in version 1. They provide no storage
utility while still consuming lease and accounting resources.

### Acceptance

The provider must not report success until it has:

1. received exactly `sizeBytes` bytes;
2. computed and matched `contentHash`;
3. committed the exact bytes to storage intended to survive ordinary process
   restart or machine reboot;
4. created a unique lease ID;
5. recorded the requester, terms, and times needed to honor the lease.

Durability does not require any particular medium or replication count. Data
held only in volatile working memory at the moment success is reported does not
satisfy the version 1 contract.

`acceptedAt` is the provider's current Unix time in whole seconds when all five
conditions become true. Unix time is the number of elapsed seconds since
1970-01-01T00:00:00Z, excluding leap seconds.

```text
expiresAt = acceptedAt + retentionSeconds
```

An addition that exceeds `uint64` must be rejected rather than wrapped.

### Lease ID

`leaseId` is exactly 32 bytes generated by the provider using a
cryptographically secure random number generator. It must be unique among that
provider identity's leases. It is an opaque identifier and is not a content
hash, encryption key, password, or bearer authorization token.

### Output

A successful `store` output is:

```text
operation:   "store"
leaseId:     bytes (exactly 32 bytes)
sizeBytes:   uint64
contentHash: bytes (exactly 32 bytes)
acceptedAt:  uint64 Unix seconds
expiresAt:   uint64 Unix seconds
price:       uint64 credits
```

The returned size and hash must match the input. `price` must equal the exact
price agreed before the upload.

The operation is charged only after this successful output. Invalid metadata,
an incomplete upload, too many or too few data bytes, a hash mismatch, storage
failure, interruption before success, or refusal by policy is a service failure
and must not be charged.

---

## 6. Authorization

Only the requester identity recorded on a lease may retrieve, renew, remove, or
check it. The requester must prove control of that identity using the CR2SE
identity authentication mechanism.

Knowledge of a lease ID is not authorization. A request made through a new
connection or another node using the same identity remains authorized after
successful identity proof. A request from a different identity is unauthorized
even if that identity knows the lease ID, content hash, or encryption key.

An unauthorized response must not reveal whether the lease exists, its size,
its hash, its expiration, or its state.

Providers must apply practical rate limits to failed authorization attempts and
lease-ID probing. Such limits must not make normal use of an authenticated
active lease impossible.

---

## 7. Retrieve

Retrieval is paid separately from storage. A requester may request any number of
paid retrievals while the lease is active. Each one requires a current
compatible provider offering, sufficient accepted credits, price agreement, and
provider acceptance.

### Input

```text
operation: "retrieve"
leaseId:   bytes (exactly 32 bytes)
offset:    uint64
length:    uint64
```

`length` must be in `1 .. maximumRetrieveBytes` from the selected current
offering. The range is valid only when:

```text
offset < sizeBytes
length <= sizeBytes - offset
```

This subtraction form is normative for validation because `offset + length`
could overflow fixed-width arithmetic.

To retrieve the complete object, use `offset = 0` and `length = sizeBytes`.
When the object is larger than `maximumRetrieveBytes`, the requester uses
several non-overlapping or overlapping range requests.

### Output

```text
operation:   "retrieve"
leaseId:     bytes (exactly 32 bytes)
offset:      uint64
data:        bytes (exactly length bytes)
contentHash: bytes (exactly 32 bytes; hash of the complete stored object)
price:       uint64 credits
```

`data` must equal the requested range of the original stored byte sequence. The
whole-object `contentHash` lets a requester validate a reconstructed complete
object. It is not the hash of the returned range unless the range is the whole
object.

The retrieval price uses the `minimumPrice` and `retrievalByteUsageFactor` from the
selected current offering. Before returning `data`, the provider communicates
the calculated price and the requester accepts or rejects it.

A retrieve request is timely when the provider accepts its metadata while:

```text
providerCurrentTime < expiresAt
```

Once a timely retrieve has been accepted and its price agreed, the provider
must complete it even if `expiresAt` occurs during transfer. A successful
retrieval is charged after the complete valid output. An invalid range,
inactive lease, authorization failure, insufficient accepted balance, or
interruption before successful output must not be charged.

---

## 8. Renew

Renewal extends an active lease without uploading its data again. Renewal uses
the `minimumPrice` and `renewalByteStorageDurationFactor` from the selected current
offering.

### Input

```text
operation:         "renew"
leaseId:           bytes (exactly 32 bytes)
expectedExpiresAt: uint64 Unix seconds
additionalSeconds: uint64
```

The lease must be active when the provider accepts the request.
`expectedExpiresAt` must equal the lease's current expiration. This comparison
prevents a duplicated or delayed renewal request from extending and charging a
lease twice.

`additionalSeconds` must be within the selected current offering's
`minimumRetentionSeconds` and `maximumRetentionSeconds`. The proposed new
expiration must satisfy its current total-retention limit:

```text
newExpiresAt = expectedExpiresAt + additionalSeconds

newExpiresAt <= acceptedAt + current maximumTotalRetentionSeconds
```

Both additions must be overflow-safe.

A renewal is an optional new agreement. The provider may reject it because of
current capacity, price disagreement, trust, policy, or limits. Rejection does
not shorten the already active lease and is not charged. To retain data beyond
the maximum permitted by available renewal offerings, the requester must create
a new lease, which includes uploading the data again.

### Output

```text
operation:         "renew"
leaseId:           bytes (exactly 32 bytes)
previousExpiresAt: uint64 Unix seconds
expiresAt:         uint64 Unix seconds
price:             uint64 credits
```

Renewal becomes effective atomically with successful output. The provider must
serialize concurrent renewals for the same lease. At most one request with a
particular `expectedExpiresAt` can succeed.

An unsuccessful renewal does not change the expiration and must not be charged.
A successful renewal is separately charged using `renewPrice`.

---

## 9. Remove

`remove` lets the requester end an active lease early.

### Input

```text
operation: "remove"
leaseId:   bytes (exactly 32 bytes)
```

### Output

```text
operation: "remove"
leaseId:   bytes (exactly 32 bytes)
removed:   bool (true)
price:     uint64 credits
```

On successful output, the provider's availability obligation ends immediately
and later retrieve, renew, and check requests must treat the lease as inactive.
No credits are refunded. A successful remove is separately charged at the
`removePrice` in the selected current offering. Although removal releases
provider resources, the nonzero charge preserves the common CR2SE rule that
every service invocation has a price.

Success means that the bytes are no longer logically retrievable through CR2SE.
It does not promise physical erasure from every medium, backup, journal, or
storage layer. Secure deletion guarantees require a separate service contract.

Removing an already removed, expired, or unknown lease returns a failure and is
not charged. If a success response is lost, the parties' ledgers may disagree as
described by the common service rules; retrying confirms only that the lease is
inactive.

---

## 10. Storage check

The Storage check asks for the byte at one requester-selected offset.

### Availability and authorization

A check is available only to the authenticated requester while the lease is
active. The offset must satisfy:

```text
0 <= offset < sizeBytes
```

The requester should choose offsets using a cryptographically secure random
number generator when it wants random sampling. The offset is sent only when
the challenge begins; pre-announced or predictable offsets provide weaker
evidence.

The requester starts the check timer immediately after sending the complete
challenge. Provider evidence must arrive within the selected current offering's
`checkResponseSeconds`. This duration includes network transit and provider
processing. A timeout is `inconclusive`, because the requester cannot determine
whether storage failure, network failure, or delay caused it.

### Check input

```text
leaseId: bytes (exactly 32 bytes)
offset:  uint64
```

### Provider evidence

The provider returns:

```text
leaseId: bytes (exactly 32 bytes)
offset:  uint64
value:   bytes (exactly 1 byte)
```

The expected byte is never sent to the provider. Otherwise a provider could
pass by echoing the expected value without reading the stored object.

### Outcome

The requester's checking implementation compares `value` with the byte at
`offset` in its original stored data:

```text
pass
    Authenticated, well-formed evidence arrived for the active lease within
    checkResponseSeconds and value equals the original byte at offset.

fail
    Authenticated, well-formed evidence arrived but value differs, or the
    provider reports that the authorized active lease or byte is unavailable.

inconclusive
    No authenticated and well-formed evidence arrived, the requester no longer
    has the expected byte, timing is ambiguous at expiration, or communication
    failed for a reason that does not establish incorrect storage.
```

The logical check output contains:

```text
outcome: string ("pass", "fail", or "inconclusive")
leaseId: bytes (exactly 32 bytes)
offset:  uint64
value:   bytes (exactly 1 byte, optional unless evidence was returned)
```

The requester computes `outcome`; it must not trust a provider-supplied claim
that its own evidence passed.

### Cost and frequency

Every version 1 Storage offering contains `checkPrice`. Each check selects a
current compatible offering and uses that offering's current `creditIssuer`,
`checkPrice`, and `checkResponseSeconds`. The requester must see and accept the
price before the challenge begins. Storage checks are not included in the
original store price.

If no compatible offering is current, the check cannot be started. If an
offering disappears after a check price was accepted, that accepted check still
uses the agreed price; the change affects only later checks.

A check that returns a valid `pass`, `fail`, or `inconclusive` result may be
charged according to the common check rules. Authentication failures, invalid
offsets, malformed requests, and failures that produce no valid check result
must not be charged.

Providers may reject overlapping checks for the same lease and may enforce a
minimum interval of one second between accepted checks. They must not impose an
undisclosed lower frequency limit.

### What the check proves

One passing byte challenge shows only that the provider returned the correct
byte for one offset at one time. It does not prove that every other byte is
present, that the complete object was continuously retained, that the provider
uses a particular physical medium, or that future retrieval will succeed.

If a provider has lost a fraction `f` of independently distributed byte
positions, `n` independently uniform byte challenges detect at least one lost
position with ideal probability:

```text
1 - (1 - f)^n
```

Real loss patterns and requester sampling may not be independent. Applications
requiring stronger assurance should use multiple challenges, full or partial
paid retrievals, several independent providers, or a future proof-of-storage
service. A provider may legitimately reconstruct or fetch a byte from its own
storage layers; the check tests timely availability, not storage architecture.

---

## 11. Expiration and time

The provider's clock determines `acceptedAt`, renewal acceptance, and whether a
lease has expired. The requester should compare returned times with its own
clock and reject a lease result when the apparent clock difference is
unacceptable to its local policy.

The provider must use a wall clock intended to track UTC and must not shorten an
active lease because of a backward or forward local clock adjustment. In
practice, an implementation should persist a deadline and ensure that observed
remaining retention never decreases faster than real elapsed time solely due
to clock correction.

At `expiresAt`, the availability obligation ends. The provider may delete the
bytes immediately or retain them internally. Retention after expiration does
not reactivate the lease and must not make later operations succeed as if it
were active.

CR2SE does not promise retrieval after expiration and does not define a grace
period. Requesters should renew or retrieve sufficiently early to tolerate
network failure and clock uncertainty.

---

## 12. Encryption and confidentiality

Storage encryption is optional. The provider stores exactly the bytes supplied
by the requester and neither encrypts nor decrypts them as part of this service.

When confidentiality is required, the requester should encrypt and authenticate
the data before `store`, using the facilities in [Encryption](./Encryption.md)
or another suitable format. In that case:

```text
plaintext -> requester encryption -> stored bytes
```

`sizeBytes`, `contentHash`, offsets, and all prices refer to the resulting
stored bytes, including any nonce, header, authentication tag, or other
encryption-format overhead included in them. The requester must retain the
decryption key and any required metadata. The provider is not responsible for
key recovery, and an encrypted object whose key is lost remains a correctly
stored but unusable object.

Keys must not be sent to a storage provider merely to use this service. A fresh
random nonce or encryption context must be used as required by the chosen
encryption format. Encryption without integrity protection is not recommended.

Plaintext storage is conforming. It may be appropriate on a protected network,
between trusted identities, or for public data. A partial CR2SE implementation
may implement Storage without implementing requester-side encryption, provided
it does not claim that stored plaintext is confidential.

Encryption hides content when used correctly; it does not hide the requester
and provider identities, stored length, lease times, access frequency, check
offsets, or traffic timing from the provider.

---

## 13. Required service definition

Every version 1 Storage offering must expose a service definition through
`service.get`. Its `id` and `description` match that particular Board offering.
Its logical schema is equivalent to the following. Because the version 1 schema
language has no union type, fields used by only some operations are marked
optional; the operation-specific rules in this document determine which fields
are required or forbidden.

```json
{
  "id": "storage-standard",
  "service": "cr2se.storage",
  "serviceVersion": 1,
  "description": "Store requester-selected data for a requester-selected period.",
  "input": {
    "type": "object",
    "fields": {
      "operation": { "type": "string", "description": "Operation: store, retrieve, renew, or remove." },
      "leaseId": { "type": "bytes", "description": "Provider-generated 32-byte lease identifier; omitted for store.", "optional": true },
      "sizeBytes": { "type": "uint64", "description": "Exact number of bytes in store data.", "optional": true },
      "retentionSeconds": { "type": "uint64", "description": "Requested initial retention in whole seconds.", "optional": true },
      "contentHash": { "type": "bytes", "description": "SHA-256 hash of the complete stored byte sequence.", "optional": true },
      "data": { "type": "bytes", "description": "Store data, streamed when necessary.", "optional": true },
      "offset": { "type": "uint64", "description": "Zero-based first byte offset for retrieval.", "optional": true },
      "length": { "type": "uint64", "description": "Number of bytes requested for retrieval.", "optional": true },
      "expectedExpiresAt": { "type": "uint64", "description": "Current lease expiration expected by a renewal requester.", "optional": true },
      "additionalSeconds": { "type": "uint64", "description": "Whole seconds requested by renewal.", "optional": true }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "operation": { "type": "string", "description": "Completed operation: store, retrieve, renew, or remove." },
      "leaseId": { "type": "bytes", "description": "Provider-generated 32-byte lease identifier." },
      "sizeBytes": { "type": "uint64", "description": "Complete stored-object size in bytes.", "optional": true },
      "contentHash": { "type": "bytes", "description": "SHA-256 hash of the complete stored byte sequence.", "optional": true },
      "acceptedAt": { "type": "uint64", "description": "Provider lease-acceptance time in Unix seconds.", "optional": true },
      "previousExpiresAt": { "type": "uint64", "description": "Expiration time immediately before a successful renewal.", "optional": true },
      "expiresAt": { "type": "uint64", "description": "Current lease expiration time in Unix seconds.", "optional": true },
      "offset": { "type": "uint64", "description": "Zero-based offset of returned retrieval data.", "optional": true },
      "data": { "type": "bytes", "description": "Exact bytes returned by retrieval.", "optional": true },
      "price": { "type": "uint64", "description": "Credits charged for the successful operation.", "optional": true },
      "removed": { "type": "bool", "description": "True when the lease was ended successfully.", "optional": true }
    }
  },
  "check": {
    "description": "Challenge an active lease for the byte at one requester-selected offset and compare it locally with the original byte.",
    "input": {
      "type": "object",
      "fields": {
        "leaseId": { "type": "bytes", "description": "Provider-generated 32-byte active lease identifier." },
        "offset": { "type": "uint64", "description": "Zero-based offset of the challenged byte." }
      }
    },
    "output": {
      "type": "object",
      "fields": {
        "outcome": { "type": "string", "description": "Requester-computed result: pass, fail, or inconclusive." },
        "leaseId": { "type": "bytes", "description": "Lease identifier that was checked." },
        "offset": { "type": "uint64", "description": "Zero-based offset that was checked." },
        "value": { "type": "bytes", "description": "One-byte provider evidence when evidence was returned.", "optional": true }
      }
    }
  }
}
```

The operation discriminant selects these exact known fields:

```text
store
    requires operation, sizeBytes, retentionSeconds, contentHash, data

retrieve
    requires operation, leaseId, offset, length

renew
    requires operation, leaseId, expectedExpiresAt, additionalSeconds

remove
    requires operation, leaseId
```

A known field listed for another operation must be rejected. An unknown object
field follows the compatible-extension rule in `Services.md` and is not rejected
solely because it is unknown.

An implementation may expose language-appropriate functions or streaming APIs
instead of this JSON shape. It must preserve the same logical fields, exact
integer ranges, byte sequences, validation rules, pricing, and observable
behavior.

---

## 14. Concurrency and idempotency

Operations on one lease must be serialized where their effects conflict.

```text
renew versus renew
    Only one renewal with the same expectedExpiresAt may succeed.

renew versus remove
    Exactly one ordering is applied; the response to each operation must reflect
    that ordering.

retrieve/check versus remove/expiration
    An operation accepted while active completes under its acceptance-time rule.
    A later operation sees the new inactive state.
```

A failed or interrupted `store` may have transferred all data without creating
a lease. Retrying it creates a new attempt and may create a different lease ID.
Applications that require deduplication may compare content hashes locally, but
providers are not required to deduplicate.

Retrieve and check are read-only and may be repeated. Renewal uses
`expectedExpiresAt` as its replay guard. Remove is not guaranteed to return the
same success response after its first successful application.

---

## 15. Failure behavior

No successful output is returned for conditions including:

```text
unsupported service or pricing version;
malformed fields or wrong fixed byte lengths;
unknown operation name;
operation-specific required field missing;
field present where the selected operation forbids it;
value outside advertised limits;
price overflow or price disagreement;
insufficient accepted credits;
failed requester authentication;
unknown, expired, or removed lease;
requester identity not owning the lease;
incomplete upload or output transfer;
store content-hash mismatch;
invalid retrieval range;
stale expectedExpiresAt;
renewal beyond the selected current offering's total-retention limit;
provider inability to commit a new store durably.
```

Errors exposed across an unauthenticated boundary must not distinguish an
unknown lease from a lease owned by another identity.

The provider may reject any not-yet-accepted operation because of capacity,
trust, local policy, current offering terms, or price disagreement. Rejection
does not alter an existing lease and must not be charged. Once a particular
operation and price are accepted, the provider must either complete that
operation as specified or return an uncharged failure.

CR2SE has no global adjudicator. Missing data, incorrect data, premature expiry,
or refusal of a valid lease operation may inform the requester's local trust
decision but does not automatically refund or reverse credits.

---

## 16. Availability, redundancy, and security considerations

### Implementation safety

Storage providers process untrusted lengths, offsets, hashes, schemas, and byte
streams. They must validate declared sizes before allocation, use overflow-safe
range checks, limit concurrency, bound temporary storage, and discard incomplete
uploads safely.

### Availability and redundancy

Requesters must assume that individual peers may be intermittently offline,
change prices, withdraw offerings, lose hardware, or behave dishonestly. They
should not keep the only recoverable copy of irreplaceable data at one provider.

A requester should create independent leases at enough unrelated identities for
its risk model. Selecting peers in different time zones and network environments
reduces correlated offline periods. Combining ordinary domestic peers with
identities that exhibit server-like availability can increase the probability
that at least one affordable copy is reachable. This can approach cloud-like
availability by aggregation, but CR2SE does not guarantee that any chosen
replica count will achieve a particular uptime.

Requesters should retain content hashes and encryption keys independently,
check different replicas periodically, renew before the final moment, and avoid
allowing all replicas to expire together. A peer that becomes unavailable,
raises prices excessively, refuses reasonable operations, or returns incorrect
data may receive lower local trust and be excluded from later placement. Trust
is local and redundancy is the recovery mechanism; neither automatically
refunds an earlier payment.

### Content security

Content hashes provide integrity comparison and content identity. SHA-256 is not
authorization and does not make low-entropy plaintext confidential. A party can
guess a small or predictable plaintext and compare its hash.

The provider learns at least the access metadata described in section 12 and
may retain received bytes after logical removal or expiration. Requesters whose
threat model does not permit that must encrypt before upload and manage their
keys accordingly.

Implementations must not log encryption keys, plaintext supplied only to a
local encryption layer, entire stored objects, or authentication secrets merely
for protocol debugging.

---

## 17. Interoperability checklist

A version 1 implementation is interoperable only if it:

```text
uses service cr2se.storage version 1;
parses the cr2se.storage.v1 pricing model;
uses exact rational, ceiling, overflow-safe price arithmetic;
agrees each charged price before large transfer or execution;
stores and returns the exact logical byte sequence;
uses SHA-256 over exactly those bytes;
uses 32-byte unpredictable lease IDs;
binds every lease to the authenticated requester identity;
starts retention only after complete durable acceptance;
uses the defined Unix-second and expiration rules;
uses a current compatible offering and newly agreed price for every later
retrieve, renew, remove, or check operation;
supports paid range retrieval, bounded renewal, removal, and byte checks;
does not charge failed store, retrieve, renew, or remove operations;
does not require storage encryption;
does not claim plaintext confidentiality;
preserves behavior across connections and ordinary restart.
```
