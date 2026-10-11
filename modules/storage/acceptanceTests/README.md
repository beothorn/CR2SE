# Storage acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases; required
suite. Fixture terms: minimumPrice1, byteUsageFactor1/2,
byteStorageDurationFactor1/2, retrievalByteUsageFactor1/2,
renewalByteStorageDurationFactor1/2, removePrice2, checkPrice3,
checkResponseSeconds5; maximumBytes/maxRetrieveBytes100, retention1..100 and
maximumTotalRetentionSeconds200. Other required fields/preconditions are valid.
Use actual field name `maximumRetrieveBytes` in the offering. Default object is
ASCII("abc"), hash `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`.

```text
TEST ST-01 exact price arithmetic
  ACT quote store(size1,retention1); ASSERT price=1, not2
  ACT quote store(size3,retention10); ASSERT price=17
  ACT quote retrieve(length3); ASSERT price=2
  ACT quote renew(size3,additional4); ASSERT price=6
  ACT quote remove/check; ASSERT prices=2 and3
  FOR EACH [zero denominator, negative factor, minimum0, overflowing advertised maximum]:
    ACT validate offering; ASSERT unusable/rejected before acceptance

TEST ST-02 durable store and exact output
  ACT store size3, retention10, hash and data above at time1000
  ASSERT no body accepted for execution before quote17 is accepted/reserved
  ASSERT output.operation="store"; leaseId length32 and unique
  ASSERT sizeBytes=3; contentHash=fixtureHash; acceptedAt=1000; expiresAt=1010; price=17
  ACT restart provider; retrieve using same authenticated owner and known lease ID
  ASSERT exact original bytes and retained terms available; one store charge17

TEST ST-03 invalid upload and publication barrier
  FOR EACH [size0, size101, retention0/101, malformed hash, hash mismatch,
            missing/extra data byte, incomplete input, durable byte write failure]:
    ACT store mutated fixture
    ASSERT no active successful lease; chargeDelta=0
    ASSERT receiving data is not reported as an accepted durable obligation
  ACT acceptedAt=U64_MAX with positive retention
  ASSERT overflow rejected, not wrapped expiration

TEST ST-04 owner-only access and opaque IDs
  create A's lease; U knows leaseId/hash
  FOR EACH operation IN [retrieve,renew,remove,check]:
    ACT as U for existing lease and unknown lease
    ASSERT no protected metadata disclosed; denial does not reveal existence
    ASSERT no charge or lease change
  ACT A reconnects from another node with coordinated same identity
  ASSERT authorized access succeeds; lease ID is not a bearer secret

TEST ST-05 ranges and whole-object hash
  ACT retrieve(offset1,length2) from abc
  ASSERT data=ASCII("bc"); offset=1; contentHash=hash of abc, not bc; price=1
  ACT retrieve(offset0,length3); ASSERT data=abc; price=2
  FOR EACH [length0, offset3, offsetU64_MAX, length>size-offset, length>current limit]:
    ACT retrieve; ASSERT REJECT without charge or overflow

TEST ST-06 expiration during transfer
  create lease expires1010; set time1009; ACT accept valid retrieve and price
  set time1011 while returning body
  ASSERT accepted transfer completes with original bytes/price
  ACT new retrieve at exactly1010 on fresh fixture
  ASSERT inactive/unavailable and uncharged

TEST ST-07 renewal guard and total bounds
  create3-byte lease expires1010 at acceptedAt1000
  ACT renew(expected1010,additional4)
  ASSERT previousExpiresAt=1010; expiresAt=1014; price=6
  ACT repeat expected1010; ASSERT conflict/failure; no second charge/extension
  race two renewals expected1010 on fresh fixture
  ASSERT at most one succeeds; expiration reflects one extension
  FOR EACH [expired lease, excessive duration, proposed expiry beyond acceptedAt+200,
            overflow addition]:
    ACT renew; ASSERT prior valid lease state unchanged; no charge

TEST ST-08 removal
  ACT remove active lease; ASSERT removed=true; price=2
  ASSERT later retrieve/renew/check treat lease inactive; no refund
  ACT remove again or remove expired/unknown lease
  ASSERT failure without charge; no promise of physical erasure

TEST ST-09 current terms versus obligations
  create lease using offering old; publish compatible new offering with retrieval rate1
  ACT retrieve3 through new offering; ASSERT quote3 explicitly accepted before output
  ASSERT original size/hash/expiration unchanged
  ACT remove all compatible offerings before new request
  ASSERT new paid request unavailable; retained lease obligation not erased
  ACT remove offering after an accepted retrieve
  ASSERT that transfer completes under its accepted terms

TEST ST-10 paid byte check outcomes
  create active abc lease; A retains expected byte b at offset1
  ACT check offset1, price3, complete timely evidence within5 seconds
  ASSERT evidence={leaseId,offset:1,value:ASCII("b")}; expected byte never sent
  ASSERT local outcome=pass; chargeDelta=3
  ACT fresh check with timely complete wrong byte; ASSERT outcome=fail; chargeDelta=3
  ACT provider validly reports authorized active byte unavailable
  ASSERT outcome=fail; no successful evidence charge
  ACT no complete valid evidence/timeout; ASSERT outcome=inconclusive; chargeDelta=0
  ACT original expected byte missing; ASSERT cannot claim pass

TEST ST-11 check bounds and timing policy
  FOR EACH [offset=size, unauthorized owner, inactive lease]:
    ACT check; ASSERT failure without charge
  configure allowed one-second minimum interval and overlap refusal
  ACT disallowed overlapping/too-soon challenge
  ASSERT refused without evidence charge; no undisclosed stricter frequency limit
  ASSERT check timer begins after complete challenge/input.end, not before negotiation

TEST ST-12 retries, races and restart
  RUN Services SV-09 with real Storage participant
  ACT lose remote successful store response
  ASSERT requester outcome_unknown; no automatic second lease creation
  ACT identical data as explicitly new accepted store
  ASSERT separate lease IDs/charges; content equality is not an idempotency key
  race renew/remove for one lease
  ASSERT one valid serialized history with corresponding exact local accounting
  ACT expire then move wall clock backward
  ASSERT an already terminal lease is not resurrected

TEST ST-13 encrypted replicas and module independence
  ACT store opaque encrypted bytes with local durable byte port
  ASSERT provider needs no decryption key and invokes no other service family
  ACT independently store same bytes at B and C
  ASSERT same hash/size but independently returned lease IDs/provider identities
  ASSERT one lease or two leases at B alone are not reported as independent redundancy
  RUN AT-E03 recovery using requester-owned catalog
```
