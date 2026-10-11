# Ledger

## TLDR

The Ledger tracks credits, spending limits, reservations, and payments. Since each identity issues its own credits, balances are kept separate for each issuer. Read the [short guide](./tldr.md).

## Module boundary

**Required** in the [minimum useful node profile](../../ModuleContracts.md#required-and-optional-capabilities).
Owns trust, balances, reservations and accounting replay state. Consumes
Identity/Cryptography and local durable persistence; Services coordinates
service effects through its ports.

Implement against the [input contract](./inputs/README.md) and
[output contract](./outputs/README.md), using the shared
[composition and recovery rules](../../ModuleContracts.md).
This boundary supports a monolith, separate logical components or separate
processes without changing the service or wire contract below.

Use the [acceptance test pseudocode](./acceptanceTests/README.md) to guide
implementation and check its observable results.

The ledger is one identity's durable record of credits and trust. Credits are
issued by individual identities; they are not a global currency. There is no
central ledger, consensus, guaranteed exchange rate, or forced reconciliation.

See [pseudocode](./pseudocode/README.md), [diagrams](./diagrams/README.md), and
[Peer Protocol](../peer-protocol/README.md) for the control messages.

## Balances and authority

Keep two separate maps:

| Map | Meaning for local identity Alice |
|---|---|
| `ownedByIssuer[Bob]` | Bob credits Alice believes she owns. |
| `issuedToOwner[Bob]` | Alice credits Alice recognizes as owned by Bob. |

Each balance is an integer `0..2^64-1`. Credits from different issuers must
never be added into one protocol balance. Reject overflow and underflow.
An issuer controls the credits it recognizes and may refuse transfers or revoke
credits by policy. A signature does not override that authority. Dishonest
issuers can lose local trust; the protocol cannot force them to honor promises.

Each peer maintains its own view. Alice's issued balance for Bob and Bob's owned
balance from Alice normally correspond but may disagree after failures or
policy changes. Balance queries report the issuer's view; they do not silently
overwrite a local view while operations are in flight.

## Payment modes

Before accepting work, both parties agree which mode applies:

| Issuer | Successful settlement |
|---|---|
| Provider | Provider subtracts price from `issuedToOwner[requester]`; requester subtracts it from `ownedByIssuer[provider]`. |
| Requester | Requester issues price to provider; provider adds it to `ownedByIssuer[requester]`. |
| Third identity | Requester sends a signed transfer to that issuer; provider recognizes payment only from an authenticated issuer receipt. |

The requester-issued case is how wanted work earns credits. Reserve finite
issuance capacity before acceptance; do not require the requester to own its
own currency. The provider must explicitly trust and accept that issuer.
Messaging restricts its offerings to provider-issued credits.

For third-party payment, the provider accepts the risk that the issuer may
refuse settlement after successful work. Agree an exact transfer fee first.
After successful output, the requester submits a transfer for `price + fee`;
the issuer delivers `price` to the provider and keeps `fee`. Reject overflow.
Record an issuer refusal or lost response as unsettled/unknown, not a successful
payment. There is no distributed escrow or atomic fair exchange in version 1.
A provider may refuse this mode. The first PoC can exercise the two-party modes
before adding issuer-mediated transfers.

Operations between nodes with the same identity still have a positive quoted
price. Record internal resource use separately with finite local budgets; do
not create owned/issued self-balances or pretend this earns external credits.

## Reservation and persistence

Reserve spendable credits or issuance capacity before accepting work. Concurrent
operations must not spend the same capacity twice. For metered computation,
reserve the maximum, settle the final price, and release the remainder.

Durably journal the accepted terms, reservation, local operation key, service
state, result metadata, and settlement state. A local operation key includes
the authenticated requester and connection/stream instance; it is not inferred
from identical input. Commit each local debit or issuance at most once.

Explicit failure before success releases the reservation without charging.
Commit durable state changes and their local ledger effect together, or use a
recoverable journal that produces the same result after restart. A socket write
and a database transaction cannot be one atomic action. If a complete response
may have been lost, retain the committed result and report outcome unknown.
Do not promise exactly-once execution across peers.

Accepted transfer replay IDs and consumed claim records are durable. Other
historical accounting can be compacted when it no longer protects obligations,
retries, or balances. Multiple nodes sharing an identity need one coordinated
writer or equivalent transactional replication. Copying keys is insufficient.

## Transfers: one canonical format

The current owner authorizes an issuer to assign credits to a new owner. The
only version 1 unsigned transfer format is exactly 121 bytes:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 1 | Version `0x01` |
| 1 | 16 | Fresh cryptographically random transfer ID |
| 17 | 32 | Issuer ID |
| 49 | 32 | Current owner ID |
| 81 | 32 | New owner ID |
| 113 | 8 | Positive amount, unsigned big-endian |

The owner signs exactly these bytes using Ed25519. Send the 32-byte owner public
key and 64-byte signature alongside the order, not inside its signed bytes.
The former 105-byte layout without a transfer ID is not valid version 1.
There are no signed expiry or extra nonce fields.

The issuer authenticates the current owner, checks the derived ID and signature,
and quotes a fee `0 <= fee < amount`. The owner accepts that fee on the same
authenticated control stream before commitment. `amount` includes the fee;
the new owner receives `amount - fee`. Transfers to the current owner or issuer
are rejected; paying the issuer uses ordinary service spending instead.

Atomically subtract amount from the owner's available issued balance, add the
net amount to the new owner's issued balance, and record the result under
`(currentOwnerId, transferId)`. Duplicate accepted orders return that result
without a second charge. The same key with different order bytes is a conflict.
Retain accepted replay records for the lifetime of the issuer ledger because
orders have no expiry. A refused order changes no balance.

The new owner need not be online. It may later query the issuer for the result
or its recognized balance. Only the original owner and new owner may retrieve
the transfer result. The issuer's authenticated response is evidence of its
current accounting, not globally enforceable money.

## Credit claims

A claim is a single-use bearer secret issued to bootstrap a relationship or
give credits without choosing an owner in advance. It is not an identity key.

Create a random 32-byte `claimId` and independent random 32-byte `secret`.
Store `SHA-256(secret)`, the positive amount, state, and any issuer restrictions.
The portable claim contains issuer ID, claim ID, secret, and amount. The issuer's
stored amount is authoritative. Creation reserves finite issuance capacity.

For copying or QR transfer, the portable form is `cr2se-claim:` followed by
padded RFC 4648 Base64 of exactly `0x01 || issuerId || claimId || secret ||
uint64be(amount)`: 105 bytes in total. Reject other versions, wrong lengths,
noncanonical Base64, and a zero amount. This form is secret bearer material.
Deliver it through a trusted private channel; it is not a public contact QR.

Redemption authenticates the new owner and sends the claim ID and secret
encrypted for the issuer, using the generic identity-encryption envelope.
The plaintext is exactly `ASCII("CR2SE-CLAIM-REDEEM-V1") || issuerId || ownerId
|| claimId || secret`. Each ID and secret is 32 bytes. Check the connection
owner against the embedded owner. Transport integrity alone does not hide a
bearer secret. Never put claims in logs, Boards, or public discovery records.

Under one transaction, verify the commitment and policy, add the amount to the
owner's issued balance, consume the capacity reservation, and mark the claim
redeemed. A retry with the same secret and owner returns the original result;
another owner cannot redeem it again. Retain its terminal record to prevent
reuse. An issuer may invalidate an unredeemed claim and release its reservation.

## Trust and bootstrap

Trust is a local, asymmetric value in `[0,1]`. Unknown identities start at zero;
a provider must not supply a paid service while its trust in that requester
is zero. Valid authentication or a large claimed balance is not trust.

This rule does not prohibit bounded handshakes, Board/definition retrieval,
claim redemption, or wanted-service negotiation. These are rate-limited control
operations, not unlimited free resource services.

A new relationship can begin in either of these ways:

- An operator explicitly assigns nonzero trust and a finite credit grant or
  claim. Redeeming a claim does not automatically change trust; the issuer's
  configured bootstrap policy must do so before services become available.
- Bob offers to fulfill Alice's wanted service. Bob decides to trust Alice
  enough to provide that bounded work in return for Alice credits. Alice can
  accept Bob's contribution without first providing a service to Bob. After
  checking the result, Alice may assign Bob nonzero trust. Bob can then spend
  the earned Alice credits on Alice's services.

If neither peer chooses to trust or contribute, there is no automatic bootstrap.
New keys do not bypass this decision. Communities grow through explicit
relationships, useful work, and finite resource budgets.

Higher trust may justify lower advertised prices or greater limits. Trust never
makes a new service free. A possible local pricing policy is
`ceil(minimum + surcharge * (1 - trust))`, with a positive minimum, but it must
be resolved into explicit advertised/quoted terms before acceptance. Published
trust records are opinions and must not replace the reader's local judgment.
