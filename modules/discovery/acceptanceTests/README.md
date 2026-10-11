# Discovery acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
runtime; share-record codec cases also apply to File Sharing catalogs without
an indexer. Fixtures use real signed address/share/trust records: time1000,
issuedAt990, expiresAt1100, skew5, lifetime200, index retention40. Prices:
indexBase2, indexRecord3, resolve/locate/find1, listIdentities/listTrust2.
Record/count/endpoint byte limits are explicitly configured to fit valid cases.
`r1<r2` denotes unsigned ordering of independently calculated record IDs.

```text
TEST DI-01 canonical address vector and ID
  ACT encode/decode the existing address-record test vector
  ASSERT signing bytes, signature and record ID equal pinned values
  ASSERT recordId=oracleSHA256(signingBytes), excluding64-byte signature
  FOR EACH record kind IN [address,share,trust]:
    ACT encode signed fixture
    ASSERT exact owning domain prefix, big-endian fields and fixed lengths
    ASSERT independent key-to-ID/signature verification succeeds

TEST DI-02 canonical endpoints
  ACT address record with sorted distinct IPv4,IPv6,DNS endpoints and ports1/65535
  ASSERT canonical binary address lengths4/16 and lowercase ASCII DNS bytes
  FOR EACH [duplicate/unsorted endpoints, IP wrong length, port0,
            uppercase/trailing-dot DNS, empty label, label64, name254,
            leading/trailing hyphen, unknown address kind, extra encoded bytes]:
    ACT validate record; ASSERT REJECT
  ASSERT endpoint ordering compares complete canonical endpoint bytes unsigned

TEST DI-03 signature, identity and field validation
  FOR EACH [wrong signer public key/ID, modified signed byte, bad signature,
            truncated fixed field, share boolean2, trust score1000000001,
            issuedAt>=expiresAt, unknown domain/record type]:
    ACT validate/index record; ASSERT REJECT with no placement/charge
  ACT trust score0 and1000000000
  ASSERT both valid; zero distinct from no published statement

TEST DI-04 currency of records
  FOR EACH (issued,expires,expected) IN [(1005,1100,valid),(1006,1100,invalid),
                                      (990,1000,invalid),(990,1191,invalid)]:
    ACT check current record at1000 with skew5/lifetime200
    ASSERT validity=expected
  ACT overflowing now+skew or retention addition
  ASSERT rejected safely, never wrap into valid time
  ASSERT expired retained history never returned as current

TEST DI-05 atomic index and exact charge
  ACT index valid two-record batch by A, including record signed by C
  ASSERT price=8; acceptedAt1000; placements order=input order
  ASSERT storedUntil1040 for record expiring1100; unique index IDs32
  ACT record expiring1020; ASSERT storedUntil1020
  ACT restart and retention check; ASSERT exact original bytes preserved
  FOR EACH [duplicate record ID, one bad signature, record count/bytes above limit,
            one durable write failure]:
    ACT batch; ASSERT none of its placements accepted and no charge

TEST DI-06 retained placements versus supersession
  ACT pay to index old record; then newer signed record supersedes it
  ASSERT lookup uses newer record
  ACT included check on old placement before storedUntil
  ASSERT exact old bytes still available; commitment not replaced by cache update
  ACT accept repeated paid indexing of same bytes under configured capacity
  ASSERT each accepted placement has its own commitment and allowance

TEST DI-07 latest address and equivocation
  fixture same identity records (sequence1,time999), (sequence2,time990), (sequence2,time995)
  ACT resolveIdentity; ASSERT only sequence2/time995 latest record
  add two different valid records tied at highest sequence/time
  ACT resolve with sufficient recordLimit
  ASSERT all tied records returned ordered by recordId, no arbitrary winner
  ACT limit smaller than whole tied set
  ASSERT reject before acceptance rather than conceal equivocation

TEST DI-08 locateShare withdrawal and complete groups
  fixture hostH positive seq1, then negative seq2 for same share
  ACT locateShare; ASSERT H omitted as current positive candidate
  fixture tied latest positive and negative records for H
  ACT locateShare; ASSERT both returned as conflict; H not unambiguous host
  ASSERT complete host groups sorted by XOR distance then host ID; ties by record ID
  ACT first group larger than recordLimit; ASSERT pre-acceptance limit rejection
  ACT later group does not fit; ASSERT no partial group returned

TEST DI-09 published trust lookup
  fixture several evaluator-subject pairs including score0 and tied records
  ACT findTrust(exact subject)
  ASSERT only exact subject's latest records, ordered evaluatorId then recordId
  ASSERT complete evaluator groups; oversized first tied group rejected
  ASSERT no averaging and no changes to requester's Ledger trust
  ACT absent subject; ASSERT empty paid result1, not a trust assessment

TEST DI-10 discovery keys and candidate order
  ACT identityKey(A.id); ASSERT result=A.id
  ACT shareKey(S), trustKey(C.id)
  ASSERT exact SHA256 of specified domain string concatenated with32-byte target
  FOR EACH fixed key/ID pair: ASSERT distance=independent unsigned256 big-endian XOR
  ACT return candidate entries
  ASSERT sorted distance then recordId for equivocations
  ASSERT each entry identity matches current valid address-record signer
  ASSERT returned candidates are hints requiring new identity authentication/Board terms

TEST DI-11 listIdentities pagination
  fixture known IDs x<y<z from current records/retained authorized observations
  ACT listIdentities(limit2); ASSERT [x,y],more=true,price2
  ACT afterIdentityId=y; ASSERT [z],more=false
  ACT cursor z; ASSERT [],more=false,price2
  ASSERT observation is not exported as transferable identity proof

TEST DI-12 listTrust full cursor
  fixture tied records r1<r2 for same evaluator/subject plus later tuple
  ACT listTrust(limit1); save returned complete tuple T1
  ACT afterEvaluator/Subject/Record=T1,limit1
  ASSERT next tied record returned without omission or duplicate
  FOR EACH partial cursor subset or invalid limit:
    ACT listTrust; ASSERT rejected without charge
  ASSERT records are not silently filtered by favorable/unfavorable scores
  ASSERT page describes disclosed local index, not all network trust

TEST DI-13 included retention check
  ACT owner check(indexId,recordId) before storedUntil with maximumPrice0
  ASSERT exact bytes and IDs; requester compares original bytes and record hash
  ASSERT local outcome=pass for timely match; allowance consumed once
  ACT second new check after allowance consumed
  ASSERT not entitled to another included check; no invented paid checkPrice
  ACT unauthorized owner/wrong record ID/expired placement
  ASSERT no protected evidence or allowance consumption
  ACT no complete evidence response
  ASSERT allowance not consumed; outcome=inconclusive
  ACT a fresh placement returns complete differing bytes
  ASSERT outcome=fail and this placement's one included allowance is consumed
  ASSERT no automatic refund

TEST DI-14 local checks for lookup/list
  FOR EACH query/list operation: ACT independently validate complete response
    ASSERT pass for correct signatures/kind/key/time/order/cursor/limits
    ASSERT fail if one required property is false in otherwise complete response
    ASSERT inconclusive if required data or local verification resources missing
  ASSERT pass does not prove completeness, reachability, possession or honest scores

TEST DI-15 bounded iterative lookup
  fixture budget2 queries, bounded candidate set and fan-out; referrals include cycles
  ACT lookup through authorized usable peers
  ASSERT each query separately priced/authorized; no hidden forwarded spending
  ASSERT queried identity/candidate deduplication; stops by query/time/credit/byte policy
  ACT referred peer with wrong authenticated ID or unusable credits/trust
  ASSERT not silently contacted as another identity or granted credits
  ASSERT empty local answer does not claim global absence

TEST DI-16 restart and independence
  RUN Services SV-09 with index batch and allowance effects
  ASSERT atomic placement/accounting and no double allowance consumption after lost local ack
  ACT start codec without indexer, File Sharing or paid Storage runtime
  ASSERT canonical address/share/trust encoding/verification still usable
  ACT start minimum node without Discovery; ASSERT configured contact bootstrap still works
```
