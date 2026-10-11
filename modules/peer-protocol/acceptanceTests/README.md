# Peer Control acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Required
suite. Supply fake authenticated Transport streams and Board/Services/Ledger
ports. Use the [encoding vectors](../pseudocode/TestVectors.md) as independent
expected bytes. Each exchange uses `cr2se.peer` version1 and a fresh stream.

```text
TEST PP-01 records across frame boundaries
  ACT encode board.get and the pinned binary body record
  ASSERT complete bytes equal existing vectors
  FOR EACH split at every record-header/body position, single bytes, coalesced records:
    ACT decode through DATA events
    ASSERT same ordered logical records; Transport frame boundaries ignored

TEST PP-02 record parsing failures
  FOR EACH [unknown kind, control length0 or1048577, binary data length0 or65537,
            truncated record, malformed/duplicate-member/trailing JSON, invalid UTF8,
            depth33, missing type, illegal message order]:
    ACT receive malformed record
    ASSERT affected stream terminates PROTOCOL_ERROR; other streams remain usable
    ASSERT no excessive allocation or handler execution
  ACT permitted maximum-size control and65536-data-byte body fixture
  ASSERT decoded without truncation

TEST PP-03 exact logical values
  FOR EACH uint64 IN [0,9007199254740993,U64_MAX]:
    ACT encode/decode; ASSERT exact canonical decimal string and logical value
  ACT int64 minimum; ASSERT "-9223372036854775808" preserved
  FOR EACH invalid64 IN ["+1","01","-0","1e2","1.0",numeric JSON value,null]:
    ACT decode declared64-bit field; ASSERT REJECT
  ACT float/double negative zero; ASSERT bit objects preserve sign
  ACT allowed NaN; ASSERT canonical bits7fc00000/7ff8000000000000
  ACT forbidden NaN/infinity or noncanonical NaN bits; ASSERT REJECT
  ASSERT Board/definition uint64 JSON numbers remain exact, not converted through float

TEST PP-04 inline and detached values
  ACT encode bytes of length0,4096,4097 and multibyte UTF8 text
  ASSERT empty bytes inline; inline decoded length never exceeds4096
  ASSERT large byte descriptor length counts logical bytes
  schema fields inserted in order z,a; each contains detached bodies
  ACT assign descriptors; ASSERT traversal uses unsigned UTF8 field order a,z
  ASSERT array traversal uses index order; IDs start0 and each appears once
  FOR EACH [noncanonical Base64, whitespace, missing padding, nonzero unused bits,
            unknown descriptor field, duplicate bodyId, gaps/overlap/extra/missing bytes,
            bodies in wrong ID order, invalid final UTF8]:
    ACT decode; ASSERT no successful logical value

TEST PP-05 metadata exchanges
  ACT board.get and service.get for available offering
  ASSERT attributed Board/definition response, no binary bodies, END both directions
  ASSERT no service charge; bounded control policy still enforced
  ACT missing offering; ASSERT failure, not synthetic definition

TEST PP-06 quote acceptance binds exact bytes
  Services quotes fixed7 with explicit issuerB and empty pricingInputs
  ACT propose with bound7; receive quote bytes Q
  ASSERT accept.quoteHash=oracleSHA256(Q), not hash of reserialized object
  ACT acceptance with wrong hash/ID, or input body before acceptance
  ASSERT no execution/settlement; protocol failure as applicable
  ACT quote changes issuer, contract/version/description, or exceeds bound
  ASSERT cannot silently accept; contract change requires definition refresh

TEST PP-07 sizes, formulas and fee bounds
  FOR EACH operation IN [Files manifest/download, Storage renew, Messaging recover/renew]:
    ACT quote with specified provider-size pricingInput
    ASSERT field has exact uint64 representation and feeds independent price calculation
    ACT completed output disagrees with quoted size
    ASSERT not accepted as valid output
  ACT third-party price7 plus fee2 with spending bound8
  ASSERT rejected before acceptance; bound9 permits exact agreement
  ACT metered quote for non-Computation family; ASSERT unsupported/rejected

TEST PP-08 input and result completion
  ACT accepted input descriptors, exact body bytes, input.end then END
  ASSERT handler receives complete input only after required validation
  ACT result metadata, exact bodies, result.end then END; local direction already ended
  ASSERT complete result returned with finalPrice equal accepted fixed price
  FOR EACH missing/extra body, missing terminal marker, abnormal Transport close,
           output.price different from envelope.finalPrice:
    ACT affected result; ASSERT no successful complete result
  ASSERT provisional bytes never exposed as success or authenticated plaintext

TEST PP-09 failure and uncertain effects
  ACT explicit failure before successful uncommitted output
  ASSERT failure code preserved; reservation releasable; no charge
  ACT failure during provisional output before result.end
  ASSERT provisional result discarded
  ACT failure after result.end
  ASSERT illegal transition, not retroactive rollback
  ACT disconnect/cancel after possible durable effect
  ASSERT outcome_unknown; no generic remote job-status or automatic retry invented

TEST PP-10 wanted roles
  B opens stream to wanted publisherA with offer
  ACT A supplies locally authorized propose; B quotes; A accepts/sends input
  ASSERT requester=A; provider=B; publisher=A despite openerB
  ASSERT incoming offer cannot fabricate A's input or spending authorization

TEST PP-11 check binding and idempotent Messaging retry
  ACT paid byte check; ASSERT mode=check and provider evidence lacks computed outcome
  ACT entitled Discovery check; ASSERT price0 and one placement-bound allowance
  ACT remote attempt at local-only check; ASSERT unsupported
  fixture exact authorized cached Messaging recovery/removal request
  ACT matching propose; ASSERT direct identical result with original price, no new quote/body/charge
  ACT mismatched caller/request/replay ID or unrelated early result
  ASSERT cannot use cached-success exception

TEST PP-12 ledger controls
  FOR EACH ledger.balance, ledger.transfer.get, ledger.claim.redeem:
    ACT valid request; ASSERT decoded exact values and authenticated caller reach Ledger
    ASSERT specified response and END returned, no service invocation dispatched
  ACT ledger.transfer with valid121-byte order, key32, signature64 and maximumFee2
  ASSERT fee quote precedes commitment; accept must match transferId and exact fee
  ACT owner END before required fee acceptance; ASSERT transfer not committed
  ACT exact accepted retry; ASSERT original result returned directly without requote

TEST PP-13 independent settlement and bounded control
  ACT service result paid in C credits; requester forwards alleged receipt
  ASSERT not sufficient; provider queries C using separate authenticated stream
  ASSERT reused transfer cannot settle another invocation
  ACT abusive metadata/control load under configured quota
  ASSERT refusal/rate limit without free resource execution or unbounded queues
```
