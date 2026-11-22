# Hosted Publications pseudocode

This document translates the [Hosted Publications specification](../README.md)
into implementation-neutral algorithms. The specification remains authoritative.
All inputs, stored content, signatures, envelopes, manifests, times and
identifiers are untrusted.

## 1. State and validation

```text
SERVICE_ID = "cr2se.hosted-publication"; SERVICE_VERSION = 1
PRICING_MODEL = "cr2se.hosted-publication.v1"
SIGNING_PREFIX = ASCII("CR2SE-PUBLICATION-V1")
KIND = {"page":0x01, "feed-post":0x02, "resource":0x03}
VISIBILITY = {"public":0x00, "restricted":0x01}

Placement:
    placementId; publication; hostId; offeringSnapshot
    acceptedAt; expiresAt; cumulativeStoreAndRenewalPrice
    state = PENDING | REMOVED | EXPIRED
```

```text
function signingBytes(p):
    return SIGNING_PREFIX || p.publicationId || p.publisherId
        || byte(KIND[p.kind]) || u64be(p.sequence) || u64be(p.publishedAt)
        || byte(VISIBILITY[p.visibility]) || u32be(length(p.audience))
        || concat(p.audience) || u64be(p.contentSize) || p.contentHash || p.content

function validatePublication(p, expectedPublisher, limits):
    require lengths: IDs/hashes 32, key 32, signature 64
    require p.kind in KIND and p.visibility in VISIBILITY
    require Identity.deriveVersion1Id(p.publisherPublicKey) == p.publisherId
    require p.publisherId == expectedPublisher
    require p.kind != "resource" or p.sequence == 0
    require 1 <= p.contentSize <= limits.maximumContentBytes
    require length(p.content) == p.contentSize and SHA256(p.content) == p.contentHash
    if p.visibility == "public": require length(p.audience) == 0
    else:
        require 1 <= length(p.audience) <= limits.maximumAudience
        require audience strictly ascending, each 32 bytes
        require envelopeIsWellFormed(p.content, length(p.audience))
    require Cryptography.verifyExactBytes(p.publisherPublicKey, signingBytes(p), p.publisherSignature)

function envelopeIsWellFormed(content, audienceCount):
    require length(content) >= 61 + 104*audienceCount + 16
    require content[0] == 0x01 and u32be(content[57..61]) == audienceCount
```

## 2. Store, list, get

```text
function store(invocation, offering):
    p = invocation.input
    validatePublication(p, invocation.authenticatedIdentity, offering.limits)
    require retention within offering minimum/maximum/total
    price = max(M, ceil(S*B.n/B.d + S*T*X.n/X.d)); agree price before body transfer
    serialize on (p.publisherId, p.kind)
    require no PENDING placement with (p.publisherId, p.publicationId)
    if p.kind in ("page","feed-post"):
        require no PENDING placement with same publisher, kind and sequence
                and a different publicationId
    placement = new Placement(randomId32(), p, now(), now() + retentionSeconds)
    commit durably; return {placementId, publicationId, acceptedAt, expiresAt, price}

function readable(placement, requester):
    p = placement.publication
    return placement.state == PENDING and now() < placement.expiresAt and
        (p.visibility == "public" or requester == p.publisherId or requester in p.audience)

function list(invocation, offering):
    in = invocation.input; require 1 <= in.limit <= offering.maximumListResults
    require in.kind in ("page","feed-post"); require both cursor fields or neither
    candidates = placements of in.publisherId, in.kind where readable(., requester)
    order by (sequence desc, publicationId desc)
    if cursor: keep entries strictly after (beforeSequence, beforePublicationId)
    page = first in.limit; more = (candidates remain after page)
    return {entries: metadata(page), more, price: offering.listPrice}

function get(invocation, offering):
    in = invocation.input
    placement = find readable placement for (in.publisherId, in.publicationId)
    fail without charge unless found and size <= min(in.maximumBytes, maximumContentBytes)
    return stored publication bytes and price = max(M, ceil(S*R.n/R.d))
```

## 3. Renew, remove, check

```text
function renew(invocation, offering):          // as Messaging renew
    placement = pending active placement owned by the authenticated publisher
    require in.expectedExpiresAt == placement.expiresAt
    require offering min <= in.additionalSeconds <= offering max
    require expectedExpiresAt + additionalSeconds <= placement.acceptedAt + maximumTotal
    atomically set expiresAt; add renewPrice to cumulative payments

function remove(invocation, offering):         // as Messaging remove
    if replay record exists for (placementId, removalId) by this publisher: return it
    placement = pending placement owned by the publisher; require expectedExpiresAt matches
    release = quoteReleaseCredits(placement)  // minimumRelease <= release <= cumulative payments
    atomically: state = REMOVED; charge removePrice; adjust publisher balance by release;
                store replay output for the ledger lifetime
```

## 4. Reader algorithms

```text
function verifyFetched(p, intendedPublisher, ownEncryptionKeys):
    validatePublication(p, intendedPublisher, readerLimits)
    if p.visibility == "restricted": plaintext = openEnvelope(p, ownEncryptionKeys)
    else: plaintext = p.content
    return plaintext          // failure yields nothing usable

function openEnvelope(p, keys):
    meta = ENCRYPTION_METADATA(p)
    find entry i whose readerEncryptionPublicKey has a private key in keys; else fail
    shared = X25519(privateKey, ephemeralPublicKey); reject invalid result
    wrapKey = HKDF-SHA-256(shared, SHA256(meta), "CR2SE-PUBLICATION-KEY-WRAP-V1", 32)
    contentKey = XChaCha20Poly1305Decrypt(wrapKey, wrapNonce, wrappedContentKey, meta || readerPub)
    return XChaCha20Poly1305Decrypt(contentKey, contentNonce, ciphertext, meta)

function validateManifest(m):
    parse canonical manifest bytes; require count in 1..max and exact end of input
    require paths canonical, ascending, unique; mediaTypes valid; "/" present with "text/html"

function readPage(publisher, hosts):
    candidates = []
    for host in hosts: for entry in list(host, publisher, "page", newest first): fetch and verify
    group candidates by sequence
    if any sequence has two different publicationIds: report equivocation; use highest unconflicted
    page = candidate with greatest unconflicted sequence
    for each needed resource in page.manifest:
        r = get(any host, publisher, resourcePublicationId); verifyFetched(r)
        require r.kind == "resource", r.visibility/audience == page's, size/hash == manifest entry
    return page snapshot
```
