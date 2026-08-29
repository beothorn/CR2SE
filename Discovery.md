# CR2SE Discovery

CR2SE Discovery is a standard, paid service for learning where identities may
be reached, which identities may host a public share, and what trust values
other identities have chosen to publish.

A **discovery record** is a signed, expiring statement that can be copied
between peers. A **current discovery record** is a valid record whose issue and
expiration times satisfy the rules in section 8 at the time it is used. A
**discovery index** is one peer's local collection of discovery
records and identities learned from authenticated connections. An **indexer** is
an identity that provides the Discovery service using such an index. A
**candidate** is an identity or address returned by an indexer. A candidate is
untrusted information to investigate; it is not proof that a connection or
service will succeed.

Discovery answers questions such as:

```text
What is the newest published address for this identity?
Which identities claim to host this share?
Which other indexers may know more about this identity or share?
Which identities does this indexer know?
Which published trust statements does this indexer know?
```

Discovery does not create a global directory, global trust score, global
membership list, or guarantee of reachability. Every answer describes the
queried indexer's current local knowledge. Signed records establish who made a
statement, but not whether the statement is true.

Common terms such as **identity**, **CR2SE ID**, **service requester**,
**service provider**, **offering**, **credit issuer**, **credit**, **trust
score**, and **check** are defined in the [CR2SE Glossary](./Glossary.md).
Identity keys and proof are defined in [Identity](./Identity.md), common service
and charging rules in [Services](./Services.md), credit and trust semantics in
[Ledger](./Ledger.md), Boards in [Board](./Board.md), and public shares in
[Public File Sharing](./PublicFileSharing.md).

---

## 1. Version 1 service

The version 1 Discovery service is identified by:

```text
service:        cr2se.discovery
serviceVersion: 1
pricing model:  cr2se.discovery.v1
```

It supports these operations:

```text
index
    Retain one or more valid signed discovery records for a bounded period.

resolveIdentity
    Return current address records for one identity and candidate indexers.

locateShare
    Return current availability records for one public share and candidate
    indexers.

findTrust
    Return current published trust records about one identity and candidate
    indexers.

listIdentities
    Return one page of identity IDs known to the provider.

listTrust
    Return one page of current trust records known to the provider.
```

Every operation acts on the provider's local state. A provider does not forward
the request, spend the requester's credits at another peer, or promise that its
answer is complete outside its own index.

All operations are paid service invocations, including an empty lookup or an
empty page. Invalid input and pre-acceptance refusal are not charged. All sizes
are byte counts, all times are whole Unix seconds, and all integer arithmetic
must be checked for overflow.

---

## 2. Records, statements, and evidence

A discovery record has four properties:

```text
the statement has one precisely defined binary representation;
the statement names the identity that made it;
that identity signs the representation with Ed25519;
the statement expires at a time chosen by its signer.
```

Version 1 defines three record types:

```text
address record
    An identity publishes network endpoints for nodes operating as that
    identity.

share record
    A host publishes whether it currently claims to host one Public File
    Sharing share.

trust record
    An evaluator publishes its local trust score for one subject identity.
```

The **signer** is the identity whose public key verifies a record's signature.
The **sequence number** is a signer-controlled `uint64` used to supersede an
older record of the same kind. The **issue time** is the signer's claimed Unix
time when it created the record. The **expiration time** is the signer's
claimed Unix time after which the record must not be returned as current.

For each independently sequenced record key, a signer must persist the greatest
`(sequence, issuedAt)` pair it has published and use a lexicographically greater
pair for a replacement. Neither component may wrap. Reusing an equal pair for
different content is equivocation, even when the deterministic lookup rules can
expose both records.

A signature proves only that the signer created the exact bytes. It does not
prove that an endpoint is reachable, a share is available, or a published trust
score is wise. Those properties require connection authentication, a Public
File Sharing invocation, or the requester's own local judgment.

---

## 3. Canonical binary helpers

Discovery records use the following language-independent encodings:

```text
u8(x)
    x as exactly one unsigned byte.

u16be(x)
    x as exactly two unsigned bytes in network byte order.

u32be(x)
    x as exactly four unsigned bytes in network byte order.

u64be(x)
    x as exactly eight unsigned bytes in network byte order.

bytes32(x)
    exactly 32 bytes, with no length prefix.

sized(x)
    u32be(length of x), followed by the exact bytes of x.

ASCII("text")
    the displayed ASCII bytes, without a length prefix or terminating zero.
```

Concatenation is written `||`. Unsigned lexicographic byte order compares the
first differing byte as an integer in `0 .. 255`; when one byte string is a
prefix of the other, the shorter string sorts first.

Every record ends in exactly one 64-byte Ed25519 signature. Its signing bytes
begin with a different ASCII domain separator for each record type. Therefore
a signature for one record type cannot be interpreted as a signature for
another record type.

The **record ID** is:

```text
SHA-256(exact signing bytes)
```

It is a 32-byte content identifier for the signed statement. It does not
include the signature. An implementation may expose a record as structured
fields, a byte string, or a language-native value, but it must reconstruct and
verify these exact signing bytes.

---

## 4. Network endpoints

A **network endpoint** describes one place at which a TCP connection may be
attempted. It contains an address kind, address bytes, and a port.

The address kinds are:

```text
0x00    IPv4
0x01    IPv6
0x02    DNS name
```

For IPv4, the address is exactly the four network-order address bytes. For
IPv6, it is exactly the sixteen network-order address bytes. Textual IP
spellings are presentation only and never appear in a signed record.

A DNS address is the lowercase ASCII form of a domain name without a trailing
dot. Each label contains 1 through 63 bytes, the complete name contains 1
through 253 bytes, labels are separated by `0x2e`, and every label contains
only `a` through `z`, `0` through `9`, and hyphen. A label must not begin or end
with hyphen. An internationalized name must be converted to its ASCII A-label
form before a record is constructed. DNS resolution and validation remain
local implementation concerns.

The port is a `uint16` in `1 .. 65535`. Version 1 endpoints always use TCP, so
no transport field is included.

The canonical endpoint bytes are:

```text
u8(addressKind)
|| u16be(address length)
|| address bytes
|| u16be(port)
```

Endpoints in one address record are sorted by unsigned lexicographic order of
these canonical bytes. Duplicates are invalid. This order makes the signature
independent of a programming language's collection order.

An advertised endpoint is not authenticated merely because it appears in a
valid record. After connecting, the remote peer must prove control of the
expected identity. An address must never replace identity authentication.

---

## 5. Address records

An **address record** is an identity's signed statement that nodes operating as
that identity may be reachable at a set of endpoints.

Its logical fields are:

```text
identityId:  bytes, exactly 32 bytes
publicKey:   bytes, exactly 32 bytes
sequence:    uint64
issuedAt:    uint64 Unix seconds
expiresAt:   uint64 Unix seconds
endpoints:   array of one or more network endpoints
signature:   bytes, exactly 64 bytes
```

The address signing bytes are exactly:

```text
ASCII("CR2SE-DISCOVERY-ADDRESS-V1")
|| identityId
|| publicKey
|| u64be(sequence)
|| u64be(issuedAt)
|| u64be(expiresAt)
|| u16be(endpoint count)
|| canonical endpoint 0
|| canonical endpoint 1
|| ...
```

The complete encoded address record is the signing bytes followed by the
64-byte signature. Before accepting or using it, an implementation must:

1. require the endpoint count to be in `1 .. 65535` and within local and
   offering limits;
2. validate every endpoint and their canonical order;
3. derive the CR2SE ID from `publicKey` and require it to equal `identityId`;
4. require `issuedAt < expiresAt`;
5. verify the signature over the exact signing bytes.

One sequence number covers the complete endpoint set. Publishing a replacement
therefore replaces the set rather than adding one endpoint. Multiple nodes
using one identity must coordinate sequence numbers and the combined endpoint
set as part of their shared identity responsibility.

For one identity, a record with a greater sequence number supersedes a record
with a smaller sequence number. If valid records have the same greatest
sequence number, the record with the greatest `issuedAt` supersedes an earlier
one. If both values tie but record IDs differ, the signer has equivocated. An
indexer retains and returns all tied records, ordered by record ID, so the
requester can detect the conflict. It must not silently select one as
authoritative.

The newest unexpired non-conflicting record is what Discovery means by the
identity's **latest address record**. The requester should try its endpoints in
a locally chosen order and authenticate the identity after connecting.

### Address-record test vector

This vector uses the following Ed25519 test seed and public key. The private
seed is published only to make the signature reproducible and must never be
used by a real identity.

```text
private seed
9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60

publicKey
d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a

identityId = SHA-256(0x01 || 0x01 || publicKey)
c15712089820d9be130963d9c25b411f8801a3d62ab7d5f547437e21e6fbbedb
```

The address record fields are:

```text
sequence  = 1
issuedAt  = 1700000000
expiresAt = 1700003600
endpoint  = IPv4 192.0.2.1, TCP port 8042
```

The canonical endpoint bytes are:

```text
000004c00002011f6a
```

The complete signing bytes are:

```text
43523253452d444953434f564552592d414444524553532d5631c15712089820d9be130963d9c25b411f8801a3d62ab7d5f547437e21e6fbbedbd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a0000000000000001000000006553f100000000006553ff100001000004c00002011f6a
```

The expected record ID and Ed25519 signature are:

```text
recordId
f1859799121c80026148fbd2f6583d296fc5d6591ed24af3ff1759bc30873484

signature
5b46a3751f31c4e49b73cf9ea94ebee18670bc45831a61d8867073a3278b011e264e590156143cdff434a01107ea7b0deea2a1aed3c0182ca33dedce14fac506
```

The complete encoded record is the displayed signing bytes immediately
followed by the displayed signature.

---

## 6. Share records

A **share record** is a host's signed availability statement about one share
defined by Public File Sharing. The **host** is the identity in `hostId`. The
`shareId` is the 32-byte SHA-256 hash of that share's canonical manifest.

Its logical fields are:

```text
hostId:     bytes, exactly 32 bytes
publicKey:  bytes, exactly 32 bytes
shareId:    bytes, exactly 32 bytes
sequence:   uint64
issuedAt:   uint64 Unix seconds
expiresAt:  uint64 Unix seconds
available:  bool
signature:  bytes, exactly 64 bytes
```

The share signing bytes are exactly:

```text
ASCII("CR2SE-DISCOVERY-SHARE-V1")
|| hostId
|| publicKey
|| shareId
|| u64be(sequence)
|| u64be(issuedAt)
|| u64be(expiresAt)
|| u8(available ? 1 : 0)
```

No other byte is valid for the boolean. The complete encoded share record is
the signing bytes followed by the 64-byte signature.

Before accepting or using it, an implementation derives the CR2SE ID from the
public key, checks all fixed lengths, requires `issuedAt < expiresAt`, and
verifies the signature. Sequence numbers are compared independently for each
pair `(hostId, shareId)` using the supersession and equivocation rules from
section 5.

An unexpired latest record with `available = true` is a current availability
claim. A latest record with `available = false` withdraws the claim before the
older record would expire. A host that stops serving a share should publish a
withdrawal to the same indexers, but requesters must tolerate stale positive
claims until expiration.

A valid positive record proves that the host made the claim. It does not prove
possession. The host confirms availability only by accepting the Public File
Sharing request, and the returned manifest and pieces prove their own content
through hashes.

---

## 7. Trust records

A **trust record** is one evaluator's signed publication of its local trust
score for one subject identity. The **evaluator** owns the score. The
**subject** is the identity being evaluated.

The Ledger represents trust conceptually from zero through one. Discovery uses
an integer scale so every language signs the same bytes:

```text
0             means 0.000000000 trust
1000000000    means 1.000000000 trust
```

Intermediate values are exact billionths. A native floating-point ledger value
must be converted by explicit local policy; it must not be reinterpreted from
its in-memory bytes.

The logical fields are:

```text
evaluatorId: bytes, exactly 32 bytes
publicKey:   bytes, exactly 32 bytes
subjectId:   bytes, exactly 32 bytes
sequence:    uint64
issuedAt:    uint64 Unix seconds
expiresAt:   uint64 Unix seconds
score:       uint32 in 0 .. 1000000000
signature:   bytes, exactly 64 bytes
```

The trust signing bytes are exactly:

```text
ASCII("CR2SE-DISCOVERY-TRUST-V1")
|| evaluatorId
|| publicKey
|| subjectId
|| u64be(sequence)
|| u64be(issuedAt)
|| u64be(expiresAt)
|| u32be(score)
```

The complete encoded trust record is the signing bytes followed by the 64-byte
signature. Before accepting or using it, an implementation derives the
evaluator ID from the public key, checks the score and times, and verifies the
signature. Sequence numbers are compared independently for each pair
`(evaluatorId, subjectId)`.

Publishing trust is optional. Absence of a trust record says nothing about the
evaluator's private score. A published zero may describe an identity the
evaluator knows and distrusts; it is different from no statement.

A requester must not copy a published score directly into its own ledger merely
because the signature is valid. It may ignore the statement or combine it with
its local relationship to the evaluator and other evidence. There is no
authoritative aggregation formula.

---

## 8. Time, expiration, and current records

Unix time is the number of elapsed seconds since 1970-01-01T00:00:00Z,
excluding leap seconds. A record is **current** at local time `now` only when:

```text
issuedAt <= now + maximumClockSkewSeconds
expiresAt > now
expiresAt - issuedAt <= maximumRecordLifetimeSeconds
```

The first addition and final subtraction must be overflow-checked.
`maximumClockSkewSeconds` and `maximumRecordLifetimeSeconds` come from the
selected offering. A provider applies them when accepting a record for
indexing. A requester applies limits no weaker than those in the offering it
selected and may apply stricter local limits.

An indexer must not return an expired record as current. It may retain expired
bytes locally for history, equivocation detection, or abuse investigation, but
such bytes are not successful lookup results.

Expiration bounds stale claims; it does not synchronize clocks. Implementations
should use a reliable clock and allow only the advertised bounded skew. A
requester may reject a record earlier than required by its own security policy.

---

## 9. Index placements

An **index placement** is one provider's paid commitment to retain exact
discovery-record bytes. It is created by `index` and is separate from the
provider's uncommitted cache.

An index placement records at least:

```text
indexId
record ID and exact record bytes
requester identity
provider identity
acceptedAt
storedUntil
offering ID, credit issuer, and price
```

`indexId` is a provider-generated cryptographically random 32-byte value. The
**storage end time** `storedUntil` is:

```text
minimum(record.expiresAt,
        acceptedAt + maximumIndexRetentionSeconds)
```

The addition must be overflow-checked. The provider must retain the exact bytes
through `storedUntil`, even if a newer record supersedes them for lookup
purposes. It may retain indexed bytes longer, but an expired record is never
current.

Indexing the same record at several providers creates independent placements.
Indexing an already known record again may create another paid placement; the
provider may deduplicate storage internally but must preserve every accepted
commitment and check.

---

## 10. Discovery keys and distance

A **discovery key** is the 32-byte value used to place and search for related
records. Version 1 defines:

```text
identityKey(identityId) = identityId

shareKey(shareId) =
    SHA-256(ASCII("CR2SE-DISCOVERY-SHARE-KEY-V1") || shareId)

trustKey(subjectId) =
    SHA-256(ASCII("CR2SE-DISCOVERY-TRUST-KEY-V1") || subjectId)
```

An indexer's **node key** is its 32-byte CR2SE ID. The **XOR distance** between
two 32-byte values is their bitwise exclusive-or result interpreted as one
unsigned 256-bit big-endian integer. A smaller integer is a shorter distance.

Candidates for one discovery key are ordered by increasing XOR distance from
their node keys. Equal distances cannot occur for different node keys. This
metric is derived from Kademlia, a distributed hash table design in which
participants iteratively ask known nodes for nodes closer to a key.

CR2SE does not require Kademlia buckets, fixed replication counts, background
traffic, or free routing messages. The exact local routing table, cache,
parallelism, and eviction algorithm are implementation choices. The key and
distance definitions are normative so independently written peers rank the
same returned candidates identically.

---

## 11. Candidate indexers

A **candidate indexer entry** contains:

```text
identityId:    bytes, exactly 32 bytes
addressRecord: bytes containing one current valid address record
```

The identity ID must equal the signer and subject of the address record. The
provider returns only identities it currently believes advertise a compatible
Discovery offering. That belief is a hint, not signed evidence; the requester
must connect, authenticate the identity, retrieve its current Board, and select
an offering before invocation.

Candidate entries are sorted by XOR distance from the lookup's discovery key,
then by record ID when equivocation produces more than one address record for
one identity. Duplicate `(identityId, recordId)` pairs are forbidden.

The provider may return candidates farther from the key than itself. This lets
a requester escape incomplete local routing tables. The requester, not the
provider, decides which candidate to query next.

---

## 12. Pricing and Board offering

Every price is an integer number of credits and is at least one. The pricing
fields are:

```text
indexBasePrice
    Base price of one successful index invocation.

indexRecordPrice
    Additional price for every record in that invocation.

resolveIdentityPrice
    Exact price of one successful resolveIdentity invocation.

locateSharePrice
    Exact price of one successful locateShare invocation.

findTrustPrice
    Exact price of one successful findTrust invocation.

listIdentitiesPrice
    Exact price of one successful listIdentities invocation.

listTrustPrice
    Exact price of one successful listTrust invocation.
```

For `R` indexed records:

```text
indexPrice = indexBasePrice + R * indexRecordPrice
```

The calculation must use arbitrary-precision arithmetic or an equivalent
overflow-safe method and fit in `uint64`. Lookup and listing prices do not
depend on how many results happen to exist. An empty successful answer costs
the advertised operation price.

The offering `info` fields are:

```text
maximumIndexRecords
    Largest record count accepted by one index operation. Range: 1 .. 2^32-1.

maximumIndexBytes
    Largest sum of encoded record lengths accepted by one index operation.
    Range: 1 .. 2^64-1.

maximumIndexRetentionSeconds
    Longest placement commitment created by index. Range: 1 .. 2^64-1.

maximumRecordLifetimeSeconds
    Longest accepted expiresAt minus issuedAt. Range: 1 .. 2^64-1.

maximumClockSkewSeconds
    Greatest accepted amount by which issuedAt may be ahead of provider time.
    Range: 0 .. 2^64-1.

maximumEndpointsPerRecord
    Largest endpoint count accepted or returned in one address record.
    Range: 1 .. 65535.

maximumLookupResults
    Largest requested records or candidate indexers in one exact lookup.
    Range: 1 .. 2^32-1.

maximumListResults
    Largest requested page in a list operation. Range: 1 .. 2^32-1.

checkResponseSeconds
    Maximum requester-observed time for an index-placement check response.
    Range: 1 .. 2^64-1.
```

A complete offering has this shape:

```json
{
  "id": "discovery-standard",
  "service": "cr2se.discovery",
  "serviceVersion": 1,
  "description": "Index and query signed, expiring identity address, public-share availability, and published trust records.",
  "creditIssuer": "PROVIDER_ID",
  "pricing": {
    "model": "cr2se.discovery.v1",
    "indexBasePrice": 1,
    "indexRecordPrice": 1,
    "resolveIdentityPrice": 1,
    "locateSharePrice": 1,
    "findTrustPrice": 1,
    "listIdentitiesPrice": 2,
    "listTrustPrice": 2
  },
  "info": {
    "maximumIndexRecords": 100,
    "maximumIndexBytes": 1048576,
    "maximumIndexRetentionSeconds": 604800,
    "maximumRecordLifetimeSeconds": 2592000,
    "maximumClockSkewSeconds": 300,
    "maximumEndpointsPerRecord": 16,
    "maximumLookupResults": 100,
    "maximumListResults": 1000,
    "checkResponseSeconds": 30
  },
  "preconditions": [
    "cr2se.identity"
  ]
}
```

The numbers are illustrative. Every version 1 offering must contain all shown
pricing and `info` fields, must use `pricing` rather than the Board fixed
`price` field, and must contain the `cr2se.identity` precondition.

The exact price and credit issuer are agreed before execution. A provider may
reject before acceptance because of trust, credit, capacity, privacy, or local
policy. A successful empty query is still charged because the provider has
performed the bounded index lookup and returned its answer.

---

## 13. Index operation

The logical input is:

```text
operation: "index"
records:   array of encoded discovery-record byte strings
```

The array must contain `1 .. maximumIndexRecords` records. The sum of the byte
lengths must not exceed `maximumIndexBytes`. Record IDs within the array must be
unique. Each record must be a canonical address, share, or trust record that is
current under the selected offering.

The operation is atomic. The provider validates every record and calculates
every `storedUntil` before acceptance. It either accepts all placements or
rejects the invocation without charging and without creating any placement.

On successful durable acceptance it returns:

```text
operation:  "index"
acceptedAt: uint64 Unix seconds
placements: array of placement entries
price:      uint64 credits
```

Each placement entry contains:

```text
indexId:    bytes, exactly 32 bytes
recordId:   bytes, exactly 32 bytes
storedUntil: uint64 Unix seconds
```

Entries appear in the same order as the submitted records. The provider must
not report success until the exact records and placement metadata are durably
stored in storage intended to survive an ordinary process restart or machine
reboot.

Any authenticated requester may pay to index a valid record signed by another
identity. This permits records to be copied toward indexers close to their
discovery key without giving the copier authority to alter them.

---

## 14. Resolve identity operation

`resolveIdentity` asks for the latest current address record of one identity.
Its input is:

```text
operation:    "resolveIdentity"
identityId:   bytes, exactly 32 bytes
recordLimit:  uint32
indexerLimit: uint32
```

Both limits must be in `1 .. maximumLookupResults`. The discovery key is
`identityKey(identityId)`.

The output is:

```text
operation:      "resolveIdentity"
identityId:     bytes, exactly 32 bytes
addressRecords: array of encoded address records
indexers:       array of candidate indexer entries
price:          uint64 credits
```

`addressRecords` contains at most `recordLimit` current records for the exact
identity. It normally contains one latest record. It contains more than one
only to expose tied latest equivocations, and it never contains a superseded
record. Records are ordered as defined in section 5. If all tied latest records
do not fit within `recordLimit`, the provider rejects before acceptance with a
result-limit error rather than concealing the equivocation.

`indexers` contains at most `indexerLimit` entries ordered as defined in
section 11. An empty `addressRecords` array means only that this provider has no
current record matching the request.

---

## 15. Locate share operation

`locateShare` asks which identities currently claim to host one public share.
Its input is:

```text
operation:    "locateShare"
shareId:      bytes, exactly 32 bytes
recordLimit:  uint32
indexerLimit: uint32
```

Both limits must be in `1 .. maximumLookupResults`. The discovery key is
`shareKey(shareId)`.

The output is:

```text
operation:    "locateShare"
shareId:      bytes, exactly 32 bytes
shareRecords: array of encoded share records
indexers:     array of candidate indexer entries
price:        uint64 credits
```

The records contain the exact requested share ID and are current latest records
for their respective hosts. A host with one latest positive record is a host
candidate. A host with one latest negative record is omitted. When tied latest
records for one host conflict and at least one is positive, the provider returns
all tied records, including any negative record, so the equivocation remains
visible; the requester must not treat that host as an unambiguous candidate.

Complete host groups are ordered by increasing XOR distance between `hostId`
and `shareKey(shareId)`, then by `hostId`; tied records inside a group are
ordered by record ID. The provider returns as many complete groups as fit in
`recordLimit`. If the first group alone does not fit, it rejects before
acceptance with a result-limit error. The distance comparison deliberately
ranks hosts without depending on the provider's private opinion. A requester
may apply a different local ranking using address reachability, credits, trust,
price, or previous performance.

A result identifies the host identity, not its address. The requester resolves
that identity separately unless it already has a current address record. This
separation prevents an indexer from substituting an unsigned address into a
host's signed availability claim.

---

## 16. Find trust operation

`findTrust` asks for published trust statements whose subject is one identity.
Its input is:

```text
operation:    "findTrust"
subjectId:    bytes, exactly 32 bytes
recordLimit:  uint32
indexerLimit: uint32
```

Both limits must be in `1 .. maximumLookupResults`. The discovery key is
`trustKey(subjectId)`.

The output is:

```text
operation:    "findTrust"
subjectId:    bytes, exactly 32 bytes
trustRecords: array of encoded trust records
indexers:     array of candidate indexer entries
price:        uint64 credits
```

Each returned record has the exact subject ID and is the current latest record
for one evaluator-subject pair. Records are ordered by `evaluatorId`, then by
record ID when an equivocation is present. The provider returns only complete
evaluator groups; if the first tied group alone exceeds `recordLimit`, it
rejects before acceptance with a result-limit error. The provider does not
average or otherwise combine scores.

An empty result does not imply that the subject is trustworthy or untrustworthy.
It means only that the provider has no current published statements it can
return under the selected offering.

---

## 17. List identities operation

`listIdentities` lets a requester copy the set of identity IDs known to one
indexer. A **known identity** is an identity for which the provider currently
has at least one of:

```text
a current discovery record signed by that identity;
a current share or trust record naming it;
a current candidate-indexer entry;
a locally retained authenticated-connection observation.
```

The observation is provider-local metadata, not a transferable identity proof.

The input is:

```text
operation:       "listIdentities"
afterIdentityId: bytes, exactly 32 bytes, optional
limit:           uint32
```

`limit` must be in `1 .. maximumListResults`. Identity IDs are ordered by
unsigned lexicographic byte order. The optional cursor is exclusive.

The output is:

```text
operation:  "listIdentities"
identities: array of 32-byte identity IDs
more:       bool
price:      uint64 credits
```

With no cursor the provider returns the first page. With a cursor it returns
IDs strictly after that value. `more` is true only when another ID existed
immediately after the last returned ID when the page was produced.

The listing is not a frozen snapshot. Concurrent additions or removals may be
missed or observed on another pass. A requester that wants records for an ID
uses `resolveIdentity`, `findTrust`, or another relevant lookup after learning
it. An ID in this list does not prove that a live node exists.

---

## 18. List trust operation

`listTrust` lets a requester copy every current trust record the provider has
chosen to include in the selected Discovery offering. Within that advertised
index, the provider must not silently omit a record because its score is low,
high, favorable, or unfavorable.

The input is:

```text
operation:        "listTrust"
afterEvaluatorId: bytes, exactly 32 bytes, optional
afterSubjectId:   bytes, exactly 32 bytes, optional
afterRecordId:    bytes, exactly 32 bytes, optional
limit:            uint32
```

The three cursor fields must either all be absent or all be present. `limit`
must be in `1 .. maximumListResults`. Current latest records are ordered by
`evaluatorId`, then `subjectId`, then record ID. The cursor is exclusive on the
complete three-value tuple. It therefore permits tied equivocation records to
span pages without omission.

The output is:

```text
operation:    "listTrust"
trustRecords: array of encoded trust records
more:         bool
price:        uint64 credits
```

`more` has the same immediate-page meaning as in `listIdentities`. The listing
is not a snapshot. It is not “all trust in CR2SE”; it is all current published
trust records in this provider's disclosed index at the time each page is
constructed.

An operator that does not want to disclose a trust index must not advertise a
Discovery offering it cannot fulfill. It may keep private trust data outside
the disclosed discovery index and must never describe that private data as
part of the offering.

---

## 19. Public File Sharing catalog relationship

An indexer can learn a host's shares by invoking the Public File Sharing
`catalog` operation. That operation returns the host's current self-signed
positive share records in deterministic pages. The indexer verifies each
record before adding it to its local discovery index or paying another indexer
to retain it.

This relationship separates responsibilities:

```text
Public File Sharing catalog
    tells a connected peer which shares this host claims to serve.

Discovery locateShare
    tells a requester which host identities or other indexers may be worth
    contacting for one known share ID.

Public File Sharing manifest and download
    confirm availability and return hash-verifiable content.
```

Catalog enumeration is paid. It is never performed automatically merely
because a connection exists. A host may choose not to advertise a catalog; in
that case its shares can still be found through share records it explicitly
indexes elsewhere.

---

## 20. Iterative lookup

An **iterative lookup** is a requester-controlled sequence of direct Discovery
invocations. It begins with one or more **bootstrap contacts**, meaning identity
IDs and addresses obtained from configuration, a contact QR, a previous
connection, or another trusted local source.

For an identity, share, or trust lookup, the requester may:

1. calculate the corresponding discovery key;
2. place bootstrap indexers in a candidate set ordered by XOR distance;
3. choose a candidate for which it has a current address and usable service
   terms;
4. connect and authenticate that identity;
5. retrieve its Board and select a compatible Discovery offering;
6. invoke the exact lookup and verify every returned signed record;
7. add previously unseen candidate indexers to the ordered set;
8. stop when it has enough verified candidates, no useful unqueried candidate
   remains, or its local time or credit budget is exhausted.

Queries may be sequential or concurrently bounded. Implementations must avoid
unbounded fan-out. They should remember queried identity IDs, reject duplicate
records, cap candidate-set size, and prefer candidates learned from providers
they trust.

The requester pays each provider directly under that provider's offering. A
provider never receives one payment and silently spends it along a multi-hop
route. Consequently a requester may be unable to follow a referral because it
lacks credits accepted by the referred identity or because that identity has
zero trust in the requester. The lookup then continues with another usable
candidate or stops.

This is intentionally a paid, relationship-constrained adaptation of
Kademlia-style lookup. It makes large anonymous crawls expensive and makes
useful reachability grow through contribution and credit relationships rather
than through a free global routing substrate.

---

## 21. Bootstrap, credits, and tit for tat

Opening a connection, authenticating identities, and reading the remote Board
are protocol prerequisites. They do not themselves provide a Discovery result.
Every `cr2se.discovery` invocation costs at least one credit.

The provider applies the Ledger rules before accepting an invocation. In
particular:

```text
the requester must have nonzero trust at the provider;
the requester must possess enough credits of the agreed issuer;
the provider may still refuse because of capacity or local policy.
```

An unknown identity cannot demand a first lookup merely because Discovery is
important for network growth. It must first obtain a usable relationship, for
example by providing a wanted service, receiving or redeeming a credit claim,
or being configured by the operator as a known contact. The exact way it earns
credits is outside Discovery.

Likewise, a referral does not create credits at the referred peer. This is the
tit-for-tat boundary: useful information moves across direct economic
relationships, while each new direct peer independently decides whether to
interact.

Bootstrap contacts should be diverse and persist across restarts. A completely
new installation with no contact address, credit claim, configured
relationship, or previously known peer cannot discover the network from an
identity ID alone. No decentralized protocol can contact an unknown network
without some initial routing information.

---

## 22. Record replication and indexing policy

A record creator or crawler should index a record at several identities whose
node keys are close to the record's discovery key and with which it can
transact. Replication reduces dependence on one indexer. Version 1 does not
mandate a replication count because credit availability, trust, and network
size differ between identities.

An indexer may also build its uncommitted cache by:

```text
remembering verified records returned by paid Discovery queries;
enumerating a peer's Public File Sharing catalog;
enumerating another indexer's identities or published trust records;
creating and publishing its own address and trust records;
receiving records through paid index invocations.
```

Only an accepted index placement creates a retention obligation. Cached or
crawled information may be evicted at any time. A provider must not claim that
its list operations are network-wide or historically complete.

Providers should prefer current records, retain equivocation evidence, bound
storage per signer and per discovery key, and avoid letting one identity evict
all other records through cheap volume. These are local indexing policies;
they must not alter record validation or required output ordering.

---

## 23. Verification check

Discovery has a local check for lookup and list operations and one remote
retention check for an index placement. No separate `checkPrice` is used;
exactly one retention check per accepted placement is included in the original
index price until `storedUntil`.

For `resolveIdentity`, `locateShare`, `findTrust`, `listIdentities`, or
`listTrust`, the requester checks the complete output locally. The outcome is:

```text
pass
    Every returned record has the requested kind or key, valid canonical bytes,
    a valid identity derivation and signature, current times, valid ordering,
    and the advertised limits; every candidate entry is internally valid.

fail
    Complete output is available and at least one required property is false.

inconclusive
    Complete output or request metadata is unavailable, or local resource
    limits prevent validation.
```

This local check cannot prove completeness, current reachability, possession of
a share, honesty of a trust score, or continued availability after the answer.

For an `index` placement, the requester supplies its `indexId` and `recordId`.
Before `storedUntil`, the provider returns the exact retained record bytes. The
requester verifies the record ID and byte equality with the originally indexed
record. The outcome is:

```text
pass
    The complete bytes are returned within `checkResponseSeconds` and exactly
    match the accepted record.

fail
    The provider returns complete different bytes or validly reports that the
    accepted placement is absent before storedUntil.

inconclusive
    The response is missing, incomplete, late, or cannot be associated with
    the accepted placement.
```

The check proves possession only at the check time. It does not prove
continuous retention, lookup inclusion, truth of the signed statement, or
retention after `storedUntil`.

---

## 24. Required service definition

Every version 1 Discovery offering must expose a definition through
`service.get`. Its `id` and `description` match the selected Board offering.
Because the version 1 schema language has no union type, operation-specific
fields are optional in the shared schema; the operation rules make them
required or forbidden.

Its logical schema is equivalent to:

```json
{
  "id": "discovery-standard",
  "service": "cr2se.discovery",
  "serviceVersion": 1,
  "description": "Index and query signed, expiring identity address, public-share availability, and published trust records.",
  "input": {
    "type": "object",
    "fields": {
      "operation": { "type": "string", "description": "Operation: index, resolveIdentity, locateShare, findTrust, listIdentities, or listTrust." },
      "records": { "type": "array", "description": "Canonical encoded discovery records submitted for paid retention.", "items": { "type": "bytes" }, "optional": true },
      "identityId": { "type": "bytes", "description": "Exact 32-byte identity ID selected by resolveIdentity.", "optional": true },
      "shareId": { "type": "bytes", "description": "Exact 32-byte Public File Sharing share ID selected by locateShare.", "optional": true },
      "subjectId": { "type": "bytes", "description": "Exact 32-byte subject identity selected by findTrust.", "optional": true },
      "recordLimit": { "type": "uint32", "description": "Maximum signed records requested from an exact lookup.", "optional": true },
      "indexerLimit": { "type": "uint32", "description": "Maximum candidate indexers requested from an exact lookup.", "optional": true },
      "afterIdentityId": { "type": "bytes", "description": "Exclusive 32-byte identity cursor for listIdentities.", "optional": true },
      "afterEvaluatorId": { "type": "bytes", "description": "Exclusive evaluator part of a listTrust cursor.", "optional": true },
      "afterSubjectId": { "type": "bytes", "description": "Exclusive subject part of a listTrust cursor.", "optional": true },
      "afterRecordId": { "type": "bytes", "description": "Exclusive record-ID part of a listTrust cursor.", "optional": true },
      "limit": { "type": "uint32", "description": "Maximum entries requested from a list operation.", "optional": true }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "operation": { "type": "string", "description": "Completed Discovery operation." },
      "acceptedAt": { "type": "uint64", "description": "Provider acceptance time for an index operation.", "optional": true },
      "placements": { "type": "array", "description": "Index placements in submitted-record order.", "items": { "type": "object", "fields": {
        "indexId": { "type": "bytes", "description": "Provider-generated 32-byte index placement ID." },
        "recordId": { "type": "bytes", "description": "SHA-256 ID of the accepted discovery-record signing bytes." },
        "storedUntil": { "type": "uint64", "description": "End of the provider's paid record-retention commitment." }
      } }, "optional": true },
      "identityId": { "type": "bytes", "description": "Exact identity selected by resolveIdentity.", "optional": true },
      "shareId": { "type": "bytes", "description": "Exact share selected by locateShare.", "optional": true },
      "subjectId": { "type": "bytes", "description": "Exact trust subject selected by findTrust.", "optional": true },
      "addressRecords": { "type": "array", "description": "Current canonical encoded address records.", "items": { "type": "bytes" }, "optional": true },
      "shareRecords": { "type": "array", "description": "Current canonical encoded share records, including tied negative records needed to expose equivocation.", "items": { "type": "bytes" }, "optional": true },
      "trustRecords": { "type": "array", "description": "Current canonical encoded trust records.", "items": { "type": "bytes" }, "optional": true },
      "indexers": { "type": "array", "description": "Candidate indexers ordered by XOR distance from the lookup key.", "items": { "type": "object", "fields": {
        "identityId": { "type": "bytes", "description": "Exact 32-byte candidate indexer identity." },
        "addressRecord": { "type": "bytes", "description": "Current canonical address record signed by the candidate identity." }
      } }, "optional": true },
      "identities": { "type": "array", "description": "Known 32-byte identity IDs in unsigned lexicographic order.", "items": { "type": "bytes" }, "optional": true },
      "more": { "type": "bool", "description": "Whether another listing entry existed when the page was produced.", "optional": true },
      "price": { "type": "uint64", "description": "Credits charged for the successful operation." }
    }
  },
  "check": {
    "description": "Locally validate lookup or listing output, or retrieve the exact record bytes for one accepted index placement before its storage end time.",
    "input": {
      "type": "object",
      "fields": {
        "operation": { "type": "string", "description": "Checked Discovery operation." },
        "indexId": { "type": "bytes", "description": "Provider-generated 32-byte index placement ID for a retention check.", "optional": true },
        "recordId": { "type": "bytes", "description": "Expected 32-byte discovery record ID for a retention check.", "optional": true },
        "identityId": { "type": "bytes", "description": "Requested identity for a resolveIdentity check.", "optional": true },
        "shareId": { "type": "bytes", "description": "Requested share for a locateShare check.", "optional": true },
        "subjectId": { "type": "bytes", "description": "Requested trust subject for a findTrust check.", "optional": true },
        "recordLimit": { "type": "uint32", "description": "Original exact-lookup record limit.", "optional": true },
        "indexerLimit": { "type": "uint32", "description": "Original exact-lookup candidate-indexer limit.", "optional": true },
        "afterIdentityId": { "type": "bytes", "description": "Original listIdentities cursor when one was supplied.", "optional": true },
        "afterEvaluatorId": { "type": "bytes", "description": "Original evaluator part of a listTrust cursor.", "optional": true },
        "afterSubjectId": { "type": "bytes", "description": "Original subject part of a listTrust cursor.", "optional": true },
        "afterRecordId": { "type": "bytes", "description": "Original record-ID part of a listTrust cursor.", "optional": true },
        "limit": { "type": "uint32", "description": "Original list-operation page limit.", "optional": true },
        "addressRecords": { "type": "array", "description": "Complete address-record array returned by resolveIdentity.", "items": { "type": "bytes" }, "optional": true },
        "shareRecords": { "type": "array", "description": "Complete share-record array returned by locateShare.", "items": { "type": "bytes" }, "optional": true },
        "trustRecords": { "type": "array", "description": "Complete trust-record array returned by findTrust or listTrust.", "items": { "type": "bytes" }, "optional": true },
        "indexers": { "type": "array", "description": "Complete candidate-indexer array returned by an exact lookup.", "items": { "type": "object", "fields": {
          "identityId": { "type": "bytes", "description": "Exact 32-byte candidate indexer identity." },
          "addressRecord": { "type": "bytes", "description": "Current canonical address record signed by the candidate identity." }
        } }, "optional": true },
        "identities": { "type": "array", "description": "Complete identity-ID page returned by listIdentities.", "items": { "type": "bytes" }, "optional": true },
        "more": { "type": "bool", "description": "Returned listing continuation indicator.", "optional": true }
      }
    },
    "output": {
      "type": "object",
      "fields": {
        "outcome": { "type": "string", "description": "Requester-computed verification result: pass, fail, or inconclusive." },
        "record": { "type": "bytes", "description": "Exact retained discovery-record bytes returned for an index-placement check.", "optional": true }
      }
    }
  }
}
```

The operation discriminant selects these exact known input fields:

```text
index
    operation, records

resolveIdentity
    operation, identityId, recordLimit, indexerLimit

locateShare
    operation, shareId, recordLimit, indexerLimit

findTrust
    operation, subjectId, recordLimit, indexerLimit

listIdentities
    operation, limit, and optionally afterIdentityId

listTrust
    operation, limit, and either all three trust cursor fields or none
```

A known field belonging only to another operation must be rejected. Unknown
object fields follow the compatible-extension rule in `Services.md`.

For a retention check of `index`, the check input requires `operation`,
`indexId`, and `recordId`. A `resolveIdentity`, `locateShare`, or `findTrust`
check requires its original selector, both original limits, the returned record
array, and the returned indexer array. A `listIdentities` check requires its
optional original cursor, original limit, identities, and `more`. A `listTrust`
check requires either all three original cursor fields or none, plus the
original limit, trust records, and `more`. Fields belonging only to another
check are forbidden. The requester supplies these logical values directly,
regardless of its local programming representation.

An implementation may expose functions, iterators, streams, processes, or
language-native records rather than JSON. It must preserve the same logical
values, fixed byte lengths, canonical signing bytes, ordering, limits,
validation, pricing, retention, and observable success or failure behavior.

---

## 25. Failure behavior

No successful output is returned and no charge is permitted for conditions
including:

```text
unsupported service, service version, or pricing model;
unknown operation;
malformed field, record, cursor, endpoint, signature, or fixed-length value;
known operation-specific field missing or forbidden;
limit outside the selected offering;
invalid identity derivation or record signature;
record expired, issued too far in the future, or valid for too long;
duplicate or non-canonical record in an index request;
index count, byte sum, price, or retention arithmetic overflow;
provider inability to create every requested index placement atomically;
insufficient accepted credits;
failed identity precondition;
provider rejection by trust, privacy, capacity, or local policy;
connection interruption before complete successful output.
```

A lookup with no matching records is not a failure. It returns empty arrays and
is charged. A provider that accepted an index operation but did not durably
retain every record through its stated `storedUntil` has failed the service.

Malformed signed bytes are never useful evidence and must not be returned as
successful records. Error text and provider-supplied explanations are
untrusted.

---

## 26. Security and privacy

### False and stale claims

Signatures prevent an indexer from altering a record without detection. They do
not prevent a signer from lying, publishing unreachable endpoints, claiming a
share it does not possess, changing its mind, or equivocating. Expiration,
sequence numbers, redundant queries, authenticated connection attempts, and
service checks limit different parts of this risk; none establishes global
truth.

### Enumeration

`listIdentities`, `listTrust`, Public File Sharing `catalog`, and repeated exact
lookups reveal social and availability information. Providers must authenticate
requesters, charge every successful page, apply trust policy, bound page sizes,
rate-limit pre-acceptance failures, and may operate separate public and private
indexes.

The selected offering defines the disclosed index. A provider must not leak a
private identity, trust value, or record through error differences after
choosing not to include it.

### Routing attacks

A malicious indexer may omit records, return only colluding candidates, or try
to isolate a requester. Requesters should keep diverse bootstrap contacts,
query more than one independently chosen indexer, remember successful contacts,
cap repeated referrals from one source, and weight information using local
trust. XOR proximity is an ordering rule, not evidence of honesty.

Cheap identity creation also permits many node keys. Discovery does not treat
key proximity as trust and does not grant a new identity free queries.

### Resource limits

Implementations must parse records without trusting counts or lengths, check
arithmetic before allocation, cap signature work, cap concurrent connection
attempts, and bound index size per signer, subject, share, requester, and
network prefix. DNS resolution must be resource-bounded and must not bypass
local address policy.

### Network privacy

The queried provider learns the requester's authenticated identity, lookup key,
timing, selected limits, and payment relationship. A referred peer later learns
the next direct request. Transport encryption does not hide this metadata from
either provider. Version 1 provides no anonymity, private information retrieval,
onion routing, broadcast concealment, or query mixing.

---

## 27. Example: locating a public share

Alice already knows Bob's identity and address and owns credits Bob accepts.
She wants the share whose ID is `S`.

1. Alice connects to Bob, authenticates Bob, retrieves Bob's Board, and selects
   Bob's Discovery offering.
2. Alice pays for `locateShare(S)`. Bob returns Carol's signed positive share
   record and candidate indexers David and Ellen.
3. Alice verifies Carol's signature. The signature proves Carol made the claim,
   not that Carol still has the bytes.
4. Alice pays Bob for `resolveIdentity(Carol)` and receives Carol's signed
   address record.
5. Alice connects to Carol and authenticates Carol's identity.
6. Alice retrieves Carol's Board and verifies that she has enough accepted
   credits and nonzero trust for Carol's Public File Sharing offering.
7. Alice requests the manifest for `S`, verifies its SHA-256 hash, and downloads
   pieces under the Public File Sharing rules.

Alice need not query David or Ellen once Carol succeeds. If Carol is stale or
unreachable, Alice may query an indexer with which she can transact. A referral
to an indexer whose credits Alice cannot spend is not directly usable.

---

## 28. Interoperability checklist

A version 1 implementation is interoperable only if it:

```text
uses service cr2se.discovery at serviceVersion 1;
uses pricing model cr2se.discovery.v1 and charges every successful operation;
derives signer IDs from Ed25519 public keys before trusting signatures;
constructs the exact domain-separated canonical signing bytes;
uses SHA-256 of signing bytes as the record ID;
validates endpoint forms, order, counts, times, scores, and fixed lengths;
applies sequence, supersession, withdrawal, expiration, and equivocation rules;
stores every accepted index placement durably through storedUntil;
uses the specified discovery keys and unsigned 256-bit XOR distance;
returns only current matching records in the required deterministic order;
paginates identity and trust listings with exclusive cursors;
distinguishes absence from a signed score of zero;
verifies records independently of the indexer that returned them;
authenticates every referred identity after connecting;
agrees the exact credit issuer and price before service execution;
does not provide Discovery merely because a requester is unknown and needs
bootstrap help;
does not treat a candidate, signature, XOR distance, or reported trust value as
proof of honesty, reachability, availability, or global consensus;
preserves the same logical contract in a library, standalone node, or any
programming language.
```
