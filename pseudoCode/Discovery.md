# Discovery pseudocode

This document translates [`Discovery.md`](../Discovery.md) into
implementation-neutral algorithms. The specification remains authoritative.
Records and lookup results are public, signed, expiring, and untrusted.

## 1. Constants and record validation

```text
SERVICE_ID = "cr2se.discovery"
SERVICE_VERSION = 1
PRICING_MODEL = "cr2se.discovery.v1"
ID_SIZE = 32

Record:
    type = ADDRESS | SHARE | TRUST
    publisherId; publisherPublicKey; sequence; issuedAt; expiresAt
    typeSpecificFields
    signature
    encodedCanonicalBytes
    recordId = SHA256(encodedCanonicalBytes)

IndexPlacement:
    recordId; encodedCanonicalBytes; acceptedAt; retainUntil
```

```text
function validateCommonRecord(encoded, terms, now):
    require encoded length is bounded before allocation
    record = parse exact version/type tags and big-endian fields
    require record.publisherId == Identity.deriveVersion1Id(record.publicKey)
    require record.issuedAt <= record.expiresAt
    require record.issuedAt <= now + terms.maximumClockSkewSeconds
    require record.expiresAt - record.issuedAt
            <= terms.maximumRecordLifetimeSeconds
    validate type-specific fields and canonical ordering
    canonicalWithoutSignature = encodeSigningFieldsExactly(record)
    require Ed25519.verify(record.publicKey, canonicalWithoutSignature,
                           record.signature)
    require encodeRecordExactly(record) == encoded
    return record with recordId=SHA256(encoded)
```

Address records validate unique, canonically ordered endpoints, supported
network/address representations, ports, and `maximumEndpointsPerRecord`.
Share records validate 32-byte share ID, provider identity, positive/negative
availability semantics, and any canonical endpoints. Trust records validate
subject ID and the exact trust representation. The fixed prefixes and complete
byte layouts are exactly those in the normative specification; no JSON or
native serialization may replace them.

A record is current only when its time interval includes the provider's current
time and it has not been superseded by the applicable higher sequence/current
record rule.

## 2. Keys, distance, and indexes

```text
function discoveryKey(recordOrQuery):
    switch type:
      ADDRESS: return SHA256(normative address-key prefix || identityId)
      SHARE:   return SHA256(normative share-key prefix || shareId)
      TRUST:   return SHA256(normative trust-key prefix || subjectId)

function xorDistance(left, right):
    require both are 32 bytes
    return unsignedBigEndianInteger(left XOR right)

function candidateIndexers(key, knownPeers, count):
    authenticate and deduplicate candidates by identity ID
    sort ascending by (xorDistance(identityId, key), identityId)
    return first count
```

Distance is a deterministic selection tool, not proof of honesty or a routing
guarantee.

## 3. Offering and charging

Offering validation requires the exact service/version/model, identity
precondition, no fixed Board price, all positive operation prices, and every
advertised limit. In particular it validates index record/count/byte/retention,
record lifetime/skew, endpoint, lookup/list, and check-response bounds.

```text
function indexPrice(recordCount, terms):
    price = BigInt(terms.indexBasePrice)
          + BigInt(recordCount) * terms.indexRecordPrice
    require 1 <= price <= UINT64_MAX
    return uint64(price)

function operationPrice(operation, terms):
    return exact advertised resolveIdentityPrice, locateSharePrice,
        findTrustPrice, listIdentitiesPrice, or listTrustPrice
```

Every successful operation, including an empty query, is charged. Failures are
not. Agree on issuer and exact price before execution.

## 4. Atomic indexing

```text
function index(authenticatedRequester, offering, encodedRecords, now):
    require 1 <= length(encodedRecords) <= terms.maximumIndexRecords
    require checkedSum(byte lengths) <= terms.maximumIndexBytes
    parsed = map bytes through validateCommonRecord(bytes, terms, now)
    require all recordIds unique
    enforce requester authorization and local indexing policy for every record
    retainUntil = min(record.expiresAt,
        checkedAdd(now, terms.maximumIndexRetentionSeconds)) per record
    price = indexPrice(length(parsed), terms); reserve charge
    transaction:
        store every placement or store none, with acceptedAt=now and retainUntil
        update current-record indexes deterministically
    commit charge
    return {operation:"index", acceptedAt:now,
            retainUntil values as specified, price:price}
```

Validation failure leaves no partial batch. Expiration removes placements from
current query indexes; a provider may retain bounded tombstones locally.

## 5. Exact lookups

```text
function resolveIdentity(identityId, recordLimit, candidateLimit, offering):
    require limits in 1 .. maximumLookupResults
    key = discoveryKey(ADDRESS, identityId)
    records = current valid address records exactly for identityId
    candidates = candidateIndexers(key, routingTable, candidateLimit)
    return bounded {records, candidates,
                    price:terms.resolveIdentityPrice}

function locateShare(shareId, recordLimit, candidateLimit, offering):
    require length(shareId)==32 and valid limits
    key = discoveryKey(SHARE, shareId)
    records = current valid positive/negative share records exactly for shareId
    return bounded records and candidate indexers with locateSharePrice

function findTrust(subjectId, recordLimit, candidateLimit, offering):
    require valid identity and limits
    key = discoveryKey(TRUST, subjectId)
    records = current valid trust records exactly for subjectId
    return bounded records and candidate indexers with findTrustPrice
```

Before success, revalidate canonical bytes, signatures, current time, exact key,
ordering, uniqueness, result count, and candidate distance ordering. Returned
claims are evidence, not proof that an endpoint works, a share is hosted, or a
trust opinion is correct.

## 6. Listing and pagination

```text
function listIdentities(afterIdentityId, limit, offering, now):
    require 1 <= limit <= maximumListResults
    ids = distinct identity IDs having current address records
    sort lexicographically by raw 32-byte ID
    select first limit strictly greater than optional cursor
    return {operation:"listIdentities", identities:ids,
            price:terms.listIdentitiesPrice}

function listTrust(afterPublisherId, afterSubjectId, limit, offering, now):
    require both cursor fields are present or both absent
    require 1 <= limit <= maximumListResults
    records = current trust records sorted by normative publisher/subject tuple
    select first limit strictly after cursor
    return {operation:"listTrust", records:records,
            price:terms.listTrustPrice}
```

Cursors are exclusive and pages are snapshots. Concurrent changes can cause a
later page to differ; implementations must not return malformed or internally
inconsistent pages.

## 7. Iterative lookup

```text
function iterativeLookup(target, bootstrapPeers, budget):
    frontier = authenticated bootstrap peers ordered by distance to target key
    queried = Set(); evidence = Map by recordId
    while frontier not empty and budget permits:
        peer = closest unqueried peer; queried.add(peer.id)
        response = invoke matching exact lookup with explicit maximum price
        if verifyLookupResponse(response, target) != PASS: continue
        add valid current matching records to evidence
        authenticate, deduplicate, and distance-order returned candidates
        add policy-approved candidates to frontier
        stop when convergence/local result policy is satisfied
    return locally ranked evidence and diagnostics
```

Set hop, peer, time, byte, concurrency, and credit budgets. Never connect to or
pay every supplied candidate blindly. Bootstrap and tit-for-tat policy are
local; zero trust may prevent initial service until credits/trust are obtained
through another route.

## 8. Placement check and security

```text
function checkIndexPlacement(sender, placementId, freshChallenge, offering):
    authenticate authorized requester
    reserve advertised check price
    respond within checkResponseSeconds with signed/bound evidence containing
        placement identity, record ID, challenge, current retention state/time
    commit only on complete response

function verifyPlacementCheck(expected, evidence, deadline):
    if unavailable, late, or local resource limit reached: return INCONCLUSIVE
    if identity/signature/challenge/record/retention fields contradict expected:
        return FAIL
    return PASS
```

Checks do not prove future retention or truth and do not reverse charges.
Providers rate-limit enumeration and probing, cap all parsing/allocation,
separate untrusted diagnostics, and may refuse indexing for privacy or policy.
Consumers corroborate endpoints and shares, retain negative claims without
letting one signer erase others' positive evidence, and resist routing/Sybil
attacks using independent bootstrap paths and local trust.
