# Ledger acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Required
suite; use authenticated identity/crypto fixtures and durable transaction ports.
Snapshots below are privileged logical accounting observations, not table names.
Each test overrides default balances as stated and supplies sufficient trust.

```text
TEST LG-01 issuer-separated accounting
  fixture A owns 100 B credits and 40 C credits
  ACT query each balance
  ASSERT results =100 and40; no combined protocol currency balance
  ACT query B remotely as A; ASSERT B reports only its issued-to-A view
  ASSERT issuer query does not silently overwrite A's in-flight local accounting

TEST LG-02 provider-issued settlement
  fixture A.owned(B)=100; B.issued(A)=100
  ACT reserve price7 and complete valid work, issuer=B
  ASSERT balances remain100 while only reserved; available capacity=93
  ACT commit successful local settlement at both peers
  ASSERT A.owned(B)=93; B.issued(A)=93; chargeDelta=7
  ACT repeat local commit with same key/token
  ASSERT balances unchanged; effects applied once

TEST LG-03 requester-issued and same-identity work
  fixture A issuance capacity=10; B explicitly accepts A credits
  ACT successful work price7, requester=A, provider=B, issuer=A
  ASSERT A.issued(B)=7; B.owned(A)=7; remaining issuance capacity=3
  ASSERT no owned/issued self-balance is required or created
  ACT another price7 reservation; ASSERT insufficient capacity
  ACT same-identity work with finite internal budget10 and price7
  ASSERT internal use=7; no external earned credits or self-balances

TEST LG-04 concurrent reservations and metered release
  fixture available=100
  race reserve(op1,60) with reserve(op2,60)
  ASSERT exactly one reservation succeeds; available=40
  ACT settle winner at21; ASSERT balance=79; available=79
  ACT explicit failure before success on fresh reserved operation
  ASSERT reservation released; chargeDelta=0

TEST LG-05 exact bounds and authorization
  FOR EACH [negative amount, zero service price, U64_MAX+1, overflow on issuance,
            underflow on spend, finalPrice>reservedMaximum, forged reservation token]:
    ACT affected operation; ASSERT REJECT; balances unchanged
  ACT spend exact U64_MAX from matching balance using valid bound
  ASSERT balance=0 without wrap/rounding
  ACT unprivileged grant/revoke/setTrust/createClaim
  ASSERT REJECT; peer input cannot act as administrator

TEST LG-06 trust and finite bootstrap
  fixture unknown A with balance100; B.trust(A)=0
  ACT paid provider service for A; ASSERT refused; no charge
  ACT bounded metadata or authorized claim redemption
  ASSERT zero trust alone does not forbid that bootstrap control
  ACT local grant5; ASSERT recognized balance increases by5 only
  ASSERT key creation and claim redemption do not automatically assign trust
  ACT local trust policy sets positive trust; ASSERT service can proceed if other terms valid

TEST LG-07 canonical transfer and fee
  fixture issuer C recognizes owner A=100, new owner B=0
  order = fixture(version1, transferId16, C.id,A.id,B.id, amount9)
  ACT encode/sign transfer
  ASSERT unsigned length=121; offsets 1,17,49,81,113 match exact fields
  ASSERT amount bytes=hex("0000000000000009"); signature covers only unsigned bytes
  ACT quote fee2 with maximumFee2; accept exact fee2; commit
  ASSERT C.issued(A)=91; C.issued(B)=7
  ASSERT result.amount=9; fee=2; receivedAmount=7

TEST LG-08 transfer refusal matrix
  FOR EACH [105-byte old layout, invalid version/length/signature, owner key mismatch,
            authenticated caller not owner, wrong issuer, amount0, fee>=amount,
            fee>maximumFee, accept fee different from quote, insufficient balance,
            newOwner=owner, newOwner=issuer, target balance overflow]:
    ACT transfer mutated fixture; ASSERT REJECT; all balances unchanged
  ACT receive transfer order without fee acceptance
  ASSERT no balance commitment yet

TEST LG-09 durable transfer replay and access
  ACT accept LG-07 transfer; lose result; restart issuer
  ACT same owner/order/transferId retry
  ASSERT identical original result without requote or second debit
  ACT same owner/transferId with different signed order
  ASSERT conflict; original result unchanged
  ACT query result as A, B and U
  ASSERT A/B receive original result; U receives no protected result
  ASSERT accepted replay guard remains after ordinary history compaction

TEST LG-10 third-party evidence and binding
  fixture successful service price7, fee2, unique transfer bound to this invocation
  ACT consume authenticated C transfer result with exact owner/newOwner/net/gross
  ASSERT mark settled once
  FOR EACH [forwarded A JSON, wrong C identity, wrong recipient, wrong ID/amount/fee,
            transfer already bound to another invocation, issuer refusal, lost response]:
    ACT settlement attempt
    ASSERT not falsely settled; no repeated service execution
  ACT policy disallows third-party credits
  ASSERT refuse before work or reservation, not after promising that mode

TEST LG-11 portable claim and encrypted redemption
  fixture issuance capacity20; ACT createClaim(amount7)
  ASSERT claimId and secret each32 bytes and independently generated
  ASSERT portable decoded bytes length=105, prefix byte1, amount7
  ASSERT stored commitment=oracleSHA256(secret); reserved issuance=7
  ACT redeem via generic encrypted envelope for C with embedded owner=A
  ASSERT authenticated A matches embedded owner
  ASSERT C.issued(A) increases7; reservation consumed; claim marked redeemed
  ASSERT clear bearer secret absent from wire/logs/Board

TEST LG-12 claim invalidation and replay
  FOR EACH [wrong secret, malformed/noncanonical Base64, zero amount, wrong issuer,
            embedded owner differs from connection, invalidated claim]:
    ACT redeem mutated fixture; ASSERT REJECT; no issuance
  ACT redeem valid claim; lose reply; restart; retry same secret and owner
  ASSERT original amount returned; issued exactly once
  ACT another owner redeems consumed claim; ASSERT REJECT
  ACT invalidate fresh unredeemed claim; ASSERT finite reservation released
  ASSERT claimed portable amount cannot override issuer's stored amount

TEST LG-13 coordination and conflicts
  ACT reserve and prepare effect under key K; repeat exact prepare
  ASSERT same durable status/token association and one reservation
  ACT prepare K with different terms/effect; ASSERT conflict
  ACT durable commit, lose ack, restart; status(K)
  ASSERT committed; repeat commit changes nothing
  ACT abort after commit; ASSERT cannot undo committed effect
  ACT dependency timeout while prepared but decision unknown
  ASSERT hold persists until coordinator resolves, not autonomously released
  RUN Services SV-09 fault matrix with this Ledger as real participant
```
