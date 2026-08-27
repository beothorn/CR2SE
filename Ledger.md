# CR2SE Ledger

The CR2SE ledger records the economic relationship between a local identity and other CR2SE identities.

Common domain terms such as **credit**, **credit issuer**, **credit owner**, **credit claim**, **local ledger**, and **trust score** are defined in the [CR2SE Glossary](./Glossary.md).

It records three kinds of information:

* credits the local identity owns;
* credits issued by the local identity and believed to be owned by another identity;
* the local identity's trust score for another identity.

The ledger is local state.

CR2SE does not define a global ledger, distributed consensus mechanism, authoritative balance database, or synchronization protocol.

Two identities interacting with each other will normally maintain corresponding records, but each identity trusts its own local ledger.

Their records may disagree.

This is intentional.

CR2SE deals with unreliable or dishonest peers through **trust**, rather than by attempting to make every participant agree on a globally authoritative state.

---

## 1. Identity

Ledger entries are associated with CR2SE identities.

A CR2SE identity is the cryptographic identity defined by the CR2SE Identity specification.

The ledger does not associate credits or trust with:

* network addresses;
* TCP connections;
* individual processes;
* individual machines.

If several nodes operate using the same CR2SE identity, they represent the same identity from the ledger's perspective.

How those nodes share or synchronize their local ledger storage is implementation-dependent.

---

## 2. Local Ledger

Every CR2SE identity maintains its own view of its economic relationships.

Conceptually, a ledger may be represented as:

```text
Other Identity | Owned Credits | Issued Credits | Trust
```

This is only a conceptual representation.

CR2SE does not require a relational database, files, serialized JSON, an embedded database, in-memory structures, or any other particular persistence mechanism.

An implementation may store ledger information however it chooses as long as it can implement the behavior defined by this specification.

---

## 3. Credits

A **credit** is an integer unit issued by one CR2SE identity.

Credits are always associated with their issuer.

There is no global CR2SE credit.

For example:

```text
Alice credit
Bob credit
BigStorage credit
SuperFederatedChatHub credit
```

are different credits.

Therefore:

```text
10 Alice credits
```

and:

```text
10 Bob credits
```

do not represent the same asset and are not required to have the same practical value.

A credit has value because its issuer may accept it in exchange for services.

---

## 4. Credit Issuer

The **credit issuer** is the identity that creates a credit.

For example:

```text
Alice gives Bob 10 Alice credits
```

Alice is the issuer.

Bob is the owner.

Conceptually:

```text
Issuer              Owner

Alice  -----------> Bob
        10 Alice
         credits
```

Only Alice controls the meaning and acceptance of Alice credits.

CR2SE does not impose a global supply of credits.

An identity may issue as many of its own credits as it chooses.

---

## 5. Credit Owner

The **credit owner** is the identity currently recognized as possessing credits issued by another identity.

For example:

```text
Bob owns 10 Alice credits
```

means that Bob's ledger records 10 credits issued by Alice.

It also normally means that Alice's ledger records that Bob owns 10 Alice credits.

These are two independent records.

They are expected to correspond during normal operation, but CR2SE does not guarantee that they correspond.

---

## 6. Credit Amount

Credit amounts are non-negative unsigned 64-bit integers.

The valid range is:

```text
0 .. 18446744073709551615
```

or:

```text
0 .. 2^64 - 1
```

Fractional credits do not exist.

For example:

```text
1 credit
10 credits
500 credits
```

are valid amounts.

The following is not a valid CR2SE credit amount:

```text
0.5 credits
```

Arithmetic that would overflow the unsigned 64-bit range must be rejected.

A balance must never become negative.

---

## 7. No Negative Balances

CR2SE does not represent debt using negative credit balances.

Suppose Bob owns no Alice credits.

The following is invalid:

```text
Bob owns -5 Alice credits
```

If Alice provides a service to Bob and expects value from Bob in return, that relationship must be represented using Bob credits or another arrangement accepted by Alice.

This keeps credit ownership directional and explicit.

---

## 8. Two Credit Entry Types

A CR2SE ledger distinguishes between two types of credit entries:

1. **owned credits**;
2. **issued credits**.

They describe different sides of credit relationships and must remain distinguishable.

---

## 9. Owned Credits

An **owned credit entry** records credits issued by another identity that the local identity believes it owns.

Suppose the local identity is Bob.

Bob's ledger may contain:

```text
Owned Credits

Issuer: Alice
Amount: 10
```

This means:

```text
Bob believes Bob owns 10 Alice credits.
```

Conceptually:

```text
Bob's ledger

Alice -> 10 owned credits
```

Owned credits are relevant when Bob wants to purchase services from Alice or transfer Alice credits to another identity.

---

## 10. Issued Credits

An **issued credit entry** records credits issued by the local identity that the local identity believes another identity owns.

Suppose the local identity is Bob.

Bob's ledger may contain:

```text
Issued Credits

Owner: Alice
Amount: 4
```

This means:

```text
Bob believes Alice owns 4 Bob credits.
```

Conceptually:

```text
Bob's ledger

Alice -> 4 issued credits
```

Issued credits are particularly important to service providers because they describe obligations that the provider may choose to honor when peers request services.

---

## 11. Why Owned and Issued Credits Are Separate

Owned credits and issued credits represent different economic relationships.

Consider Alice and a large storage provider named BigStorage.

Alice may provide some useful service to BigStorage and request payment in BigStorage credits.

The resulting relationship may be:

```text
Alice's ledger:

Owned credits:
    BigStorage -> 100


BigStorage's ledger:

Issued credits:
    Alice -> 100
```

BigStorage may have little interest in accumulating Alice credits.

Alice, however, may value BigStorage credits because she expects to use BigStorage's services later.

CR2SE therefore does not assume that service exchange is symmetric or that two identities should maintain equal balances in opposite credit types.

---

## 12. Corresponding Ledger Entries

When Alice issues credits to Bob, two corresponding records normally exist.

For example:

```text
Alice gives Bob 10 Alice credits.
```

Alice records:

```text
Issued Credits

Owner: Bob
Amount: 10
```

Bob records:

```text
Owned Credits

Issuer: Alice
Amount: 10
```

Conceptually:

```text
Alice's view                 Bob's view

Bob owns                     I own
10 Alice credits             10 Alice credits
```

These records are maintained independently.

CR2SE does not define one record as a synchronized replica of the other.

---

## 13. Ledger Disagreement

Peers may disagree about credit balances.

For example:

```text
Bob's ledger:

I own 10 Alice credits.


Alice's ledger:

Bob owns 7 Alice credits.
```

CR2SE does not define a consensus mechanism to determine that one of these records is globally correct.

Bob trusts Bob's ledger.

Alice trusts Alice's ledger.

If Bob requests a service from Alice, Alice ultimately decides what Alice is willing to provide.

Bob cannot force Alice to accept Bob's view of the balance.

Likewise, Alice cannot force Bob to consider Alice trustworthy after refusing credits that Bob believes Alice previously issued.

The disagreement becomes part of the relationship between the identities.

Trust exists to allow peers to react to such behavior.

---

## 14. Issuer Control

An identity has complete control over the credits it issues.

An issuer may:

* create credits;
* decide who receives credits;
* decide which services accept its credits;
* decide how much a service costs;
* refuse credits;
* reduce a balance it previously recognized;
* revoke credits;
* invalidate unclaimed credit claims;
* reject a transfer;
* charge for a credit transfer;
* refuse to provide a service.

For example, Alice may previously record:

```text
Bob owns 100 Alice credits.
```

and later decide to record:

```text
Bob owns 0 Alice credits.
```

CR2SE does not technically prevent this.

Bob may respond by lowering Alice's trust score.

Other identities may independently do the same based on their own experiences or information.

The protocol therefore does not attempt to make promises technically irreversible.

---

## 15. Credits Are Not Globally Enforced Assets

CR2SE credits must not be interpreted as globally enforced currency.

Possessing a credit does not cryptographically force its issuer to provide a service.

There is no authority that forces an issuer to honor a balance.

There is no global database that can overrule the issuer.

There is no consensus algorithm that determines the universally correct balance.

Instead:

```text
peer behavior
      |
      v
local observations
      |
      v
trust
      |
      v
price and willingness to interact
```

An identity that repeatedly refuses to honor its credits may become less trusted.

Lower trust may make interacting with other peers more expensive or impossible.

The economic mechanism is therefore based on relationships and consequences rather than global enforcement.

---

## 16. Spending Credits

When credits are spent with their issuer, the corresponding balance decreases.

Suppose Bob owns:

```text
10 Alice credits
```

and purchases a service from Alice costing:

```text
3 Alice credits
```

After the service exchange, the expected records are:

```text
Bob's ledger:

Alice owned credits:
10 -> 7
```

and:

```text
Alice's ledger:

Bob issued credits:
10 -> 7
```

The spent credits do not need to be transferred back to Alice.

They are simply removed from the recognized outstanding balance.

A spending operation must not reduce a balance below zero.

---

## 17. Credit Transfer

Credits may be transferred between identities.

A transfer involves three roles:

```text
issuer
current owner
new owner
```

For example:

```text
Issuer:        Alice
Current owner: Bob
New owner:     Carol
Amount:        4
```

Suppose Bob owns 10 Alice credits and wants Carol to own 4 of them.

Conceptually:

```text
Before:

Alice credits

Bob   -> 10
Carol -> 0


Transfer 4 from Bob to Carol


After:

Bob   -> 6
Carol -> 4
```

Because Alice issued the credits, Alice participates in the transfer.

---

## 18. Transfer Order

The current owner initiates a transfer by creating a **transfer order**.

The transfer order identifies:

* the credit issuer;
* the current owner;
* the new owner;
* the amount being transferred.

The current owner signs the transfer order using the identity signing mechanism defined by CR2SE.

Conceptually:

```text
Transfer Order

Issuer:     Alice
From:       Bob
To:         Carol
Amount:     4

Signed by Bob
```

The signature allows Alice to verify that the identity currently claiming ownership of the credits requested the transfer.

The exact cryptographic signing operations use the signing mechanism defined by the CR2SE Encryption specification.

---

## 19. Transfer Processing

The current owner sends the signed transfer order to the issuer.

For example:

```text
Bob                              Alice

signed transfer order
Bob -> Carol
4 Alice credits
----------------------------------->
```

Alice verifies the transfer order and decides whether to accept it.

Alice is not required by CR2SE to accept the transfer.

If Alice accepts it, Alice updates the issued-credit entries in Alice's ledger.

Conceptually:

```text
Bob:

10 -> 6

Carol:

0 -> 4
```

Bob updates Bob's owned-credit entry accordingly.

Carol does not need to participate in the transfer at the time the transfer occurs.

Carol may later contact Alice and request the balance that Alice recognizes for Carol.

How Carol learns that the transfer occurred is outside the ledger requirements.

---

## 20. Transfer Fees

The issuer may charge for processing a transfer.

CR2SE does not define a mandatory transfer price.

For example, Alice could decide that transferring Alice credits costs:

```text
1 Alice credit
```

An implementation may also make transfers free of additional charges.

Transfer pricing is an issuer policy.

The applicable cost must be known before a transfer that charges credits is committed.

Implementations should expose transfer costs to the requesting peer before requesting final authorization where the surrounding protocol allows it.

---

## 21. Transfer Validity

A transfer order does not force an issuer to update its ledger.

The issuer may reject a transfer for any reason.

Possible implementation-specific reasons include:

* insufficient recognized balance;
* invalid signature;
* invalid amount;
* local policy;
* transfer fees;
* low trust;
* revoked credits;
* rate limits;
* suspected abuse.

Only the issuer decides which issued-credit balances it recognizes.

A rejected transfer may affect how the current owner evaluates the issuer's trustworthiness.

---

## 22. Transfer Order Representation

Independent CR2SE implementations must be able to produce and verify the same transfer order.

A version 1 transfer order contains:

```text
Version
Issuer ID
Current Owner ID
New Owner ID
Amount
```

The version is:

```text
0x01
```

The amount is an unsigned 64-bit integer encoded in network byte order, most significant byte first.

CR2SE version 1 IDs are 32 bytes.

The canonical bytes to be signed are:

```text
Transfer Version || Issuer ID || Current Owner ID || New Owner ID || Amount
```

with:

```text
Offset | Size     | Field
0      | 1 byte   | Transfer Version
1      | 32 bytes | Issuer ID
33     | 32 bytes | Current Owner ID
65     | 32 bytes | New Owner ID
97     | 8 bytes  | Amount
```

The complete unsigned transfer order is therefore exactly:

```text
105 bytes
```

The current owner signs these 105 bytes.

The signature is transported together with the transfer order.

The current owner ID must correspond to the identity whose key verifies the signature.

An amount of zero must be rejected.

---

## 23. Transfer Replay

A valid transfer order must not be processed repeatedly.

Otherwise the same signed order could be replayed and cause repeated transfers.

Implementations must therefore associate each transfer with a unique transfer identifier.

For version 1, a transfer order additionally contains a 16-byte cryptographically random transfer identifier.

The canonical transfer representation is therefore:

```text
Transfer Version || Transfer ID || Issuer ID || Current Owner ID || New Owner ID || Amount
```

with:

```text
Offset | Size     | Field
0      | 1 byte   | Transfer Version
1      | 16 bytes | Transfer ID
17     | 32 bytes | Issuer ID
49     | 32 bytes | Current Owner ID
81     | 32 bytes | New Owner ID
113    | 8 bytes  | Amount
```

The canonical unsigned transfer order is exactly:

```text
121 bytes
```

These 121 bytes are signed by the current owner.

An issuer that has already accepted a transfer with the same transfer ID must not apply it again.

How processed transfer IDs are stored and how long rejected transfer IDs are retained is implementation-dependent.

An implementation should retain accepted transfer identifiers for as long as replay of the corresponding transfer could incorrectly modify its ledger.

---

## 24. Credit Claims

A **credit claim** allows an issuer to create credits without initially assigning them to an identity.

Instead, the issuer associates the credits with a secret.

Conceptually:

```text
Alice creates:

Amount: 100 Alice credits
Credit Claim: secret value

Owner: unassigned
```

Alice may give the credit claim to another party.

Whoever possesses the claim may present it to Alice and ask that the associated credits be assigned to a CR2SE identity.

This mechanism is similar to a bearer credential:

```text
possess claim
      |
      v
present claim to issuer
      |
      v
request credits for Identity X
```

The claim is not a CR2SE identity private key.

It is a separate secret used only for claiming credits.

---

## 25. Credit Claim Security

A credit claim must be difficult for another participant to guess.

CR2SE version 1 credit claims must contain at least:

```text
128 bits
```

of cryptographically secure random data.

Implementations may use larger claims.

A recommended size is:

```text
256 bits
32 bytes
```

Claims must be generated using a cryptographically secure random number generator.

Sequential values, timestamps, predictable pseudo-random values, usernames, passwords chosen by users, or similar predictable values must not be used as credit claims.

Possession of the claim is sufficient to request its credits.

A claim must therefore be treated as secret until redeemed or invalidated.

---

## 26. Credit Claim Representation

For interoperability, the transferable form of a version 1 credit claim is:

```text
cr2se-claim:<base32-secret>
```

The secret is encoded using the RFC 4648 Base32 alphabet:

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZ234567
```

without padding.

Implementations must accept ASCII letters case-insensitively.

Implementations should produce uppercase Base32.

The `cr2se-claim:` prefix is not part of the random secret.

A claim may be transported using text, QR codes, messages, files, or any other mechanism.

The transport mechanism is outside the ledger specification.

---

## 27. Creating a Credit Claim

When an issuer creates a credit claim, it records at least:

```text
Claim
Amount
State
```

Conceptually:

```text
Claim:  cr2se-claim:...
Amount: 100
State:  unclaimed
```

The credits do not yet have an identity owner.

The issuer remains completely in control of whether the claim will later be honored.

The internal storage representation is implementation-dependent.

---

## 28. Redeeming a Credit Claim

A peer redeems a claim by presenting:

```text
credit claim
identity receiving the credits
```

to the issuer.

For example:

```text
Bob                              Alice

claim K
assign to Bob
----------------------------------->
```

If Alice accepts the claim:

```text
Claim K:

unclaimed -> claimed
```

and Alice records:

```text
Issued Credits

Owner: Bob
Amount: +100
```

Bob may correspondingly record:

```text
Owned Credits

Issuer: Alice
Amount: +100
```

One claim assigns its entire amount.

Partial claim redemption is not supported.

A successfully redeemed claim must not be redeemable again.

---

## 29. Claim Authority

A credit claim does not independently prove that credits have globally recognized value.

The issuer decides whether to honor it.

For example, Bob may receive an Alice credit claim representing 100 credits.

Bob cannot force Alice to accept the claim merely because Bob possesses the correct secret.

Alice may have invalidated it.

Alice may refuse it.

Alice may no longer recognize it.

Alice may change her policy.

The decision to accept a credit claim from another identity is therefore itself a matter of trust.

CR2SE defines how claims are represented and what they mean when honored.

It does not guarantee that an issuer will honor them.

---

## 30. Claim Invalidation

An issuer may invalidate an unclaimed credit claim at any time.

An invalidated claim must not subsequently create a balance unless the issuer explicitly decides otherwise.

Implementations may additionally support implementation-specific policies such as:

* expiration times;
* manual cancellation;
* automatic invalidation;
* claim usage restrictions.

Such policies are not required by CR2SE.

A peer receiving a claim must not assume that possession guarantees future redemption.

---

## 31. Trust

A **trust score** is the local identity's evaluation of another CR2SE identity.

Trust is represented as a value from:

```text
0
```

through:

```text
1
```

inclusive.

Conceptually:

```text
0.0 = no trust
1.0 = maximum trust
```

Trust belongs to the evaluating identity.

There is no global CR2SE trust score.

---

## 32. Trust Is Asymmetric

Trust is directional.

For example:

```text
Bob's trust in Alice = 0.8
Alice's trust in Bob = 0.3
```

is valid.

There is no requirement that:

```text
trust(Alice, Bob) = trust(Bob, Alice)
```

Each identity makes its own evaluation.

---

## 33. Initial Trust

An unknown identity starts with trust:

```text
0
```

This is a deliberate CR2SE design choice.

A new identity is not automatically granted access to services merely because it can establish a valid cryptographic identity.

A trust score of zero means that the local peer must not provide a CR2SE service to that identity.

Conceptually:

```text
new identity
      |
      v
trust = 0
      |
      v
no service provided by this peer
```

A new relationship therefore normally begins in the opposite direction.

If Alice has zero trust in Bob, Alice does not begin by providing resources to Bob.

Bob may first provide a service or resource to Alice.

Alice may then choose to increase Bob's trust.

This creates relationships through demonstrated contribution rather than merely through identity creation.

---

## 34. Trust and New Identities

CR2SE identity creation is intentionally inexpensive.

An identity can generate a new cryptographic identity without asking permission from anyone.

Therefore, identity creation itself cannot establish economic trust.

A participant cannot escape a poor trust relationship and automatically regain access simply by generating a new identity.

The new identity starts at:

```text
trust = 0
```

from the perspective of peers that have not chosen to trust it.

This property is intended to encourage networks that grow from existing relationships, successful interactions, resource contribution, and local trust decisions.

---

## 35. Trust Calculation

CR2SE does not define how an implementation calculates trust.

An implementation may consider any information available to it.

Possible factors include:

* successful service fulfillment;
* failed service fulfillment;
* whether credits were honored;
* rejected transfers;
* invalidated credit claims;
* previous interactions;
* information reported by trusted peers;
* network information;
* abuse detection;
* local configuration;
* operator decisions;
* application-specific information.

These are examples, not protocol requirements.

An implementation may use a simple algorithm, a complex reputation model, manual configuration, or another mechanism.

The final trust value exposed to the CR2SE ledger remains a value between zero and one.

---

## 36. Trust Information From Other Peers

Peers may communicate their trust values for other identities.

For example:

```text
Bob asks Alice about Carol.

Alice reports:

trust(Carol) = 0.7
```

Bob is not required to adopt Alice's value.

Bob may:

* ignore it;
* use it as one input;
* weight it according to Bob's trust in Alice;
* combine it with other information;
* assign Carol a completely different value.

This document defines only that trust information may exist and may be shared.

The mechanism used to request or distribute third-party trust information is defined outside the ledger specification.

---

## 37. Trust Is Not Reputation Consensus

Trust information from several peers does not create a global reputation score.

For example:

```text
Alice trusts Carol = 0.9
Bob trusts Carol   = 0.2
Dave trusts Carol  = 0.7
```

CR2SE does not calculate an authoritative average.

Each peer independently decides:

```text
my trust in Carol
```

The result may be influenced by other identities but always remains a local decision.

---

## 38. Trust and Service Price

Trust is an input that a service provider may use when calculating the price of a service.

The exact pricing algorithm is implementation-dependent.

CR2SE strongly recommends the following relationship:

```text
lower trust -> higher price
higher trust -> lower price
```

A trust score of zero is special.

For service provision:

```text
trust = 0 -> infinite effective price
```

In practical terms:

```text
trust = 0 -> refuse service
```

The peer must first establish nonzero trust through some other interaction before receiving the service.

---

## 39. Suggested Trust Pricing Function

CR2SE does not require a specific pricing function.

A simple recommended model is:

```text
price = minimum_price + trust_surcharge × (1 - trust)
```

where:

```text
minimum_price > 0
trust_surcharge >= 0
0 < trust <= 1
```

and:

```text
trust = 0 -> service unavailable
```

For example:

```text
minimum_price  = 10
trust_surcharge = 20
```

produces approximately:

```text
Trust | Price
------+------
0.00  | unavailable
0.25  | 25
0.50  | 20
0.75  | 15
1.00  | 10
```

Because CR2SE credits are integer units, the provider must define how non-integer calculated prices are rounded.

Rounding upward is recommended so that pricing never accidentally falls below the intended price.

This formula is only a recommendation.

A provider may use another pricing function.

---

## 40. Services Must Not Become Free Through Trust

Maximum trust does not imply free service.

Trust affects the conditions under which peers exchange resources.

It does not eliminate the exchange.

Every CR2SE service offering must maintain:

```text
price >= 1 credit
```

This is a protocol requirement, not merely a pricing recommendation.

A trust score of one represents the lowest trust-related risk adjustment, not an obligation to provide resources for free.

---

## 41. Other Pricing Factors

Trust does not need to be the only factor affecting price.

A provider may consider factors such as:

* available storage;
* available computation;
* bandwidth;
* current demand;
* service capacity;
* resource scarcity;
* operating cost;
* requested duration;
* requested amount;
* current credit balance;
* local policy.

For example:

```text
storage becoming scarce
        |
        v
storage price increases
```

even if the requesting peer's trust remains unchanged.

The complete service-pricing policy belongs to the service provider.

---

## 42. Trust and Refusal

A provider always retains the ability to refuse a service.

A nonzero trust score does not guarantee that a service will be provided.

For example:

```text
trust = 0.8
```

means only that the provider currently assigns that trust value to the identity.

The provider may still refuse because:

* the resource is unavailable;
* the offered service is disabled;
* the price cannot be paid;
* capacity has been reached;
* another local policy rejects the request.

Trust is an input to service decisions, not a promise of service.

---

## 43. No Ledger Synchronization Protocol

CR2SE does not require ledgers to synchronize.

There is no operation whose purpose is to force:

```text
Alice's ledger == Bob's ledger
```

Peers may exchange information necessary for individual operations, but their local ledger state remains their own responsibility.

Implementations may provide optional reconciliation, auditing, history exchange, backups, or synchronization mechanisms.

Such mechanisms must not be required for basic CR2SE ledger interoperability.

---

## 44. No Required Transaction History

CR2SE requires current ledger state but does not require a complete historical transaction log.

An implementation may store:

```text
current balance only
```

or:

```text
current balance
+
complete transaction history
```

or another internal representation.

Transaction history may be useful for:

* debugging;
* trust calculation;
* auditing;
* user interfaces;
* dispute investigation;
* backups.

It is not required to establish a globally authoritative balance.

---

## 45. No Proof Overrides Local Policy

A cryptographic signature can prove that an identity signed a particular message.

It cannot force another identity to provide a service.

For example, Bob may possess a correctly signed message showing that Alice previously participated in some credit operation.

Alice may nevertheless refuse Bob's request.

CR2SE does not contain a mechanism by which Bob can cryptographically compel Alice to honor the previous state.

Bob's available response within the economic model is to change how much Bob trusts Alice and potentially communicate that information to others.

This distinction is fundamental:

```text
cryptography proves actions

trust evaluates behavior

neither forces future cooperation
```

---

## 46. Ledger Persistence

Ledger information should normally survive node restarts.

Otherwise an identity could unintentionally lose the economic relationships associated with that identity.

An implementation should persist at least:

* owned-credit balances;
* issued-credit balances;
* trust scores;
* unclaimed credit claims it issued;
* information necessary to prevent accepted transfer replay.

The storage mechanism is implementation-dependent.

Possible implementations include:

* relational databases;
* embedded databases;
* structured files;
* binary files;
* serialized objects;
* other durable storage systems.

These choices do not affect CR2SE interoperability.

---

## 47. Multiple Nodes Using One Identity

CR2SE permits the same identity to operate on several nodes.

Because credits and trust belong to the identity, those nodes conceptually represent the same economic participant.

However, CR2SE does not define how several nodes using the same identity synchronize their ledgers.

For example:

```text
                    Identity Alice
                         |
              +----------+----------+
              |                     |
           Node A                 Node B
              |                     |
           Ledger A              Ledger B
```

If Ledger A and Ledger B diverge, resolving that divergence is Alice's implementation problem.

Other peers are not required to distinguish between Alice's nodes.

Any externally visible inconsistency may affect how those peers evaluate Alice's trustworthiness.

---

## 48. Concurrency

An implementation must prevent concurrent local operations from accidentally violating ledger invariants.

For example, suppose Bob owns:

```text
10 Alice credits
```

and two concurrent requests attempt to spend:

```text
8 Alice credits
```

each.

The implementation must not allow both operations to independently observe the original balance and produce an invalid result.

After committed operations:

```text
balance >= 0
```

must always remain true.

How implementations provide atomicity, locking, transactions, serialization, or other concurrency control is implementation-dependent.

---

## 49. Required Ledger Invariants

A conforming CR2SE ledger implementation must preserve the following local invariants:

```text
credit amounts are unsigned 64-bit integers

credit balances are never negative

fractional credits do not exist

owned credits identify an external issuer

issued credits identify an external owner

trust is associated with an identity

0 <= trust <= 1

unknown identities begin with trust 0

trust 0 prevents paid service provision

a credit belongs to exactly one issuer

credit value is issuer-specific

a successful claim consumes the entire claim

a successfully consumed claim cannot be consumed again

an accepted transfer must not be applied more than once

only the current owner signs a transfer order requesting transfer
```

These are protocol requirements.

Storage layout, pricing algorithms, trust algorithms, history retention, and most policy decisions are implementation-dependent.

---

## 50. Minimum Conceptual Ledger Interface

The exact programming API is implementation-specific, but a ledger implementation must be capable of performing operations equivalent to:

```text
get_owned_credits(issuer)

get_issued_credits(owner)

set_owned_credits(issuer, amount)

set_issued_credits(owner, amount)

increase_owned_credits(issuer, amount)

decrease_owned_credits(issuer, amount)

increase_issued_credits(owner, amount)

decrease_issued_credits(owner, amount)

get_trust(identity)

set_trust(identity, value)

create_credit_claim(amount)

redeem_credit_claim(claim, identity)

invalidate_credit_claim(claim)

create_transfer_order(issuer, new_owner, amount)

verify_transfer_order(order, signature)

accept_transfer_order(order)

reject_transfer_order(order)
```

These names are illustrative.

CR2SE does not require implementations to expose functions with these exact names or signatures.

They describe the behavior the ledger layer must be capable of supporting.

---

## 51. Implementation-Dependent Decisions

The following decisions are intentionally left to implementations:

* physical ledger storage;
* database schema;
* file formats used internally;
* transaction history retention;
* trust calculation algorithm;
* how quickly trust changes;
* use of third-party trust information;
* abuse detection;
* service pricing formula;
* price rounding policy;
* transfer fees;
* credit issuance policy;
* credit revocation policy;
* claim expiration policy;
* claim invalidation policy;
* service refusal policy;
* optional ledger reconciliation;
* synchronization between nodes using the same identity;
* backups and recovery;
* concurrency-control mechanism.

Implementations should choose these policies according to the environment in which they operate.

They must not assume that other CR2SE implementations make the same choices.

---

## 52. Example: Two Small Peers

Alice and Bob are new to each other.

Initially:

```text
Alice's ledger:

Bob:
    issued credits: 0
    owned credits:  0
    trust:          0


Bob's ledger:

Alice:
    issued credits: 0
    owned credits:  0
    trust:          0
```

Because trust is zero, neither should begin by providing a CR2SE service to the other merely because the other requested one.

Suppose Bob first provides Alice with a useful resource.

Alice decides to compensate Bob with 10 Alice credits and increase Bob's trust.

Alice records:

```text
Bob:

issued credits: 10
trust:          0.2
```

Bob records:

```text
Alice:

owned credits: 10
```

Later Bob requests a service from Alice costing 3 Alice credits.

Alice now has nonzero trust in Bob and decides to accept.

After successful service provision:

```text
Alice's ledger:

Bob:
    issued credits: 7
```

and:

```text
Bob's ledger:

Alice:
    owned credits: 7
```

Alice and Bob may continue exchanging services.

Their relationship grows from actual interaction rather than from automatic trust granted to newly created identities.

---

## 53. Example: Large Service Provider

Consider a large service provider:

```text
BigStorage
```

and a smaller participant:

```text
Alice
```

Alice wants BigStorage's storage service.

BigStorage credits are useful to Alice because they can be spent on BigStorage's services.

Alice may therefore provide some resource useful to BigStorage and prefer payment in:

```text
BigStorage credits
```

rather than requiring BigStorage to accumulate Alice credits.

The resulting ledgers may contain:

```text
Alice:

Owned BigStorage credits: 500
```

and:

```text
BigStorage:

Issued credits to Alice: 500
```

This asymmetry is normal.

CR2SE does not require every pair of peers to exchange equal amounts of each other's credits.

---

## 54. Example: Dishonest Issuer

Suppose Alice legitimately believes:

```text
Bob owns 100 Alice credits.
```

Bob also records:

```text
I own 100 Alice credits.
```

Later Bob requests a service costing 20 Alice credits.

Alice refuses to recognize Bob's balance and claims:

```text
Bob owns 0 Alice credits.
```

CR2SE does not attempt to force Alice to restore the balance.

Bob may instead decide:

```text
trust(Alice) -> 0
```

Bob may stop providing services to Alice.

Bob may also report Bob's trust value for Alice when other peers ask for it.

Other peers independently decide whether that information affects their own trust in Alice.

The protocol therefore allows Alice to behave dishonestly.

It also allows the surrounding network economy to stop cooperating with Alice.

---

## 55. Design Principle

The CR2SE ledger is deliberately not a global accounting system.

It does not attempt to answer:

```text
What is the universally correct balance?
```

Instead, every identity answers:

```text
What balance do I recognize?

What credits do I believe I own?

What obligations do I recognize?

How much do I trust this identity?

Under what conditions am I willing to exchange resources with it?
```

This keeps economic authority local.

A peer cannot force another peer to provide resources.

A peer cannot force another peer to recognize credits.

A peer cannot force another peer to assign it trust.

The consequence of unreliable behavior is that other peers may independently become less willing to interact with that identity.

CR2SE therefore bases resource exchange on local credit relationships and local trust rather than on central authority or global consensus.
