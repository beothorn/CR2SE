# Hosted Publications

## TLDR

Hosted Publications lets any provider store signed pages and feed posts for a publisher that cannot accept connections, such as a phone. Readers fetch them from any provider and verify the publisher themselves. Content can be public or encrypted for chosen readers.

## Module boundary

**Optional** in the [minimum useful node profile](../../ModuleContracts.md#required-and-optional-capabilities).
Owns hosted publication placements. Consumes Services, Identity, Cryptography
and local persistence. Neither Storage, Messaging, Static Pages, Public Feeds nor
the Discovery indexer is a handler dependency; it reuses their rules by
reference only.

Implement against the [input contract](./inputs/README.md) and
[output contract](./outputs/README.md), using the shared
[composition and recovery rules](../../ModuleContracts.md). Use the
[acceptance test pseudocode](./acceptanceTests/README.md) and the
[fixed vectors](./vectors/README.md). See also the
[pseudocode](./pseudocode/README.md), [sequence diagrams](./diagrams/README.md)
and the [shared wire binding](../peer-protocol/README.md).

A **publisher** signs a **publication** and stores it, for a paid retention
period, at one or more **hosts** (service providers). A **reader** lists and
fetches publications from any host and verifies the publisher's signature
without trusting that host. A **hosted page** is a publication carrying a static
page snapshot; a **hosted feed** is an ordered series of publications carrying
feed posts. The publisher need not ever accept a connection or be online while
readers read.

> **Reliability boundary:** one accepted placement is one copy at one host. It
> is not durable publication by itself. Publishers needing availability across
> host failure must follow [CR2SE Redundancy](../../Redundancy.md) and obtain
> independent placements.

Common terms are defined in the [CR2SE Glossary](../../Glossary.md). Common
invocation and charging rules are in [Services](../services/README.md), identity
proof in [Identity](../identity/README.md), algorithms in
[Encryption](../cryptography/README.md) and credit accounting in
[Ledger](../ledger/README.md).

---

## 1. Version 1 service

```text
service:        cr2se.hosted-publication
serviceVersion: 1
pricing model:  cr2se.hosted-publication.v1
```

Operations:

```text
store     retain one signed publication for a retention period
list      list publications of one publisher and kind, newest first
get       return one complete publication
renew     extend the retention of one placement
remove    end one placement and apply an agreed credit release
```

Plus one check: a byte-challenge of a pending placement, defined in section 10.

Each operation acts on one host. Storing the same publication at four hosts
creates four independent service agreements. The service does not replicate
automatically and hosts do not coordinate. All sizes are bytes, all durations
whole seconds, all times Unix seconds, and fixed-width arithmetic never wraps.

This is a new service. The existing `cr2se.page` and
`cr2se.open-social-messaging` services are unchanged and remain valid for
publishers that can accept connections (section 15).

---

## 2. Problem and requirements

In `cr2se.page` and `cr2se.open-social-messaging` the publisher's own identity
is the service provider; a provider must refuse to return feed messages signed
by anyone else, and CR2SE has no relay (see
[Public Feeds section 6](../public-feeds/README.md#6-availability-and-feed-ownership)
and [Decisions](../../Decisions.md)). A phone behind NAT cannot accept a reader's
connection and is often offline, and its readers may be behind NAT too, so its
profile page and feed cannot be read.

A hosted publication changes only who serves and who vouches. Requirements:

1. **No trust in the host.** A reader verifies the publisher's signature and
   every content hash. A host can withhold or serve an older version but cannot
   forge content.
2. **No coordination.** A publisher stores the identical signed bytes at as
   many hosts as it chooses; hosts know nothing of each other.
3. **Minimal host knowledge.** Restricted content is opaque to hosts; they learn
   only the metadata fields below.
4. **Reuse.** Placement, retention, renewal, removal credits, byte checks, price
   arithmetic and replay rules reuse [Messaging](../messaging/README.md).
5. **Static meaning preserved.** A page remains a static snapshot and a feed post
   remains a [Public Feeds message](../public-feeds/README.md).

Not provided: a relay for live traffic, notifications, retraction of copies a
reader already holds, or a name system.

### Relationship to existing services

| Topic | Messaging | Static Pages | Public Feeds | Hosted Publications |
|---|---|---|---|---|
| Who serves | Any provider | Publisher only | Publisher only | Any provider |
| Who signs | Sender, over exact bytes | No resource signature | Publisher over message hash | Publisher, over exact bytes |
| Who reads | One recipient | Any visitor | Any reader | Any reader, or an audience |
| Encryption | Optional, one recipient | None | None | Public or audience-encrypted |
| Retention | Paid placement, renewable | None promised | None promised | Paid placement, renewable |
| Pricing | Rational formulas | Fixed price | Fixed price | Messaging's rational formulas |
| Replay/idempotency | Recovery and removal IDs | None | None | Removal ID; reads are idempotent |

Reused unchanged from Messaging: placement IDs, `acceptedAt`/`expiresAt`, the
rational price formulas and ceiling rule, guarded renewal, removal with
early-release credits and `removalId` replay, the byte check, and the key
derivation pattern for encryption. Reused from Static Pages: canonical paths
and media types. Reused from Public Feeds: canonical message bytes and
attachments.

---

## 3. Publications

A **publication** is a signed association between metadata and one immutable
byte sequence, its **content**. Metadata fields:

```text
publicationId:  bytes, exactly 32 bytes
publisherId:    bytes, exactly 32 bytes
kind:           "page", "feed-post", or "resource"
sequence:       uint64
publishedAt:    uint64 Unix seconds
visibility:     "public" or "restricted"
audience:       array of 32-byte identity IDs
contentSize:    uint64
contentHash:    bytes, exactly 32 bytes
```

`publicationId` is generated by the publisher with a cryptographically secure
random number generator. The same publication is stored unchanged at every
host, so all replicas share one publication ID. A publisher must never reuse a
publication ID for different bytes.

`kind` has one code byte:

```text
0x01  page         content is a page manifest (section 11)
0x02  feed-post    content is Public Feeds canonical message bytes (section 12)
0x03  resource     content is one page resource's bytes (section 11)
```

`sequence` is publisher-assigned. For `page` and `feed-post` it is the ordering
and version number of section 13. For `resource` it must be zero. `publishedAt`
is the publisher's claimed time; hosts may reject implausible values by local
policy but it is not a trusted clock.

`visibility` has one code byte: `0x00` public, `0x01` restricted. `audience` is
empty when public. When restricted it holds 1 to `maximumAudience` unique
identity IDs in strictly ascending unsigned lexicographic order; these identities
and the publisher may read the publication. `contentSize` must be at least one.
`contentHash` is `SHA-256(content)`.

The **stream** of a publisher and kind is all its publications of that kind. A
publisher has one page stream and one feed-post stream, which readers list.
Resources are addressed only by publication ID (from a signed manifest) and are
not listed.

Metadata other than the audience is visible to hosts. Encryption protects only
the content (section 5). Publisher ID, kind, sequence, time, size, hash,
audience IDs, timing and access patterns are not hidden.

---

## 4. Publisher signature

Integers in signing inputs are big-endian: `uint32_be` four bytes, `uint64_be`
eight bytes. IDs and hashes are their exact 32 bytes. String constants are
exact ASCII without a terminator. The **publication signing bytes** are:

```text
ASCII("CR2SE-PUBLICATION-V1")
|| publicationId
|| publisherId
|| kindCode
|| uint64_be(sequence)
|| uint64_be(publishedAt)
|| visibilityCode
|| uint32_be(audience count)
|| audience IDs, in the stored ascending order
|| uint64_be(contentSize)
|| contentHash
|| content
```

`publisherSignature` is the 64-byte Ed25519 signature over those bytes;
`publisherPublicKey` is the publisher's 32-byte Ed25519 public key. Because the
signature covers content, restricted content is signed as ciphertext.

Before accepting a store, and before using a fetched publication, the checker
must:

1. derive the identity ID from `publisherPublicKey` and require it to equal
   `publisherId`;
2. require `publisherId` to equal the authenticated publisher (host, on store)
   or the publisher the reader intended (reader, on get);
3. validate kind, sequence rule, visibility, audience ordering, size and hash;
4. verify `publisherSignature` over the exact signing bytes.

A host serves the exact signed bytes it stored. A reader repeats every step and
additionally the content-specific checks of sections 5, 11 and 12. Test
vectors are in [vectors](./vectors/README.md).

---

## 5. Public and restricted visibility

A **public** publication's content is plaintext. Any authenticated reader may
list and get it. A host must not require any relationship to the publisher.

A **restricted** publication's content is an **encrypted envelope**: the
plaintext content (section 11 manifest, resource bytes or section 12 message
bytes) is encrypted once with a random content key, and that key is wrapped for
each audience member. Only identities in `audience`, and the publisher, may
list or get it; the host enforces this by the authenticated requester ID.

### Reader encryption keys

Each audience member's persistent X25519 key is obtained and verified exactly as
for [Messaging](../messaging/README.md#board-encryption-key-field), through the
Board `identityEncryption` field of that identity. The publisher lists the
reader's identity ID in `audience` and that key in the envelope, in the same
order.

### Envelope layout

The **encryption metadata bytes** are:

```text
ASCII("CR2SE-PUBLICATION-ENCRYPTION-METADATA-V1")
|| publicationId || publisherId || kindCode
|| uint64_be(sequence) || uint64_be(publishedAt)
```

The publisher generates a random 32-byte `contentKey`, one ephemeral X25519 key
pair, a random 24-byte `contentNonce` and, for each reader, a random 24-byte
`wrapNonce`. For each reader encryption public key `R`:

```text
sharedSecret = X25519(ephemeralPrivateKey, R)
wrapKey = HKDF-SHA-256(
    inputKeyMaterial = sharedSecret,
    salt = SHA-256(encryptionMetadataBytes),
    info = ASCII("CR2SE-PUBLICATION-KEY-WRAP-V1"),
    outputLength = 32)
wrappedContentKey = XChaCha20-Poly1305-Encrypt(
    key = wrapKey, nonce = wrapNonce, plaintext = contentKey,
    authenticatedData = encryptionMetadataBytes || R)       // 48 bytes
contentCiphertext = XChaCha20-Poly1305-Encrypt(
    key = contentKey, nonce = contentNonce, plaintext = plaintextContent,
    authenticatedData = encryptionMetadataBytes)
```

The stored content of a restricted publication is exactly:

```text
0x01                                    envelope version
|| ephemeralPublicKey                   32 bytes
|| contentNonce                         24 bytes
|| uint32_be(entry count)               equals the audience count
|| for each audience identity, in audience order:
       readerEncryptionPublicKey        32 bytes
    || wrapNonce                        24 bytes
    || wrappedContentKey                48 bytes
|| contentCiphertext                    remaining bytes, at least 16
```

The header is 61 bytes and every entry 104 bytes. The entry count must equal the
audience count. An invalid X25519 shared result must be rejected.

A reader finds an entry whose `readerEncryptionPublicKey` it holds the private
key for, recomputes `sharedSecret = X25519(readerPrivateKey, ephemeralPublicKey)`,
derives `wrapKey`, unwraps `contentKey` and decrypts `contentCiphertext`. Any
failure yields no plaintext and the publication is unusable for that reader.
The host does not decrypt, and a host cannot tell which entry belongs to which
audience member beyond the audience ordering.

Visibility limits: a reader in the audience can copy the plaintext, and every
audience member sees every audience identity and encryption key. A publisher
that must not reveal one reader to another stores a separate restricted
publication per reader.

---

## 6. Placements, retention, renewal and removal

A **placement** is one host's accepted agreement to retain one publication. It
records the complete signed publication, publisher and host identities, offering
ID and version, `acceptedAt`, `expiresAt`, cumulative store and renewal prices
and credit issuer, and its state:

```text
pending -> removed
   \-> expired
```

There is no recovered state: reading does not consume a publication. A
placement ID is a 32-byte provider-generated random value unique at that host.
A host must retain the complete publication while the placement is pending and
may delete it once removed or expired. `expiresAt = acceptedAt + retentionSeconds`.
Active means `providerCurrentTime < expiresAt`. Differences from Messaging:

- there is no recipient and no recovery transition or receipt;
- anyone permitted by visibility may read while pending, as often as they pay;
- only the publisher may store, renew, remove or check;
- a host must reject a store whose `(publisherId, publicationId)` already has a
  pending placement at that host (the publisher renews instead).

Everything else follows Messaging: serialization of conflicting operations on
one placement, operations accepted while active completing under their terms,
and no charge for failed operations.

---

## 7. Store

The authenticated publisher supplies:

```text
operation:          "store"
publicationId, publisherId, kind, sequence, publishedAt, visibility,
audience, contentSize, contentHash, publisherPublicKey, publisherSignature,
retentionSeconds, content
```

The host validates the offering limits, calculated price (section 14), the
checks of section 4, the sequence rule below, and for restricted content the
envelope structure. Metadata required for validation and pricing is exchanged
before a streamed body. Success is reported only after the placement and
complete publication are durable.

Sequence rules, enforced per host over its pending placements of the same
publisher and kind (`page` and `feed-post` only):

```text
a new publication whose sequence equals the sequence of a pending publication
with a different publicationId is rejected as a conflict
```

A host need not require sequences to increase; readers choose (section 13). The
output is:

```text
operation: "store"; placementId; publicationId; acceptedAt; expiresAt; price
```

---

## 8. List

`list` returns metadata of one publisher's publications of one kind, newest
first. The authenticated reader supplies:

```text
operation:            "list"
publisherId:          bytes, exactly 32 bytes
kind:                 "page" or "feed-post"
beforeSequence:       uint64, optional cursor field
beforePublicationId:  bytes, exactly 32 bytes, optional cursor field
limit:                uint32
```

`limit` is in `1 .. maximumListResults`; the two cursor fields are both present
or both absent. The host considers the pending placements of that publisher and
kind that the reader may read: all public ones, and restricted ones whose
audience contains the authenticated reader (or whose publisher is the reader).
It orders them by `(sequence descending, publicationId descending)`, unsigned
lexicographic for IDs, and returns entries strictly after the cursor pair in
that order, at most `limit`. Each entry:

```text
placementId, publicationId, kind, sequence, publishedAt, visibility,
contentSize, contentHash, acceptedAt, expiresAt
```

The output is `operation`, `publisherId`, `entries`, `more` and `price`.
`more` is true only when another readable entry followed the last returned one.
The next page's cursor is the last entry's `sequence` and `publicationId`. An
empty result is a successful, charged list. Restricted publications the reader
may not read are omitted without any difference in result shape: they do not
affect `entries`, `more` or `price`, so an unauthorized reader learns nothing
about their existence. List is not a snapshot. Entry metadata is a hint; the
reader trusts only what it verifies after `get`.

---

## 9. Get

The authenticated reader supplies:

```text
operation:    "get"
publisherId:  bytes, exactly 32 bytes
publicationId:bytes, exactly 32 bytes
maximumBytes: uint64
```

`maximumBytes` is the largest content the reader accepts; it must not exceed
`maximumContentBytes`. The host locates one pending, readable publication with
that publisher and publication ID. It fails without charge when the input is
invalid, no such readable publication exists (unknown, expired, removed and
unauthorized are indistinguishable), the content exceeds `maximumBytes`, or the
host cannot return the complete publication. The successful output contains the
stored `publicationId`, `publisherId`, `kind`, `sequence`, `publishedAt`,
`visibility`, `audience`, `contentSize`, `contentHash`, `publisherPublicKey`,
`publisherSignature`, `content` and `price`.

The reader then performs section 4 and the content checks. Repeating `get` is a
new invocation and charge; get has no replay guard because it changes no state.

**Wire pricing input.** The price of `get` depends on the size the host returns,
which the requester cannot know beforehand, so the quote carries it: the
[Peer Protocol](../peer-protocol/README.md) `pricingInputs` of a hosted `get` and
of a hosted `renew` is `{"contentSize": decimal}`. For `get` the reader requires
`1 <= contentSize <= maximumBytes` and prices the quote from it; the returned
`contentSize` must equal the quoted value exactly, or the result is invalid and
is not paid. For `renew` the publisher requires the value to equal the content
size it stored. A hosted `remove` quote carries its `releaseCredits` as Messaging
`remove` does.

---

## 10. Renew, remove and check

**renew.** Publisher only, on a pending placement. Input `placementId`,
`expectedExpiresAt`, `additionalSeconds`. Exactly the rules and output of
[Messaging renew](../messaging/README.md#12-renew): the expected expiration must
equal the current one, durations obey the current offering, and
`newExpiresAt <= acceptedAt + maximumTotalRetentionSeconds`.

**remove.** Publisher only, on a pending placement. Input `placementId`,
`removalId`, `expectedExpiresAt`, `minimumReleaseCredits`. Quote, acceptance,
atomic effects, idempotent replay and limits are exactly those of
[Messaging remove](../messaging/README.md#13-remove-and-early-release-credits),
applied to a pending placement. Removal ends the host's retention and serving
obligation; it does not retract copies readers hold, and public content stays
public.

**check.** Publisher only, pending active placement. Input `placementId` and
`offset < contentSize`; output one content byte; the pass/fail/inconclusive
rules, timer and charge are exactly those of the
[Messaging check](../messaging/README.md#14-messaging-check) using
`checkResponseSeconds` and `checkPrice`. The publisher's expected byte is the
byte of the content it signed (ciphertext, if restricted).

---

## 11. Hosted pages

A hosted page is a `page` publication whose content is a **page manifest** and
whose resources are separate `resource` publications by the same publisher with
the same visibility and audience. The manifest lists, for each resource, a
canonical path and media type ([Static Pages](../pages/README.md)), its size and
hash and the resource publication ID. The **canonical manifest bytes** are:

```text
ASCII("CR2SE-HOSTED-PAGE-MANIFEST-V1")
|| uint32_be(resource count)
|| for each resource, ordered by path bytes ascending, no duplicates:
       length-prefixed path
    || length-prefixed mediaType
    || uint64_be(resource size)
    || SHA-256(resource content)
    || resourcePublicationId
```

A length-prefixed string is `uint64_be(byte length) || UTF-8 bytes` as in
[Public Feeds](../public-feeds/README.md#2-bytes-integers-text-and-time). The
count is `1 .. maximumManifestResources`. The root path `/` must be present and
its media type must be `text/html`. Paths and media types obey Static Pages
section 3 and 4.

A reader fetches a page by listing `page` (first entry is the newest), `get`ting
the manifest publication, verifying it, and then `get`ting each resource it
needs by `resourcePublicationId` from any host. For each resource it requires
the publication to be signed by the same publisher with kind `resource`, the
same visibility and audience as the manifest, `contentSize` and `contentHash`
equal to the manifest entry, and (if restricted) a successful decryption. A
resource that fails any check is not part of the page. Resources are immutable
and may be shared by several page versions; a publisher stores each resource
once per host and renews it as long as any retained manifest references it.
Each resource retrieval is a separate charged `get`, as in Static Pages. A
publisher should keep each resource's retention at least as long as every
manifest that names it; a reader that cannot obtain a named resource from any
host treats the page as incomplete (not corrupt) and may show what it has.

A hosted page snapshot is self-consistent: its resources are exactly those the
signed manifest names. Content is untrusted exactly as in Static Pages section
13.

---

## 12. Hosted feeds

A hosted feed is the `feed-post` stream of a publisher. A feed-post
publication's content is the **Public Feeds canonical message bytes**
(attachments inline), with `messageId` equal to `publicationId`, `publisherId`
equal to the publication's publisher and `publishedAt` equal to the
publication's. The reader reconstructs and validates attachments and fields as
Public Feeds section 4 and 5 require, except that the authenticator is the
publication signature of section 4 rather than a separate
`publisherSignature` over a message hash. A mismatch makes the post invalid.

Hosted feed order is `(sequence descending, publicationId descending)`. A
publisher normally assigns increasing sequence numbers in publication order.
Readers combining several publishers merge by `publishedAt`, using publisher ID
and publication ID as deterministic tie-breakers, as in
[Public Feeds section 14](../public-feeds/README.md#14-reader-algorithm-and-combined-feeds),
and deduplicate by `(publisherId, publicationId)`.

The hosted-feed read of "since" or "interval" is performed by the reader locally:
it lists newest first and stops when `publishedAt` is out of range. Hosts
define no time selector, which keeps the host's work and price independent of
reader policy. As with Public Feeds, a feed is not an archive commitment: a
post is available only while a placement for it is pending at some host.

---

## 13. Updates and the latest version

A page update is a new `page` publication with a larger `sequence`; old
versions are not edited. A reader selects the **latest** page by querying one
or more hosts, verifying every candidate and taking the greatest verified
`sequence`. It then uses that manifest's resources.

Equivocation is two verified publications with the same publisher, kind and
`sequence` but different `publicationId` (or the same publication ID with
different signed bytes, which cannot both verify). A reader that detects it from
any hosts must not choose between them: it should keep showing the latest
sequence below the conflict, report the publisher as equivocating, and may
apply local trust decisions. Hosts reject a conflict they see at store
(section 7); only a reader combining hosts can detect one across hosts.

Absence proves nothing. A host may be offline, may have expired a placement, or
may serve an older version, and a reader cannot know whether a newer version
exists elsewhere. Readers should query several hosts and treat the highest
verified sequence as best-known, not as proven-latest. A publisher that loses
its counter should choose a sequence not less than `publishedAt` (seconds) and
greater than any sequence it knows it used, to avoid reuse. A publisher may stop renewing, or remove, old versions.
Version 1 has no tombstone or retraction.

---

## 14. Pricing, Board offering and service definition

Credits are integers; usage factors are exact fractions as in
[Messaging section 7](../messaging/README.md#7-pricing-and-board-offering):
`{ "numerator": uint64, "denominator": uint64 >= 1 }`, no floating point,
arbitrary-precision intermediate arithmetic, and an exact result above `uint64`
is invalid. Let `S` be content bytes, `T` initial retention seconds, `A`
renewal seconds, `M = minimumPrice`, and `B, X, R, N` the factors below:

```text
storePrice = max(M, ceil(S*B.n/B.d + S*T*X.n/X.d))
getPrice   = max(M, ceil(S*R.n/R.d))        // S = returned content bytes
renewPrice = max(M, ceil(S*A*N.n/N.d))
listPrice, removePrice, checkPrice: advertised exact prices, at least 1
```

Offering fields (`pricing` and `info`; no fixed `price`):

```text
minimumPrice
contentByteUsageFactor               B
contentByteStorageDurationFactor     X
readByteUsageFactor                  R
renewalByteStorageDurationFactor     N
listPrice, removePrice
checkPrice (top-level, as in Messaging)

maximumContentBytes
minimumRetentionSeconds, maximumRetentionSeconds, maximumTotalRetentionSeconds
maximumListResults                    1 .. 2^32-1
maximumAudience                       0 .. 65535 (0 = public only)
maximumManifestResources              1 .. 2^32-1
checkResponseSeconds                  at least 1
```

The duration limits obey `minimum <= maximum <= maximumTotal`. A complete
offering:

```json
{
  "id": "hosted-publication-standard",
  "service": "cr2se.hosted-publication",
  "serviceVersion": 1,
  "description": "Host signed pages and feed posts for readers until expiration.",
  "creditIssuer": "PROVIDER_ID",
  "pricing": {
    "model": "cr2se.hosted-publication.v1",
    "minimumPrice": 1,
    "contentByteUsageFactor": { "numerator": 1, "denominator": 1000000 },
    "contentByteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
    "readByteUsageFactor": { "numerator": 1, "denominator": 1000000 },
    "renewalByteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
    "listPrice": 1,
    "removePrice": 1
  },
  "checkPrice": 1,
  "info": {
    "maximumContentBytes": 10000000,
    "minimumRetentionSeconds": 3600,
    "maximumRetentionSeconds": 157680000,
    "maximumTotalRetentionSeconds": 315360000,
    "maximumListResults": 100,
    "maximumAudience": 64,
    "maximumManifestResources": 1000,
    "checkResponseSeconds": 30
  },
  "preconditions": [ "cr2se.identity" ]
}
```

The numbers are illustrative. `creditIssuer` must equal the host identity.
Changing an offering does not shorten an accepted placement; each later paid
operation selects a current offering with the same service, version and pricing
model. Exact prices and issuer are agreed before chargeable work or a large
transfer. Failed operations are not charged.

### Service definition

Every offering exposes a definition through `service.get`, logically equal to:

```json
{
  "id": "hosted-publication-standard",
  "service": "cr2se.hosted-publication",
  "serviceVersion": 1,
  "description": "Host signed pages and feed posts for readers until expiration.",
  "input": { "type": "object", "fields": {
    "operation": { "type": "string", "description": "Operation: store, list, get, renew, or remove." },
    "placementId": { "type": "bytes", "description": "Host-generated 32-byte placement identifier.", "optional": true },
    "publicationId": { "type": "bytes", "description": "Publisher-generated 32-byte publication identifier.", "optional": true },
    "publisherId": { "type": "bytes", "description": "Publisher CR2SE ID.", "optional": true },
    "kind": { "type": "string", "description": "Publication kind: page, feed-post, or resource.", "optional": true },
    "sequence": { "type": "uint64", "description": "Publisher-assigned sequence.", "optional": true },
    "publishedAt": { "type": "uint64", "description": "Publisher-claimed time in Unix seconds.", "optional": true },
    "visibility": { "type": "string", "description": "public or restricted.", "optional": true },
    "audience": { "type": "array", "description": "Sorted 32-byte reader identity IDs for restricted content.", "items": { "type": "bytes", "description": "Reader CR2SE ID." }, "optional": true },
    "contentSize": { "type": "uint64", "description": "Exact content size in bytes.", "optional": true },
    "contentHash": { "type": "bytes", "description": "32-byte SHA-256 content hash.", "optional": true },
    "publisherPublicKey": { "type": "bytes", "description": "Publisher 32-byte Ed25519 public key.", "optional": true },
    "publisherSignature": { "type": "bytes", "description": "Publisher 64-byte publication signature.", "optional": true },
    "content": { "type": "bytes", "description": "Exact publication content bytes.", "optional": true },
    "retentionSeconds": { "type": "uint64", "description": "Requested initial retention in seconds.", "optional": true },
    "beforeSequence": { "type": "uint64", "description": "Exclusive list cursor sequence.", "optional": true },
    "beforePublicationId": { "type": "bytes", "description": "Exclusive list cursor publication ID.", "optional": true },
    "limit": { "type": "uint32", "description": "Maximum list entries requested.", "optional": true },
    "maximumBytes": { "type": "uint64", "description": "Largest content the reader accepts.", "optional": true },
    "expectedExpiresAt": { "type": "uint64", "description": "Placement expiration expected by the requester.", "optional": true },
    "additionalSeconds": { "type": "uint64", "description": "Retention seconds added by renewal.", "optional": true },
    "removalId": { "type": "bytes", "description": "Publisher-generated 32-byte removal identifier.", "optional": true },
    "minimumReleaseCredits": { "type": "uint64", "description": "Smallest early-release credit amount accepted.", "optional": true }
  } },
  "output": { "type": "object", "fields": {
    "operation": { "type": "string", "description": "Completed operation." },
    "placementId": { "type": "bytes", "description": "Host-generated 32-byte placement identifier.", "optional": true },
    "publicationId": { "type": "bytes", "description": "Publication identifier.", "optional": true },
    "publisherId": { "type": "bytes", "description": "Publisher CR2SE ID.", "optional": true },
    "kind": { "type": "string", "description": "Publication kind.", "optional": true },
    "sequence": { "type": "uint64", "description": "Publisher-assigned sequence.", "optional": true },
    "publishedAt": { "type": "uint64", "description": "Publisher-claimed time.", "optional": true },
    "visibility": { "type": "string", "description": "public or restricted.", "optional": true },
    "audience": { "type": "array", "description": "Reader identity IDs.", "items": { "type": "bytes", "description": "Reader CR2SE ID." }, "optional": true },
    "contentSize": { "type": "uint64", "description": "Content size in bytes.", "optional": true },
    "contentHash": { "type": "bytes", "description": "32-byte SHA-256 content hash.", "optional": true },
    "publisherPublicKey": { "type": "bytes", "description": "Publisher Ed25519 public key.", "optional": true },
    "publisherSignature": { "type": "bytes", "description": "Publisher signature.", "optional": true },
    "content": { "type": "bytes", "description": "Exact content bytes.", "optional": true },
    "acceptedAt": { "type": "uint64", "description": "Host acceptance time.", "optional": true },
    "previousExpiresAt": { "type": "uint64", "description": "Expiration before renewal.", "optional": true },
    "expiresAt": { "type": "uint64", "description": "Current placement expiration.", "optional": true },
    "entries": { "type": "array", "description": "Listed publication metadata.", "items": { "type": "object", "fields": {
      "placementId": { "type": "bytes", "description": "Placement identifier." },
      "publicationId": { "type": "bytes", "description": "Publication identifier." },
      "kind": { "type": "string", "description": "Publication kind." },
      "sequence": { "type": "uint64", "description": "Publisher sequence." },
      "publishedAt": { "type": "uint64", "description": "Publisher-claimed time." },
      "visibility": { "type": "string", "description": "public or restricted." },
      "contentSize": { "type": "uint64", "description": "Content size." },
      "contentHash": { "type": "bytes", "description": "Content hash." },
      "acceptedAt": { "type": "uint64", "description": "Acceptance time." },
      "expiresAt": { "type": "uint64", "description": "Expiration time." }
    } }, "optional": true },
    "more": { "type": "bool", "description": "Whether another readable entry existed.", "optional": true },
    "removalId": { "type": "bytes", "description": "Removal identifier.", "optional": true },
    "removed": { "type": "bool", "description": "True after successful removal.", "optional": true },
    "releaseCredits": { "type": "uint64", "description": "Provider-issued early-release credits.", "optional": true },
    "price": { "type": "uint64", "description": "Credits charged.", "optional": true }
  } },
  "check": {
    "description": "Challenge a pending placement for one publisher-selected content byte.",
    "input": { "type": "object", "fields": {
      "placementId": { "type": "bytes", "description": "Pending placement identifier." },
      "offset": { "type": "uint64", "description": "Zero-based challenged content offset." }
    } },
    "output": { "type": "object", "fields": {
      "outcome": { "type": "string", "description": "Requester-computed result: pass, fail, or inconclusive." },
      "placementId": { "type": "bytes", "description": "Placement identifier that was checked." },
      "offset": { "type": "uint64", "description": "Challenged offset." },
      "value": { "type": "bytes", "description": "One-byte provider evidence when returned.", "optional": true }
    } }
  }
}
```

The operation discriminant selects required input fields:

```text
store    publicationId, publisherId, kind, sequence, publishedAt, visibility,
         audience, contentSize, contentHash, publisherPublicKey,
         publisherSignature, retentionSeconds, content
list     publisherId, kind, limit, and either both cursor fields or neither
get      publisherId, publicationId, maximumBytes
renew    placementId, expectedExpiresAt, additionalSeconds
remove   placementId, removalId, expectedExpiresAt, minimumReleaseCredits
```

A known field belonging only to another operation is rejected; an unknown field
follows the compatible-extension rule in Services.

---

## 15. Versioning against existing Pages and Feeds

Hosted Publications is a new service identifier, `cr2se.hosted-publication`
version 1, not a mode of `cr2se.page` or `cr2se.open-social-messaging`, because
those services define the provider as the publisher, a fixed price, no
retention, and (for Pages) no signature. Changing those semantics would break
conforming version 1 implementations. Consequences:

- Existing publisher-served Pages and Feeds are unchanged and fully valid.
- A publisher may do both: serve its own pages when reachable and host
  publications for when it is not. Readers prefer neither; they apply their own
  trust and freshness policy and may combine verified results.
- A node that hosts publications must not claim them as `cr2se.page` or
  `cr2se.open-social-messaging` resources under its own identity, because those
  services require the provider to be the publisher.
- A reader supports hosted publications only if it advertises and implements
  this service.

---

## 16. Time, concurrency and failures

Conflicting operations on one placement are serialized: `remove` versus `get`
yields one definite order; a `get` accepted while pending completes. Failure
without charge includes malformed fields, invalid lengths, unsupported kinds,
forbidden fields, limits exceeded, price disagreement, insufficient accepted
balance, failed identity proof, invalid signature, size or hash mismatch, unsorted
or duplicate audience, envelope or entry-count mismatch, kind or sequence rule
violations, duplicate publication ID, conflicting sequence, stale expected
expiration, inactive placement and interrupted output.

Errors across an authorization boundary do not distinguish an unknown
publication from one the requester may not read. A missing or refused
publication does not create an automatic credit reversal, beyond an explicitly
completed early-release agreement. CR2SE has no global adjudicator.

---

## 17. Security, privacy and abuse

Hosts handle untrusted sizes, arrays, audiences, envelopes, manifests, cursors
and identifiers: validate before allocating, bound list work and output, use
overflow-safe arithmetic, stream large bodies in bounded frames and serialize
state changes durably.

- **Content authenticity.** Signatures and hashes protect integrity and origin,
  not trustworthiness. A host cannot forge, but can withhold or serve stale
  content (section 13). Active page content is untrusted as in Static Pages.
- **Metadata leakage.** Hosts and every reader see publisher ID, kind, sequence,
  time, size and access patterns; restricted publications also reveal audience
  identity IDs and encryption keys to the host and all audience members.
  Reader access patterns are visible to the host.
- **Restricted visibility.** The host check is an access-control convenience on
  top of encryption, not its replacement. An authorized reader can re-share
  plaintext. A publisher cannot revoke a key already wrapped.
- **Unbounded listing and spam.** Store is paid, which makes unsolicited hosting
  costly but does not eliminate spam. Hosts should apply publisher trust,
  per-publisher quotas on placements and total bytes, list limits and rate
  limits on failed identity proof and probing. Readers pay for `list`, bounding
  scanning abuse; hosts should bound the work of one `list`.
- **Abusive content.** Hosts may refuse or remove public content by local policy
  and cannot inspect restricted content. Removal by a host is not a protocol
  guarantee.
- **Key use.** Encryption reuses the identity's persistent X25519 key through
  Identity; no new key purpose or private-key export is required.

A version 1 implementation is interoperable only if it:

```text
uses cr2se.hosted-publication version 1 and cr2se.hosted-publication.v1 pricing;
uses exact rational, ceiling, overflow-safe price arithmetic;
authenticates the publisher for store, renew, remove and check;
verifies the exact signing bytes of section 4 and reproduces the vectors;
uses SHA-256 over the exact content bytes;
uses 32-byte unpredictable publication, placement and removal IDs;
retains pending publications durably until removal or expiration;
enforces visibility by authenticated requester without distinguishing hidden items;
orders and pages list results as defined;
implements idempotent removal accounting;
agrees every price and release amount before execution;
does not charge failed operations;
implements the exact envelope and manifest layouts when advertising them;
preserves placement state across connections and ordinary restart.
```
