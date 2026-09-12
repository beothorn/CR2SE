# Storage pseudocode

This document translates the normative Storage contract in
[`Storage.md`](../Storage.md) into implementation-neutral pseudocode. The
specification remains authoritative. Names such as `LeaseStore`, locks,
transactions, streams, credit reservations, and clocks describe
responsibilities, not required classes, APIs, storage media, or thread models.

All received metadata, schemas, lengths, offsets, hashes, and byte streams are
untrusted. JSON integers below are mathematical integers and must not first be
rounded through a floating-point type. Persistent operations must survive an
ordinary process restart or machine reboot.

---

## 1. Constants and state

```text
SERVICE_ID                 = "cr2se.storage"
SERVICE_VERSION            = 1
PRICING_MODEL              = "cr2se.storage.v1"
IDENTITY_PRECONDITION      = "cr2se.identity"
UINT64_MAX                 = 18_446_744_073_709_551_615
HASH_SIZE                  = 32
LEASE_ID_SIZE              = 32

LEASE_RECEIVING            = receiving
LEASE_ACTIVE               = active
LEASE_EXPIRED              = expired
LEASE_REMOVED              = removed

CHECK_PASS                 = "pass"
CHECK_FAIL                 = "fail"
CHECK_INCONCLUSIVE         = "inconclusive"

Rate:
    numerator              uint64
    denominator            uint64 in 1 .. UINT64_MAX

StorageTerms:
    minimumPrice           uint64 in 1 .. UINT64_MAX
    byteUsageFactor        Rate
    byteStorageDurationFactor Rate
    retrievalByteUsageFactor Rate
    renewalByteStorageDurationFactor Rate
    removePrice            uint64 in 1 .. UINT64_MAX
    checkPrice             uint64 in 1 .. UINT64_MAX
    maximumBytes           uint64 in 1 .. UINT64_MAX
    minimumRetentionSeconds uint64 in 1 .. UINT64_MAX
    maximumRetentionSeconds uint64 in 1 .. UINT64_MAX
    maximumTotalRetentionSeconds uint64 in 1 .. UINT64_MAX
    maximumRetrieveBytes   uint64 in 1 .. UINT64_MAX
    checkResponseSeconds   uint64 in 1 .. UINT64_MAX

OfferingSnapshot:
    offeringId             nonempty string
    revision               implementation-defined immutable revision
    creditIssuer           canonical 32-byte CR2SE ID
    terms                  StorageTerms

Lease:
    leaseId                32 bytes
    requesterId            authenticated canonical CR2SE ID
    providerId             local canonical CR2SE ID
    originalOfferingId     string
    originalOfferingRevision implementation-defined revision
    sizeBytes              uint64
    contentHash            32-byte SHA-256 digest
    acceptedAt             uint64 Unix seconds
    expiresAt              uint64 Unix seconds
    storePrice             uint64 credits
    state                  RECEIVING | ACTIVE | EXPIRED | REMOVED
    bytesHandle            durable immutable byte-sequence handle or NONE

AcceptedOperation:
    kind                   STORE | RETRIEVE | RENEW | REMOVE | CHECK
    requesterId            authenticated canonical CR2SE ID
    offering               immutable current offering snapshot
    agreedPrice            uint64 credits
    creditReservation      reservation handle
```

An implementation may maintain expiration in an active index rather than
persisting an `EXPIRED` marker. A `RECEIVING` record is an incomplete attempt,
not a completed lease and not a retention obligation.

---

## 2. Exact validators and arithmetic

```text
function requireUint64(value, name, minimum = 0):
    if value is not an exact mathematical integer:
        raise ValidationError(name + " must be an exact integer")
    if value < minimum or value > UINT64_MAX:
        raise ValidationError(name + " is outside its uint64 range")
    return value


function requireFixedBytes(value, size, name):
    if value is not bytes or length(value) != size:
        raise ValidationError(name + " has the wrong byte length")
    return value


function checkedAddUint64(left, right):
    requireUint64(left, "left")
    requireUint64(right, "right")
    sum = BigInteger(left) + BigInteger(right)
    if sum > UINT64_MAX:
        raise PriceOrTimeOverflow
    return uint64(sum)


function ceilNonnegativeFraction(numerator, denominator):
    require denominator > 0
    require numerator >= 0
    // div is exact integer division. Both operands are arbitrary precision.
    return (numerator + denominator - 1) div denominator


function validateRate(value, name):
    requireExactKnownMembers(value, {"numerator", "denominator"}, name)
    return Rate {
        numerator: requireUint64(value.numerator, name + ".numerator"),
        denominator: requireUint64(
            value.denominator, name + ".denominator", minimum = 1)
    }


function requirePriceFitsUint64(price):
    if price < 1 or price > UINT64_MAX:
        raise InvalidPrice
    return uint64(price)
```

`BigInteger` means arbitrary-precision arithmetic or an equivalent proven
overflow-safe calculation. Protocol prices must never use floating point.

---

## 3. Offering validation

```text
function validateStorageOffering(offering):
    if offering.service != SERVICE_ID:
        raise InvalidOffering("wrong service")
    if offering.serviceVersion != SERVICE_VERSION:
        raise InvalidOffering("wrong service version")
    if offering has member "price":
        raise InvalidOffering("Storage uses variable pricing")
    if offering.pricing.model != PRICING_MODEL:
        raise InvalidOffering("wrong pricing model")
    if IDENTITY_PRECONDITION not in offering.preconditions:
        raise InvalidOffering("authenticated identity is required")

    pricing = offering.pricing
    info = offering.info
    terms = StorageTerms {
        minimumPrice: requireUint64(pricing.minimumPrice, "minimumPrice", 1),
        byteUsageFactor: validateRate(
            pricing.byteUsageFactor, "byteUsageFactor"),
        byteStorageDurationFactor: validateRate(
            pricing.byteStorageDurationFactor,
            "byteStorageDurationFactor"),
        retrievalByteUsageFactor: validateRate(
            pricing.retrievalByteUsageFactor,
            "retrievalByteUsageFactor"),
        renewalByteStorageDurationFactor: validateRate(
            pricing.renewalByteStorageDurationFactor,
            "renewalByteStorageDurationFactor"),
        removePrice: requireUint64(pricing.removePrice, "removePrice", 1),
        checkPrice: requireUint64(offering.checkPrice, "checkPrice", 1),
        maximumBytes: requireUint64(info.maximumBytes, "maximumBytes", 1),
        minimumRetentionSeconds: requireUint64(
            info.minimumRetentionSeconds, "minimumRetentionSeconds", 1),
        maximumRetentionSeconds: requireUint64(
            info.maximumRetentionSeconds, "maximumRetentionSeconds", 1),
        maximumTotalRetentionSeconds: requireUint64(
            info.maximumTotalRetentionSeconds,
            "maximumTotalRetentionSeconds", 1),
        maximumRetrieveBytes: requireUint64(
            info.maximumRetrieveBytes, "maximumRetrieveBytes", 1),
        checkResponseSeconds: requireUint64(
            info.checkResponseSeconds, "checkResponseSeconds", 1)
    }

    if terms.minimumRetentionSeconds > terms.maximumRetentionSeconds:
        raise InvalidOffering("minimum retention exceeds maximum")
    if terms.maximumRetentionSeconds > terms.maximumTotalRetentionSeconds:
        raise InvalidOffering("maximum retention exceeds total maximum")

    // Every input admitted by the advertised maxima must have a representable
    // price. Zero numerators are valid.
    calculateStorePrice(
        terms.maximumBytes, terms.maximumRetentionSeconds, terms)
    calculateRetrievePrice(terms.maximumRetrieveBytes, terms)
    calculateRenewPrice(
        terms.maximumBytes, terms.maximumRetentionSeconds, terms)

    return terms
```

The common Board validator remains responsible for the generic offering fields,
exact required-member rules, `creditIssuer`, IDs, descriptions, and unknown
extension fields. The Storage validator requires every Storage pricing and
`info` member shown in the normative offering.

---

## 4. Price calculation

```text
function calculateStorePrice(sizeBytes, retentionSeconds, terms):
    S = BigInteger(requireUint64(sizeBytes, "sizeBytes", 1))
    T = BigInteger(requireUint64(retentionSeconds, "retentionSeconds", 1))
    B = terms.byteUsageFactor
    X = terms.byteStorageDurationFactor

    // Add the two rational terms before applying one ceiling.
    numerator = S * B.numerator * X.denominator
              + S * T * X.numerator * B.denominator
    denominator = BigInteger(B.denominator) * X.denominator
    calculated = ceilNonnegativeFraction(numerator, denominator)
    return requirePriceFitsUint64(max(terms.minimumPrice, calculated))


function calculateRetrievePrice(length, terms):
    L = BigInteger(requireUint64(length, "length", 1))
    R = terms.retrievalByteUsageFactor
    calculated = ceilNonnegativeFraction(L * R.numerator, R.denominator)
    return requirePriceFitsUint64(max(terms.minimumPrice, calculated))


function calculateRenewPrice(sizeBytes, additionalSeconds, terms):
    S = BigInteger(requireUint64(sizeBytes, "sizeBytes", 1))
    A = BigInteger(requireUint64(additionalSeconds, "additionalSeconds", 1))
    N = terms.renewalByteStorageDurationFactor
    calculated = ceilNonnegativeFraction(
        S * A * N.numerator, N.denominator)
    return requirePriceFitsUint64(max(terms.minimumPrice, calculated))
```

Removal uses `terms.removePrice` exactly and a check uses `terms.checkPrice`
exactly. Compression, framing, encryption outside the stored value, and
physical allocation never enter these calculations.

---

## 5. Common selection, authorization, and lease state

```text
function selectCurrentFollowUpOffering(providerBoard, selection):
    offering = providerBoard.resolveImmutableSnapshot(selection)
    if offering is NONE:
        raise ServiceUnavailable
    terms = validateStorageOffering(offering)
    return OfferingSnapshot {
        offeringId: offering.id,
        revision: offering.revision,
        creditIssuer: offering.creditIssuer,
        terms: terms
    }


function authorizeLeaseLookup(authenticatedRequesterId, leaseId, now):
    requireFixedBytes(leaseId, LEASE_ID_SIZE, "leaseId")
    lease = LeaseStore.lookupForUpdateOrRead(leaseId)

    // Externally collapse missing and wrong-owner results.
    if lease is NONE or lease.requesterId != authenticatedRequesterId:
        rateLimitLeaseProbing(authenticatedRequesterId)
        raise UnauthorizedOrUnknownLease

    refreshLeaseState(lease, now)
    return lease


function refreshLeaseState(lease, now):
    requireUint64(now, "provider current time")
    if lease.state == ACTIVE and now >= lease.expiresAt:
        LeaseStore.atomicallyMarkExpired(lease)
        lease.state = EXPIRED


function requireActive(lease):
    if lease.state != ACTIVE:
        raise InactiveLease


function agreeAndReserveCredits(requesterId, offering, exactPrice):
    communicate(offering.creditIssuer, exactPrice)
    if requester does not accept that exact issuer and price:
        raise PriceRejected
    reservation = CreditReservations.reserve(
        requesterId, offering.creditIssuer, exactPrice)
    if reservation is ERROR:
        raise InsufficientAcceptedCredits
    return reservation
```

Follow-up operations use a currently advertised compatible provider offering,
not necessarily the offering that created the lease. The accepted snapshot is
immutable even if the Board changes during execution.

---

## 6. Store

```text
function validateStoreMetadata(input, terms):
    requireOperationFields(
        input,
        operation = "store",
        required = {"sizeBytes", "retentionSeconds", "contentHash", "data"},
        forbiddenKnownFields = FOLLOW_UP_ONLY_FIELDS)

    size = requireUint64(input.sizeBytes, "sizeBytes", 1)
    retention = requireUint64(
        input.retentionSeconds, "retentionSeconds", 1)
    hash = requireFixedBytes(input.contentHash, HASH_SIZE, "contentHash")

    if size > terms.maximumBytes:
        raise AdvertisedLimitExceeded
    if retention < terms.minimumRetentionSeconds
       or retention > terms.maximumRetentionSeconds:
        raise AdvertisedLimitExceeded

    return {sizeBytes: size, retentionSeconds: retention, contentHash: hash}


function providerStore(
    authenticatedRequesterId,
    localProviderId,
    selectedOfferingSnapshot,
    inputMetadata,
    inputByteStream,
    durableStore,
    clock
):
    offering = selectedOfferingSnapshot
    terms = offering.terms
    metadata = validateStoreMetadata(inputMetadata, terms)
    price = calculateStorePrice(
        metadata.sizeBytes, metadata.retentionSeconds, terms)
    reservation = agreeAndReserveCredits(
        authenticatedRequesterId, offering, price)

    receiving = durableStore.beginReceivingAttempt(metadata.sizeBytes)
    hasher = SHA256.new()
    received = 0

    while chunk = inputByteStream.readBoundedChunk():
        if received + length(chunk) > metadata.sizeBytes:
            abort receiving
            release reservation
            raise WrongUploadLength
        receiving.append(chunk)
        hasher.update(chunk)
        received = received + length(chunk)

    if received != metadata.sizeBytes or hasher.finish() != metadata.contentHash:
        abort receiving
        release reservation
        raise InvalidUpload

    acceptedAt = requireUint64(clock.currentUnixSeconds(), "acceptedAt")
    expiresAt = checkedAddUint64(acceptedAt, metadata.retentionSeconds)
    leaseId = generateUniqueLeaseId(durableStore)

    lease = Lease {
        leaseId: leaseId,
        requesterId: authenticatedRequesterId,
        providerId: localProviderId,
        originalOfferingId: offering.offeringId,
        originalOfferingRevision: offering.revision,
        sizeBytes: metadata.sizeBytes,
        contentHash: metadata.contentHash,
        acceptedAt: acceptedAt,
        expiresAt: expiresAt,
        storePrice: price,
        state: ACTIVE,
        bytesHandle: receiving.finalHandle
    }

    // Atomically make both exact bytes and lease metadata durable. Do not
    // report success while either exists only in volatile memory.
    if durableStore.commitReceivingAsActive(receiving, lease) is ERROR:
        abort receiving
        release reservation
        raise DurableCommitFailure

    output = {
        operation: "store", leaseId: leaseId,
        sizeBytes: lease.sizeBytes, contentHash: lease.contentHash,
        acceptedAt: acceptedAt, expiresAt: expiresAt, price: price
    }
    successfullyReturnCompleteOutput(output)
    CreditReservations.charge(reservation)
    return output
```

```text
function generateUniqueLeaseId(durableStore):
    loop:
        candidate = CSPRNG.randomBytes(LEASE_ID_SIZE)
        if not durableStore.containsLeaseId(candidate):
            return candidate
```

Any malformed metadata, refusal, interruption, length mismatch, hash mismatch,
time overflow, or failed durable commit releases the reservation and is not
charged. An interrupted retry is a new attempt and may receive a new lease ID.

---

## 7. Retrieve

```text
function providerRetrieve(
    authenticatedRequesterId, selectedCurrentOffering, input, clock
):
    requireOperationFields(
        input, "retrieve", {"leaseId", "offset", "length"},
        STORE_OR_RENEW_OR_REMOVE_ONLY_FIELDS)
    leaseId = requireFixedBytes(input.leaseId, LEASE_ID_SIZE, "leaseId")
    offset = requireUint64(input.offset, "offset")
    length = requireUint64(input.length, "length", 1)
    offering = selectedCurrentOffering

    if length > offering.terms.maximumRetrieveBytes:
        raise AdvertisedLimitExceeded

    lock lease for acceptance:
        lease = authorizeLeaseLookup(
            authenticatedRequesterId, leaseId, clock.currentUnixSeconds())
        requireActive(lease)
        if offset >= lease.sizeBytes or length > lease.sizeBytes - offset:
            raise InvalidRange
        price = calculateRetrievePrice(length, offering.terms)
        reservation = agreeAndReserveCredits(
            authenticatedRequesterId, offering, price)
        // Pin the immutable bytes so expiration or a later remove cannot
        // invalidate this timely accepted retrieval.
        pinnedRange = LeaseStore.pinRange(lease.bytesHandle, offset, length)

    data = pinnedRange.readExactly(length)
    if length(data) != length:
        release reservation
        raise RetrievalFailure

    output = {
        operation: "retrieve", leaseId: leaseId, offset: offset,
        data: data, contentHash: lease.contentHash, price: price
    }
    successfullyReturnCompleteOutput(output)
    CreditReservations.charge(reservation)
    release pinnedRange
    return output
```

Range validation uses subtraction rather than `offset + length`. A retrieval
accepted before expiration completes even when expiration occurs in transfer.
Incomplete or incorrect output is an uncharged service failure.

---

## 8. Renew

```text
function providerRenew(
    authenticatedRequesterId, selectedCurrentOffering, input, clock
):
    requireOperationFields(
        input, "renew",
        {"leaseId", "expectedExpiresAt", "additionalSeconds"},
        STORE_OR_RETRIEVE_OR_REMOVE_ONLY_FIELDS)
    leaseId = requireFixedBytes(input.leaseId, LEASE_ID_SIZE, "leaseId")
    expected = requireUint64(input.expectedExpiresAt, "expectedExpiresAt")
    additional = requireUint64(input.additionalSeconds, "additionalSeconds", 1)
    terms = selectedCurrentOffering.terms

    if additional < terms.minimumRetentionSeconds
       or additional > terms.maximumRetentionSeconds:
        raise AdvertisedLimitExceeded

    lock lease exclusively:
        lease = authorizeLeaseLookup(
            authenticatedRequesterId, leaseId, clock.currentUnixSeconds())
        requireActive(lease)
        if lease.expiresAt != expected:
            raise StaleExpectedExpiration

        newExpiresAt = checkedAddUint64(expected, additional)
        totalLimit = checkedAddUint64(
            lease.acceptedAt, terms.maximumTotalRetentionSeconds)
        if newExpiresAt > totalLimit:
            raise AdvertisedLimitExceeded

        price = calculateRenewPrice(lease.sizeBytes, additional, terms)
        reservation = agreeAndReserveCredits(
            authenticatedRequesterId, selectedCurrentOffering, price)

        // Persist the new expiration and success record atomically. A given
        // expected expiration can therefore succeed at most once.
        if LeaseStore.commitRenewal(
            lease, expectedExpiresAt = expected,
            newExpiresAt = newExpiresAt) is ERROR:
            release reservation
            raise RenewalFailure

        output = {
            operation: "renew", leaseId: leaseId,
            previousExpiresAt: expected, expiresAt: newExpiresAt,
            price: price
        }

    successfullyReturnCompleteOutput(output)
    CreditReservations.charge(reservation)
    return output
```

Rejected or failed renewal leaves the old expiration unchanged and is not
charged. Concurrent renewals and removal are serialized by the lease lock.

---

## 9. Remove

```text
function providerRemove(
    authenticatedRequesterId, selectedCurrentOffering, input, clock
):
    requireOperationFields(
        input, "remove", {"leaseId"}, ALL_OTHER_OPERATION_FIELDS)
    leaseId = requireFixedBytes(input.leaseId, LEASE_ID_SIZE, "leaseId")

    lock lease exclusively:
        lease = authorizeLeaseLookup(
            authenticatedRequesterId, leaseId, clock.currentUnixSeconds())
        requireActive(lease)
        price = selectedCurrentOffering.terms.removePrice
        reservation = agreeAndReserveCredits(
            authenticatedRequesterId, selectedCurrentOffering, price)

        if LeaseStore.atomicallyMarkRemoved(lease) is ERROR:
            release reservation
            raise RemovalFailure

        output = {
            operation: "remove", leaseId: leaseId,
            removed: true, price: price
        }

    successfullyReturnCompleteOutput(output)
    CreditReservations.charge(reservation)
    LeaseStore.mayReclaimPhysicalBytes(lease.bytesHandle)
    return output
```

Logical removal is immediate and ends CR2SE retrieval; it is not a secure
physical-erasure guarantee. Removing an unknown, expired, or already removed
lease fails without charge and does not replay the earlier success response.

---

## 10. Paid byte check

```text
function requesterCheck(
    authenticatedConnection,
    originalLeaseRecord,
    selectedCurrentOffering,
    offset,
    localClock
):
    leaseId = requireFixedBytes(
        originalLeaseRecord.leaseId, LEASE_ID_SIZE, "leaseId")
    offset = requireUint64(offset, "offset")
    if offset >= originalLeaseRecord.sizeBytes:
        raise InvalidOffset
    if originalLeaseRecord.originalBytes are unavailable locally:
        return localUnchargedResult(CHECK_INCONCLUSIVE, leaseId, offset)

    price = selectedCurrentOffering.terms.checkPrice
    accept selectedCurrentOffering.creditIssuer and price
    checkSession = authenticatedConnection.openPricedCheckSession(
        selectedCurrentOffering, price)
    started = localClock.monotonicNow()
    checkSession.sendCompleteChallenge({leaseId, offset})
    response = checkSession.receiveCheckResultOrFailure()
    elapsed = localClock.monotonicNow() - started

    if elapsed > selectedCurrentOffering.terms.checkResponseSeconds:
        return validCheckResult(CHECK_INCONCLUSIVE, leaseId, offset)
    if response is authenticated provider evidence
       and response.leaseId == leaseId
       and response.offset == offset
       and response.value is exactly one byte:
        if response.value == originalLeaseRecord.originalBytes[offset]:
            return validCheckResult(
                CHECK_PASS, leaseId, offset, value = response.value)
        return validCheckResult(
            CHECK_FAIL, leaseId, offset, value = response.value)
    if response is authenticated report that the authorized active lease
       or challenged byte is unavailable:
        return validCheckResult(CHECK_FAIL, leaseId, offset)
    return validCheckResult(CHECK_INCONCLUSIVE, leaseId, offset)
```

```text
function providerAnswerCheck(
    authenticatedRequesterId,
    selectedCurrentOffering,
    preacceptedCheckSession,
    challenge,
    clock
):
    // The fixed check issuer and price were accepted and reserved while
    // opening this session, before the requester disclosed the offset.
    require preacceptedCheckSession.offering == selectedCurrentOffering
    reservation = preacceptedCheckSession.creditReservation
    requireExactCheckFields(challenge, {"leaseId", "offset"})
    leaseId = requireFixedBytes(challenge.leaseId, LEASE_ID_SIZE, "leaseId")
    offset = requireUint64(challenge.offset, "offset")

    enforceAtMostOneOverlappingCheckPerLeaseIfConfigured(leaseId)
    enforceNoUndisclosedIntervalLongerThanOneSecond(leaseId)

    lock lease for acceptance:
        lease = authorizeLeaseLookup(
            authenticatedRequesterId, leaseId, clock.currentUnixSeconds())
        requireActive(lease)
        if offset >= lease.sizeBytes:
            raise InvalidOffset
        pinnedByte = LeaseStore.pinRange(lease.bytesHandle, offset, 1)

    evidence = {leaseId: leaseId, offset: offset, value: pinnedByte.readExactly(1)}
    if evidence.value is not exactly one byte:
        // The invocation layer may return an authenticated unavailable report;
        // it must never invent or echo an expected byte.
        returnUnavailableCheckResult()
    successfullyReturnCompleteEvidence(evidence)
    settleSuccessfullyCompletedCheckAccordingToCommonCheckRules(reservation)
    return evidence
```

The requester starts its timer only after sending the complete unpredictable
challenge and computes the outcome itself. A valid completed check result may
be charged whether it is `pass`, `fail`, or `inconclusive`; malformed input,
authentication failure, invalid offset, or execution that returns no valid
check result is not charged. Expiration timing ambiguity and communication
failure are inconclusive. A passing byte proves only timely availability of
that byte at that time.

---

## 11. Expiration, recovery, and clock behavior

```text
function recoverDurableLeasesOnStartup(clock):
    now = requireUint64(clock.currentUnixSeconds(), "current time")
    for each durable lease:
        if lease metadata or bytes fail integrity checks:
            quarantine lease and report local storage failure
        else:
            refreshLeaseState(lease, now)


function expireDueLeases(clock):
    now = requireUint64(clock.currentUnixSeconds(), "current time")
    for each ACTIVE lease with expiresAt <= now:
        lock lease exclusively:
            refreshLeaseState(lease, now)
```

The provider clock determines lease times. Its wall clock must track UTC, while
the implementation must preserve accepted retention across clock corrections;
an adjustment must not make remaining retention decrease faster than real
elapsed time. At `expiresAt`, availability ends without a grace period.
Internally retained expired bytes do not reactivate a lease.

---

## 12. Operation fields and service-definition consistency

```text
KNOWN_INPUT_FIELDS = {
    "operation", "leaseId", "sizeBytes", "retentionSeconds", "contentHash",
    "data", "offset", "length", "expectedExpiresAt", "additionalSeconds"
}

function requireOperationFields(input, operation, required, forbiddenKnownFields):
    require input is an object
    if input.operation != operation:
        raise InvalidOperation
    for each field in required:
        if field is absent:
            raise MissingRequiredField(field)
    for each field in KNOWN_INPUT_FIELDS - ({"operation"} union required):
        if field is present:
            raise FieldForbiddenForOperation(field)
    preserve unknown fields under the Services compatible-extension rule


function validateStorageServiceDefinition(offering, definition):
    require definition.id == offering.id
    require definition.description == offering.description
    require definition.service == SERVICE_ID
    require definition.serviceVersion == SERVICE_VERSION
    require schemas are structurally equivalent to Storage section 13
    require the input operation descriptions and discriminant rules cover
        exactly store, retrieve, renew, and remove
    require the separate check schema has exact leaseId, offset, outcome,
        and optional one-byte value semantics
```

Language-specific functions and bounded streaming transports may replace the
logical JSON shape, but they must preserve exact values, operation-specific
required and forbidden known fields, compatible unknown fields, and complete
output semantics.

---

## 13. Failure, settlement, and concurrency invariants

```text
for every store, retrieve, renew, or remove:
    validate authentication, current offering, metadata, limits, state,
        exact price, accepted credits, and local policy before acceptance;
    on failure before complete successful output, release reserved credits;
    charge only after complete successful output;
    never mutate an existing lease on rejected or failed work

serialize on one lease:
    renew against renew;
    renew against remove;
    acceptance of retrieve/check against remove and expiration

after timely retrieve/check acceptance:
    preserve the accepted operation's pinned bytes through completion even if
        remove or expiration is ordered later

never reveal across an unauthorized boundary whether:
    a lease ID exists;
    its owner, size, hash, expiration, or state;
    or its bytes remain physically present
```

Capacity, trust, concurrency, rate, and security policy may reject work before
acceptance, but may not evade an accepted lease obligation. Check rate policy
may reject overlapping checks and impose at most a one-second minimum interval;
no stricter undisclosed frequency limit is conforming.

---

## 14. Confidentiality and storage boundaries

```text
storedBytes = exactly the requester-supplied data bytes
contentHash = SHA256(storedBytes)
prices, offsets, and sizes apply to storedBytes

if requester requires confidentiality:
    storedBytes = authenticatedRequesterSideEncryption(plaintext)
    retain encryption key and format metadata outside the Storage provider
```

Storage itself neither encrypts nor decrypts. Plaintext storage is conforming,
and encryption keys must not be disclosed merely to use Storage. Internal
compression, replication, erasure coding, or remote backing is permitted only
when exact logical bytes and accepted behavior remain unchanged.

---

## 15. Minimum conformance cases

An implementation should test at least:

```text
accepting all zero rate numerators while requiring positive denominators;
rejecting zero minimumPrice, removePrice, checkPrice, and all zero limits;
rejecting wrong service/version/model, fixed price, missing identity
    precondition, missing required Storage terms, and invalid limit ordering;
single-round store vector S=1, T=1, B=1/2, X=1/2 producing price 1;
store, retrieve, and renew prices at advertised maxima fitting uint64;
rejecting any exact calculated price or time addition above UINT64_MAX;
never using floating point for rates or JSON uint64 values;
rejecting zero-size store, wrong declared length, extra bytes, short upload,
    and SHA-256 mismatch without charge or lease creation;
not reporting store success before durable bytes and metadata survive restart;
generating unpredictable 32-byte provider-unique lease IDs;
returning exact whole and partial ranges and the whole-object SHA-256 hash;
rejecting zero-length, over-limit, out-of-range, and overflow-shaped retrievals;
completing a retrieval accepted immediately before expiration;
renewing only an active lease with matching expectedExpiresAt;
allowing at most one concurrent renewal for the same expectedExpiresAt;
enforcing both extension and total-retention limits with safe addition;
serializing renew/remove and making later operations observe the ordering;
logical removal without claiming secure physical erasure or issuing a refund;
rejecting repeat removal without replaying success or charging;
authorization by authenticated requester identity across new connections;
indistinguishable errors for unknown leases and leases owned by another ID;
random valid byte checks returning pass for every sampled original byte;
wrong evidence returning fail and timeout/ambiguous communication returning
    inconclusive, with the requester computing the outcome;
never sending the expected byte in a challenge;
using each current follow-up offering's issuer, price, limits, and timeout;
honoring an accepted immutable offering snapshot after Board withdrawal;
charging completed successful operations only and releasing reservations for
    every specified service failure;
expiration at now == expiresAt and no implicit grace-period reactivation;
startup recovery of active and expired leases;
preserving stored ciphertext exactly without requiring provider-side keys;
and rejecting known fields belonging to a different operation while applying
    compatible-extension handling to unknown fields.
```
