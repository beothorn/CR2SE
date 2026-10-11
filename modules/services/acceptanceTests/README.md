# Services acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md). Required suite. Install a
test-owned custom handler that can return a literal valid result, fail, or pause
at a contract boundary; do not download code from a description. Observe Board,
Ledger and handler ports. Default fixed quote is 7 B credits.

```text
TEST SV-01 definition contract
  ACT validate complete matching definition with input/output/check schemas
  ASSERT usable
  FOR EACH [missing input/output/check, missing check description,
            empty nested field description, unknown schema type, mismatched version]:
    ACT validate mutated definition; ASSERT unusable/rejected
  ASSERT matching custom service name alone does not prove compatible contract

TEST SV-02 complete type vocabulary
  FOR EACH (type,valid,invalid) IN [
    (bool,[true,false],[0,"true",null]),
    (int32,[-2147483648,2147483647],[-2147483649,2147483648]),
    (uint32,[0,U32_MAX],[-1,U32_MAX+1]),
    (int64,[-9223372036854775808,9223372036854775807],[belowMin,aboveMax]),
    (uint64,[0,U64_MAX],[-1,U64_MAX+1]),
    (string,[empty,UTF8("€")],[invalidUTF8,null]),
    (bytes,[empty,hex("00ff")],[null]),
    (float/double,[positiveZero,negativeZero,finiteValues],[forbiddenNaN,forbiddenInfinity])]:
    ACT validate each value against that schema
    ASSERT all valid accepted with exact value/bits; invalid rejected
  ACT schema explicitly permits NaN/infinity; ASSERT permitted logical values accepted

TEST SV-03 structured values and limits
  schema = object(required x:uint64, optional label:string, items:array<bytes>)
  ACT validate {x:1,items:[empty]}; ASSERT valid
  ACT label absent then label null; ASSERT absent valid, null invalid
  ACT unknown optional field; ASSERT ignored/retained without new semantics
  FOR EACH [missing x, wrong array item, excessive configured depth/count/bytes]:
    ACT validate; ASSERT REJECT before unbounded work
  ACT standard operation with field forbidden for its discriminator
  ASSERT REJECT even though generic schema extensions may be optional

TEST SV-04 selection, quote and capacity
  ACT propose fixed work with maximumPrice7 and issuer B
  ASSERT input metadata validated before body; no execute before acceptance
  ACT matching acceptance and complete input
  ASSERT one reservation7 precedes execution; handler receives immutable terms
  FOR EACH [unknown required precondition, unsupported handler, issuer mismatch,
            quote8 above bound7, definition mismatch, zero trust, exhausted capacity]:
    ACT separate proposal; ASSERT no execution; ASSERT noEffects

TEST SV-05 full input and fixed result validation
  FOR EACH [missing body byte, extra byte, wrong value type, invalid content hash]:
    ACT accept metadata then supply invalid complete input
    ASSERT no successful obligation; chargeDelta=0
  ACT valid input; handler returns literal output with finalPrice7
  ASSERT output matches definition; settle7 once
  ACT handler returns invalid output or finalPrice8
  ASSERT not exposed as valid successful completion or authorized settlement

TEST SV-06 metered and negative business results
  ACT Computation quote max60, valid completion billed1201 at rate1/1000
  ASSERT finalPrice2; release58 reserved credits
  ACT valid executionError or timeLimitReached completion
  ASSERT billable under Computation rules, not generic uncharged failure
  ACT empty Discovery/Feeds page
  ASSERT paid success at its fixed operation price
  ACT ordinary non-Computation handler requests post-execution metering
  ASSERT unsupported/rejected

TEST SV-07 wanted offers and local authority
  ACT remote peer offers to fulfill local wanted service
  ASSERT local publisher becomes requester only with locally authorized input/budget
  ACT offer carrying fabricated input or installation suggestion
  ASSERT cannot compel input, spending, installing or running provider code
  ASSERT TCP direction and stream opener do not select payer/provider

TEST SV-08 checks and independent outcomes
  ACT Storage/Messaging remote check with accepted positive checkPrice
  ASSERT requester retains expected byte; provider receives challenge only
  ACT well-formed wrong byte within deadline
  ASSERT outcome=fail and exact evidence charge, with no automatic refund
  ACT no complete valid evidence; ASSERT chargeDelta=0; outcome=inconclusive when timeout
  ACT Discovery entitled check at price0; ASSERT accepted within allowance
  ACT remote call to local-only check; ASSERT no invented remote operation
  ACT local verifier lacks original evidence; ASSERT inconclusive

TEST SV-09 durable coordination fault matrix
  FOR EACH cut IN [before reservation ack, after reservation before prepare,
    after handler prepare, after Ledger prepare, before durable decision,
    after durable commit decision, after one participant commit,
    after both commits before success reply]:
    fixture one stateful operation K, price7, valid complete input and result
    ACT crash coordinator/affected participant at cut; drop the cut's reply
    ACT restart with only durable state; recover decision/status; deliver duplicate local messages
    IF commit decision persisted:
      ASSERT eventually exactly one visible resource and one price7 effect
      ASSERT no abort can replace decision; no re-execution to recover a reply
    ELSE:
      resolve through recovered coordinator to one permitted commit or abort decision
      ASSERT either consistent success/resource+price7 or abort/no resource+no charge
      ASSERT no guessing abort from timeout; no successful partial state
    ASSERT conflicting reads/spends gated while effects unresolved
    ASSERT no duplicate reservation/charge; immutable decision and effect references survive
  ASSERT lifetime service replay guards are not removed by coordination compaction

TEST SV-10 explicit failure, cancellation and uncertainty
  ACT explicit handler rejection before successful commitment
  ASSERT no charge and releasable reservation
  ACT lose connection/IPC reply after possible commitment
  ASSERT outcome_unknown or recoverable pending state, not proof of rollback
  ACT cancel committed operation; ASSERT durable obligation/accounting not erased
  ACT repeat identical input on a new stream without service replay key
  ASSERT not mistaken for same local operation; no automatic retry initiated

TEST SV-11 optional handler lifecycle
  ACT register Storage only; invoke optional family
  ASSERT unsupported before acceptance; no substitute family dispatch
  ACT publish wanted custom service with requester codec but no local provider
  ASSERT remote provider may fulfill it through authorized requester path
  ACT remove handler from new selection while accepted work remains
  ASSERT retained handler/recovery path honors accepted obligations

TEST SV-12 process boundary and result lifetime
  ACT same invocation through direct and serialized adapters
  ASSERT identities, uint64, quote bytes/hash, bodies and result are equal
  ACT expire client session while durable commit pending
  ASSERT coordinator's retained result does not disappear with session blob
  ACT unknown local contract version or forged commit caller
  ASSERT REJECT before effects; no access to another module's private state required
```
