# Board acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md), including common cases.
Required suite. Fixtures have complete matching definitions; `o` is a provided
custom fixed-price offering at price 7, issued by B, with service version 1.
Only schema/definition validation, local persistence and capability ports are
needed; no running service provider is needed to validate a document.

```text
TEST BD-01 empty and populated Boards
  ACT validate {version:1, providedServices:[], wantedServices:[]}
  ASSERT valid
  ACT publish o and matching definition; read snapshot and definition(o.id)
  ASSERT exact offering/definition identity fields match fixture
  ASSERT Board contains no input/output/check schema; definition contains all three

TEST BD-02 document parsing
  FOR EACH [missing version/list, wrong list type, unsupported version,
            invalid UTF8, malformed JSON, duplicate JSON member]:
    ACT validate malformed Board; ASSERT REJECT; prior publication unchanged
  ACT lossless parse price=9007199254740993 and price=U64_MAX
  ASSERT exact integers retained and re-emitted, never rounded

TEST BD-03 offering fields and identifier uniqueness
  FOR EACH required offering field: ACT malformed(field); ASSERT unusable/rejected
  FOR EACH duplicate ID placement IN [same provided list, same wanted list, across lists]:
    ACT publish duplicate-ID candidate; ASSERT REJECT; prior snapshot unchanged
  ASSERT neither first-wins nor last-wins selects a duplicate as unambiguous
  ACT same service/version under two different offering IDs
  ASSERT both available with their own terms

TEST BD-04 prices and exact ranges
  FOR EACH price IN [1,U64_MAX]: ACT validate fixed offering; ASSERT valid
  FOR EACH price IN [0,-1,U64_MAX+1,1.5,"7",true,null]:
    ACT validate fixed offering; ASSERT REJECT
  FOR EACH [neither price nor pricing, both price and pricing, empty pricing.model,
            checkPrice=0, checkPrice=U64_MAX+1, embedded input/output/check]:
    ACT validate mutated offering; ASSERT REJECT
  ACT valid known family pricing whose advertised maximum overflows uint64
  ASSERT unusable/rejected before a requester can accept overflowing work

TEST BD-05 roles and issuer
  ACT select provided o with publisher B and peer A
  ASSERT provider=B; requester=A; issuer=B
  ACT select wanted o with publisher B and peer A
  ASSERT provider=A; requester=B; issuer=B
  ASSERT changing TCP opener changes neither role assignment nor issuer
  FOR EACH creditIssuer IN ["self","own","remote",bad textual ID]:
    ACT validate offering; ASSERT REJECT

TEST BD-06 compatibility and untrusted hints
  ACT read Board containing known o and another unknown service/version/pricing model
  ASSERT known o remains selectable; unknown offering is not automatically usable
  ACT select offering with unknown required precondition
  ASSERT cannot accept until semantics are understood
  ACT forward original Board with unknown optional nested metadata
  ASSERT unknown fields preserved; no new mandatory behavior inferred
  ACT read suggestion with install/run/spend instructions
  ASSERT no installation, execution, key access or spending commands emitted

TEST BD-07 definition consistency
  FOR EACH field IN [id,service,serviceVersion,description]:
    ACT publish o with definition differing only in field
    ASSERT REJECT; existing snapshot unchanged
  ACT select remotely fetched mismatching definition
  ASSERT no invocation accepted using the mismatched pair
  ACT fetch missing/removed offering definition
  ASSERT failure, not a nearby contract/version substituted

TEST BD-08 atomic publication
  pin snapshot S1; stage S2 changing offering and definition together
  race readers with publish(S2)
  ASSERT each local read sees a complete S1 or complete S2 pair
  ASSERT pinned S1 remains immutable
  ACT storage failure before S2 publication; restart
  ASSERT no partly published S2; last acknowledged snapshot recoverable

TEST BD-09 stale selection and accepted terms
  A selects price=7; B changes current price to9 before quote
  ACT quote; ASSERT A must explicitly accept9 or decline without charge
  A accepts price=7 on another already quoted valid attempt; B then removes offering
  ASSERT that attempt retains accepted price7 and obligations
  ASSERT removal blocks new selection, not completion of accepted work

TEST BD-10 attribution and bounds
  ACT fetch Board directly over authenticated B context
  ASSERT provenance=B
  ACT receive identical document forwarded by C
  ASSERT not automatically attributed as authenticated publication by B
  ACT publish Board/definition exceeding allowed peer control response size
  ASSERT REJECT before advertising an unretrievable definition
  ACT reorder both service arrays
  ASSERT no implicit priority or change of meaning
```
