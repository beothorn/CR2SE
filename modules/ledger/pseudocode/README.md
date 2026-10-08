# Ledger pseudocode

The [specification](../README.md) owns formats and authority. These algorithms
describe durable local transitions, not a global transaction across peers.

```text
Ledger:
    ownedByIssuer: Map<identity, uint64>
    issuedToOwner: Map<identity, uint64>
    trust: Map<identity, value in [0,1]>, default 0
    reservations: durable Map<localOperationKey, reservation>
    transfers: durable Map<(ownerId, transferId), (orderBytes, result)>
    claims: durable Map<claimId, (secretHash, amount, state, owner, result)>
    journal: durable local service effects and settlement state

function reserveSettlement(requester, provider, issuer, maximum):
    require maximum > 0 and maximum fits uint64
    require provider's trust in requester > 0
    if requester == provider:
        reserve finite internal resource budget; return INTERNAL
    if issuer == provider:
        atomically reserve maximum from recognized spendable issued balance
        return SPEND_PROVIDER_CREDITS
    if issuer == requester:
        require provider explicitly accepts requester credits
        atomically reserve finite requester issuance capacity
        require recipient balance has room for maximum
        return ISSUE_REQUESTER_CREDITS
    require provider explicitly accepts third-party settlement risk
    reserve local owned credits for maximum plus agreed fee
    return THIRD_PARTY_PENDING

function commitSettlement(key, finalPrice):
    transaction:
        reservation = require key exists
        if already COMMITTED: return prior result
        require 1 <= finalPrice <= reservedMaximum
        apply exact mode-specific balance changes with checked arithmetic
        third-party mode remains UNSETTLED until issuer confirms transfer
        journal result and local service effect consistently
        release unused capacity and persist state

function failBeforeCommit(key):
    transaction:
        if still PENDING: release reservation; mark FAILED
        else: preserve committed state; report OUTCOME_UNKNOWN
```

Only update the ledger controlled by this node. The corresponding peer makes
its own update. A lost response can leave different views. Included checks and
recognized result retransmissions use their existing paid entitlement instead
of creating a zero-price service reservation.

```text
function createTransfer(issuer, newOwner, amount):
    transferId = randomBytes(16)
    bytes = 0x01 || transferId || issuer || localId || newOwner
        || uint64be(amount)
    require length(bytes) == 121 and amount > 0
    return {order:bytes, ownerPublicKey:localPublicKey,
            signature:Ed25519.sign(localPrivateKey, bytes)}

function prepareTransfer(caller, order, publicKey, signature, maximumFee):
    parse exact 121 bytes; require version == 1
    require caller == order.owner and order.issuer == localId
    require deriveId(publicKey) == order.owner
    require valid signature over exact order bytes
    require amount > 0 and newOwner not in {owner, issuer}
    key = (owner, transferId)
    if key already accepted:
        require bytes equal stored order; return stored result without charge
    fee = localPolicy.quoteFee(order)
    require 0 <= fee < amount and fee <= maximumFee
    send fee quote; require owner's exact acceptance on this stream
    transaction:
        recheck replay key under lock
        require amount <= spendableIssuedBalance(owner)
        subtract amount from issuedToOwner[owner]
        add amount-fee to issuedToOwner[newOwner], rejecting overflow
        persist order and result under key atomically
    return result

function createClaim(amount):
    claimId = randomBytes(32); secret = randomBytes(32)
    transaction:
        reserve finite issuance capacity
        persist unique claimId, SHA256(secret), amount, AVAILABLE
    return {issuerId:localId, claimId, secret, amount}

function redeemClaim(caller, envelope):
    plaintext = authenticatedGenericDecrypt(envelope)
    parse exact domain prefix || issuerId || ownerId || claimId || secret
    require issuerId == localId and ownerId == caller
    transaction with claim locked:
        require constantTimeEqual(SHA256(secret), storedSecretHash)
        if REDEEMED and storedOwner == caller: return stored result
        require AVAILABLE and issuer restrictions permit caller
        add claim amount to issuedToOwner[caller], rejecting overflow
        consume reservation; mark REDEEMED; store owner and result
    return result

function invalidateClaim(claimId):
    transaction: require AVAILABLE; mark INVALIDATED; release capacity
```

Keep accepted transfers and terminal claim records for the ledger lifetime.
Never reset a transfer replay table while continuing its balances. Trust updates
are explicit local policy; accepting a signature or redeeming a claim does not
automatically raise trust. A bootstrap policy may deliberately grant nonzero
trust under a finite resource budget.
