# Messaging pseudocode

This document translates [`Messaging.md`](../Messaging.md) into
implementation-neutral algorithms. The specification remains authoritative.
All inputs, stored payloads, signatures, times, identifiers, and check evidence
are untrusted.

## 1. State and message validation

```text
SERVICE_ID = "cr2se.messaging"
SERVICE_VERSION = 1
PRICING_MODEL = "cr2se.messaging.v1"
SIGNING_PREFIX = ASCII("CR2SE-MESSAGE-V1")

Placement:
    placementId; message; providerId; offeringSnapshot
    acceptedAt; expiresAt; cumulativeStoreAndRenewalPrice
    state = RECEIVING | PENDING | RECOVERED | REMOVED | EXPIRED
    cachedFirstRecoveryOutput or NONE
```

```text
function messageSigningBytes(m):
    code = {"opaque":0x00, "cr2se.identity-encrypted.v1":0x01}[m.payloadEncoding]
    return SIGNING_PREFIX || m.messageId || m.senderId || m.recipientId
        || uint64_be(m.senderCreatedAt) || byte(code)
        || uint64_be(m.payloadSize) || m.payloadHash || m.payload

function validateMessage(m, authenticatedSender, maximumPayloadBytes):
    require all IDs/hashes are 32 bytes and signature is 64 bytes
    require m.senderId == authenticatedSender
    require Identity.deriveVersion1Id(m.senderPublicKey) == m.senderId
    require 1 <= m.payloadSize <= maximumPayloadBytes
    require length(m.payload) == m.payloadSize
    require SHA256(m.payload) == m.payloadHash
    require Ed25519.verify(m.senderPublicKey, messageSigningBytes(m),
                           m.senderSignature)
```

## 2. Offering and prices

Validation requires exact service/version/model, provider as `creditIssuer`,
the identity precondition, all four rational factors, positive fixed operation
prices and `checkPrice`, all limits, and `minimumRetention <= maximumRetention
<= maximumTotalRetention`. Using arbitrary precision:

```text
store(S,T) = max(M, ceil(S*B.n/B.d + S*T*X.n/X.d))
recover(S) = max(M, ceil(S*R.n/R.d))
renew(S,A) = max(M, ceil(S*A*N.n/N.d))
discover, status, remove, check = their advertised exact prices
```

Add rational store terms before one ceiling. Every result must fit uint64, and
the exact issuer and price are agreed before acceptance or a large transfer.

## 3. Store, discover, and recover

```text
function store(authenticatedSender, offering, input):
    validateMessage(input, authenticatedSender, terms.maximumPayloadBytes)
    require retention in advertised bounds
    acceptedAt = currentUnixSeconds(); expiresAt = checkedAdd(acceptedAt, retention)
    price = store(input.payloadSize, retention)
    reserveCharge(authenticatedSender, providerId, price)
    placementId = CSPRNG unique 32-byte identifier
    durably commit complete immutable message and PENDING placement atomically
    commit charge; return {operation:"store", placementId,
                           acceptedAt, expiresAt, price}

function discover(authenticatedRecipient, offering, cursor, limit):
    require 1 <= limit <= maximumDiscoverResults
    select PENDING placements with recipientId == authenticatedRecipient,
        strictly after cursor, in normative (acceptedAt, placementId) order
    reserve discoverPrice
    return bounded metadata page without payloads and commit

function recover(authenticatedRecipient, offering, placementId, requestId):
    lock placement
    require placement.recipientId == authenticatedRecipient
    if same successful recovery request is retried:
        return cachedFirstRecoveryOutput without second charge
    require placement.state == PENDING and not expired
    price = recover(placement.message.payloadSize)
    reserve price; stream and validate complete signed message
    atomically set RECOVERED and cache exact output before committing charge
    return cached output
```

Unauthorized answers do not reveal existence. The first recovery changes state;
idempotent retry semantics prevent duplicate recovery charging.

## 4. Status, renewal, removal, and expiry

```text
function status(authenticatedSender, offering, placementId):
    require placement.senderId == authenticatedSender
    reserve statusPrice; return current state/times and commit

function renew(authenticatedSender, offering, placementId, addSeconds):
    lock placement; require sender authorization and PENDING state
    require addSeconds within current offering duration bounds
    newExpiry = checkedAdd(placement.expiresAt, addSeconds)
    require newExpiry <= placement.acceptedAt + maximumTotalRetentionSeconds
    price = renew(payloadSize, addSeconds); reserve price
    durably set newExpiry and cumulative price; commit charge

function remove(authenticatedSender, offering, placementId, now):
    lock placement; require sender authorization and PENDING state
    reserve removePrice
    earlyReleaseCredit = calculateNormativeUnusedRetentionCredit(
        placement, now) // bounded by prior eligible storage charges
    atomically set REMOVED, release bytes, apply credit, commit remove charge
    return exact state, release credit, and price

function expire(now):
    atomically mark pending placements with expiresAt <= now as EXPIRED
    release bytes; keep only policy/tombstone data allowed by specification
```

Failures do not charge or mutate terminal state. Recovered metadata and cached
first-recovery output remain until expiration solely for authorized retry.

## 5. Encryption and check

```text
function encryptPayload(mMetadata, recipientCredential, plaintext):
    Encryption.validateEncryptionPublicCredential(recipientCredential)
    metadata = ASCII("CR2SE-MESSAGE-ENCRYPTION-METADATA-V1")
        || messageId || senderId || recipientId || uint64_be(senderCreatedAt)
    ephemeral = X25519.generateKeyPair(CSPRNG); nonce = randomBytes(24)
    shared = X25519(ephemeral.private, recipientCredential.x25519PublicKey)
    key = HKDF_SHA256(shared, SHA256(metadata),
                     ASCII("CR2SE-MESSAGE-PAYLOAD-KEY-V1"), 32)
    sealed = XChaCha20Poly1305.encrypt(key, nonce, plaintext, metadata)
    return 0x01 || recipient key || ephemeral.public || nonce || sealed
```

Erase ephemeral secrets. Decryption verifies the embedded recipient key and
AEAD tag before releasing plaintext. Encryption hides neither metadata nor
traffic patterns.

The paid Messaging check is sender-authorized and returns bounded evidence that
a pending placement was retained at the challenge time, within
`checkResponseSeconds`. The requester independently validates placement ID,
message hash/signature, provider response, freshness, and agreed check price.
Contradiction is `FAIL`; unavailable evidence is `INCONCLUSIVE`. A check does
not recover the payload, alter state, reverse charges, or settle disputes.

## 6. Availability check

```text
function checkPendingPlacement(authenticatedSender, offering, placementId):
    placement = requireAuthorizedPendingPlacement(
        placementId, authenticatedSender)
    offset = CSPRNG.uniformInteger(0, placement.message.payloadSize - 1)
    start timer after sending complete {placementId, offset}
    reserve current offering.checkPrice
    evidence = provider.readExactlyOnePayloadByte(placementId, offset)
    if no valid result completes: release reservation; return INCONCLUSIVE
    commit check charge
    if evidence arrives after terms.checkResponseSeconds: return INCONCLUSIVE
    if evidence.placementId != placementId or evidence.offset != offset:
        return FAIL
    if evidence.value == originalPayload[offset]: return PASS
    return FAIL
```

Only the authenticated sender may check a still-pending placement. A passing
sample proves one byte was returned once, not complete or continuous storage.
