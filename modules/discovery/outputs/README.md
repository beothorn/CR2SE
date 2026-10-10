# Discovery outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Results returned through Services

Invocation results carry matching `operation` and `price:uint64`. IDs are 32
bytes, times uint64 Unix seconds, record arrays contain exact encoded bytes.
Consumers are [Services](../../services/inputs/README.md) and requester lookup
clients, which may provide validated hints to Identity/Transport applications.

| Operation | Output beyond operation/price | Guarantee |
|---|---|---|
| `index` | `acceptedAt`, `placements:[{indexId,recordId,storedUntil}]` | Same order as submitted records, all durably retained or none accepted; one included check allowance per placement. |
| `resolveIdentity` | `identityId`, `addressRecords`, `indexers` | Current latest exact-identity records, complete tied latest set or pre-acceptance limit rejection. |
| `locateShare` | `shareId`, `shareRecords`, `indexers` | Complete host groups in specified XOR-distance order; tied positive/negative conflict remains visible. Resolve host addresses separately. |
| `findTrust` | `subjectId`, `trustRecords`, `indexers` | Current exact-subject statements ordered by evaluator and record ID, complete tied groups. |
| `listIdentities` | `identities`, `more` | Unique ordered IDs strictly beyond cursor. It describes this provider's knowledge, not global membership. |
| `listTrust` | `trustRecords`, `more` | Complete selected page in `(evaluatorId,subjectId,recordId)` order. No selective suppression of scores within the advertised index. |
| Remote check | `indexId`, `recordId`, `record` | Exact retained bytes; complete valid evidence consumes the allowance once, with no separate check price. |

Candidate indexer entries and record validity follow the specification's exact
schema, ordering and timing limits. Empty query/list results are charged
successes and do not prove global absence. Pagination is not a frozen snapshot.
Local verification returns pass/fail/inconclusive without assigning trust or
claiming future reachability. Timeouts do not prove loss of a retained record.

Canonical record encoders emit exact signed bytes and record IDs for consumers
such as [File Sharing catalogs](../../file-sharing/inputs/README.md), without a
running indexer. Optional iterative lookup emits bounded candidates and explicit
budget/termination state; each next paid query requires caller authority.

Index state, retained results and allowance consumption participate in Services'
local recovery protocol. No partial successful batch or double consumption may
appear after a crash or lost local acknowledgement.

## Independent acceptance examples

- A batch containing one invalid signed record leaves no placements or charge;
  a valid batch survives restart with exact bytes and ordered IDs.
- Query tied latest conflicting records with too small a limit: reject before
  acceptance where required instead of hiding an equivocation.
- Page `listTrust` through tied records using all three cursor fields; consume
  an included check once despite repeated local commit delivery.
