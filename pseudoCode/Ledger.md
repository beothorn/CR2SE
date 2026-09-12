# Ledger pseudocode

This document translates [`Ledger.md`](../Ledger.md) into implementation-neutral
state transitions. The specification remains authoritative. A ledger is local,
durable state; there is no global balance, consensus, or synchronization
protocol.

## 1. State and invariants

```text
UINT64_MAX = 18_446_744_073_709_551_615

LedgerState:
    localIdentityId             canonical CR2SE ID
    ownedByIssuer               Map<identityId, uint64>
    issuedToOwner               Map<identityId, uint64>
    trustByIdentity             Map<identityId, real in [0, 1]>
    processedTransferIds        durable Set<bytes>
    claims                      durable Map<claimId, ClaimRecord>
    reservations               durable Map<reservationId, Reservation>

ClaimRecord:
    claimId                     unguessable identifier
    amount                      uint64 greater than zero
    secretCommitment            cryptographic digest
    state                       AVAILABLE | REDEEMED | INVALIDATED
    restrictions                local issuer policy
```

Owned credits are credits issued by another identity that the local identity
believes it owns. Issued credits are local-identity credits believed to be
owned by another identity. They are never merged.

```text
function checkedAdd(balance, amount):
    require both are exact uint64 values
    if amount > UINT64_MAX - balance: raise CreditOverflow
    return balance + amount

function checkedSubtract(balance, amount):
    require both are exact uint64 values
    if amount > balance: raise InsufficientCredits
    return balance - amount

function assertLedgerInvariants(state):
    require every balance is in 0 .. UINT64_MAX
    require every trust value is finite and in [0, 1]
    require no claim is both redeemable and terminal
    require reservation totals never permit a spendable balance below zero
```

## 2. Atomic balance operations

```text
function receiveCreditsIssuedBy(issuerId, amount, durableStore):
    require issuerId != localIdentityId
    require amount > 0
    transaction durableStore:
        old = ownedByIssuer.getOrDefault(issuerId, 0)
        ownedByIssuer[issuerId] = checkedAdd(old, amount)
        persist before success

function issueLocalCreditsTo(ownerId, amount, durableStore):
    require ownerId != localIdentityId and amount > 0
    transaction durableStore:
        old = issuedToOwner.getOrDefault(ownerId, 0)
        issuedToOwner[ownerId] = checkedAdd(old, amount)
        persist before success

function chargeForLocalService(requesterId, creditIssuerId, amount):
    require amount > 0
    if creditIssuerId == localIdentityId:
        // Requester spends credits the local identity issued to it.
        transaction:
            issuedToOwner[requesterId] = checkedSubtract(
                issuedToOwner.getOrDefault(requesterId, 0), amount)
    else:
        // Exact mechanics require agreement with that issuer; do not invent
        // authority over a third party's ledger.
        applyConfiguredIssuerSettlementAtomically(
            requesterId, creditIssuerId, localIdentityId, amount)
```

A service must reserve sufficient balance before acceptance, commit exactly
once only after success, and release on failure.

```text
function reserveCharge(payerId, issuerId, amount):
    lock relevant balance
    require amount <= spendableBalance(payerId, issuerId)
    reservation = new unique pending reservation
    durably reduce spendable capacity by amount
    return reservation

function commitReservation(reservation):
    transaction: require PENDING; apply debit exactly once; mark COMMITTED

function releaseReservation(reservation):
    transaction: if PENDING, restore capacity and mark RELEASED
```

## 3. Transfer orders and replay safety

```text
function createTransferOrder(issuerId, recipientId, amount, nonce, expiry):
    require amount > 0 and identities and time fields are valid
    canonical = canonicalTransferBytes(
        version, issuerId, localIdentityId, recipientId, amount, nonce, expiry)
    return {fields..., signature: Identity.sign(canonical)}

function processTransferOrder(order, authenticatedSender, now):
    validate canonical fields, issuer, identities, amount, and time
    require authenticatedSender == order.currentOwnerId
    require Identity.verify(order.currentOwnerId, canonicalTransferBytes(order),
                            order.signature)
    transferId = SHA256(canonicalTransferBytes(order) || order.signature)

    transaction:
        if transferId in processedTransferIds: return priorResult
        enforce local issuer authority and transfer policy
        fee = configuredTransferFee(order); require fee < order.amount
        issuedToOwner[order.currentOwnerId] = checkedSubtract(
            issuedToOwner[order.currentOwnerId], order.amount)
        issuedToOwner[order.recipientId] = checkedAdd(
            issuedToOwner.getOrDefault(order.recipientId, 0),
            order.amount - fee)
        add transferId and result to durable replay table
    return result
```

Only the issuer can authoritatively update ownership of its credits. Validation
includes the exact representation defined by the application/protocol using a
transfer order; this pseudocode does not introduce a new wire format.

## 4. Credit claims

```text
function createClaim(amount, restrictions):
    require amount > 0
    secret = CSPRNG.randomBytes(policy.claimSecretBytes)
    claimId = uniqueIdentifier()
    transaction:
        reserve amount of local issued-credit capacity
        claims[claimId] = {claimId, amount, SHA256(secret), AVAILABLE,
                           restrictions}
    return {issuerId: localIdentityId, claimId, secret, amount}

function redeemClaim(claim, redeemerId):
    require claim.issuerId == localIdentityId
    transaction with claim row locked:
        record = claims[claim.claimId] or reject UnknownClaim
        require record.state == AVAILABLE
        require constantTimeEqual(SHA256(claim.secret), record.secretCommitment)
        require restrictionsPermit(record, redeemerId, currentTime())
        issuedToOwner[redeemerId] = checkedAdd(
            issuedToOwner.getOrDefault(redeemerId, 0), record.amount)
        consume claim reservation
        record.state = REDEEMED
        persist all changes atomically
    return record.amount

function invalidateClaim(claimId):
    transaction with claim row locked:
        require claims[claimId].state == AVAILABLE
        claims[claimId].state = INVALIDATED
        release its reserved capacity
```

A claim transfers its entire amount and can succeed once. Possession is not a
global guarantee: the issuer may refuse or invalidate an unredeemed claim.

## 5. Trust

```text
function getTrust(identityId):
    return trustByIdentity.getOrDefault(identityId, 0.0)

function setTrust(identityId, value):
    require value is finite and 0 <= value <= 1
    transaction: trustByIdentity[identityId] = value

function authorizeService(identityId, baseTerms):
    trust = getTrust(identityId)
    if trust == 0: return REFUSE
    return localPolicy.priceAndLimits(baseTerms, trust)
```

Trust is asymmetric, starts at zero, and is determined solely by local policy.
Third-party reports are input to that policy, not consensus or proof. Maximum
trust need not make a service free, and nonzero trust does not compel service.

## 6. Persistence and concurrency

All successful mutations must be durable before acknowledgement. Locks or
serializable transactions must prevent lost updates, double spending, claim
double redemption, and reservation races. Multiple nodes sharing one identity
must use a coordination mechanism that preserves the same invariants; otherwise
they must not claim one coherent ledger. Cryptographic evidence never overrides
the local ledger or issuer policy.
