# Discovery pseudocode

This document translates [Discovery specification](../README.md) into
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
    recordId = SHA256(exactSigningBytes) // excludes the signature

IndexPlacement:
    indexId; requesterId; recordId; encodedCanonicalBytes; acceptedAt; storedUntil
    includedCheckState = AVAILABLE | IN_PROGRESS | CONSUMED
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
    require Cryptography.verifyExactBytes(record.publicKey, canonicalWithoutSignature,
                           record.signature)
    require encodeRecordExactly(record) == encoded
    return record with recordId=SHA256(canonicalWithoutSignature)
```

Address records validate unique, canonically ordered endpoints, supported
network/address representations, ports, and `maximumEndpointsPerRecord`.
Share records validate 32-byte share ID, provider identity, positive/negative
availability semantics, and any canonical endpoints. Trust records validate
subject ID and the exact trust representation. The fixed prefixes and complete
byte layouts are exactly those in the normative specification; no JSON or
native serialization may replace them.

A record is current only when expiresAt > now, issuedAt <= now + advertised
clock skew, and its lifetime fits the advertised bound. Use checked arithmetic.
Latest sequence selection preserves tied conflicting records as required by
the specification; a newer record never cancels an existing paid placement.

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
    storedUntil = min(record.expiresAt,
        checkedAdd(now, terms.maximumIndexRetentionSeconds)) per record
    price = indexPrice(length(parsed), terms); reserve charge
    transaction:
        store every placement or none, with unique random 32-byte indexId,
            requesterId, acceptedAt=now, storedUntil, and one included check
        update current-record indexes deterministically
    commit charge
    return {operation:"index", acceptedAt:now,
            placements:[{indexId, recordId, storedUntil} in input order], price:price}
```

Validation failure leaves no partial batch. Expiration removes placements from
current query indexes; a provider may retain bounded tombstones locally.

## 5. Exact lookups

```text
function resolveIdentity(identityId, recordLimit, indexerLimit, offering):
    require limits in 1 .. maximumLookupResults
    key = discoveryKey(ADDRESS, identityId)
    records = current valid address records exactly for identityId
    indexers = candidateIndexers(key, routingTable, indexerLimit)
    return bounded {operation:"resolveIdentity", identityId, addressRecords:records, indexers,
                    price:terms.resolveIdentityPrice}

function locateShare(shareId, recordLimit, indexerLimit, offering):
    require length(shareId)==32 and valid limits
    key = discoveryKey(SHARE, shareId)
    records = current valid positive/negative share records exactly for shareId
    return {operation:"locateShare", shareId, shareRecords:records,
            indexers:boundedCandidates, price:terms.locateSharePrice}

function findTrust(subjectId, recordLimit, indexerLimit, offering):
    require valid identity and limits
    key = discoveryKey(TRUST, subjectId)
    records = current valid trust records exactly for subjectId
    return {operation:"findTrust", subjectId, trustRecords:records,
            indexers:boundedCandidates, price:terms.findTrustPrice}
```

Before success, revalidate canonical bytes, signatures, current time, exact key,
ordering, uniqueness, result count, and candidate distance ordering. Returned
claims are evidence, not proof that an endpoint works, a share is hosted, or a
trust opinion is correct.

## 6. Listing and pagination

```text
function listIdentities(afterIdentityId, limit, offering, now):
    require 1 <= limit <= maximumListResults
    ids = distinct IDs from current records as signer or named subject/provider,
        current candidate entries, and retained authenticated observations
    sort lexicographically by raw 32-byte ID
    select first limit strictly greater than optional cursor
    return {operation:"listIdentities", identities:ids, more:hasNext,
            price:terms.listIdentitiesPrice}

function listTrust(afterEvaluatorId, afterSubjectId, afterRecordId, limit, offering, now):
    require all three cursor fields are present or all absent
    require 1 <= limit <= maximumListResults
    records = current latest trust records, including tied equivocation records,
        sorted by (evaluatorId, subjectId, recordId)
    select first limit strictly after cursor
    return {operation:"listTrust", trustRecords:records, more:hasNext,
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
function checkIndexPlacement(requester, input, now):
    require input.operation == "index"
    lock placement selected by input.indexId
    require requester owns placement and now < placement.storedUntil
    require input.recordId == placement.recordId
    require includedCheckState == AVAILABLE
    mark IN_PROGRESS; quote zero additional credits
    evidence = {indexId, recordId, record:exact retained bytes}
    send complete evidence within accepted checkResponseSeconds
    on complete response: durably mark CONSUMED
    on failed response before completion: restore AVAILABLE

function verifyPlacementCheck(expected, evidence, deadline):
    if unavailable, incomplete, late, or unassociated: return INCONCLUSIVE
    if valid response reports absent active placement: return FAIL
    if evidence.record != expected.exactRecordBytes: return FAIL
    require SHA256(signingBytes(evidence.record)) == expected.recordId
    return PASS
```

Checks do not prove future retention or truth and do not reverse charges.
Providers rate-limit enumeration and probing, cap all parsing/allocation,
separate untrusted diagnostics, and may refuse indexing for privacy or policy.
Consumers corroborate endpoints and shares, retain negative claims without
letting one signer erase others' positive evidence, and resist routing/Sybil
attacks using independent bootstrap paths and local trust.
