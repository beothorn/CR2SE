# Discovery inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Optional. The Discovery runtime owns its index, paid placements and included
check allowances. Its canonical address/share/trust codecs are reusable formats
that can be implemented without an indexer. It consumes
[Services context](../../services/outputs/README.md), [Identity](../../identity/outputs/README.md),
[Cryptography](../../cryptography/outputs/README.md), durable local persistence,
clock and randomness. No File Sharing server or paid Storage invocation is needed.

## Operations received from Services

Inputs carry `operation`, except the remote retention check. IDs below are 32
bytes and limits are uint32; signed records are exact canonical byte strings.

| Operation | Fields beyond `operation` | Expectations |
|---|---|---|
| `index` | `records:array<bytes>` | Nonempty bounded total bytes/count, unique record IDs, valid canonical signatures and current times. Any authenticated payer can index another identity's unchanged record. Validate the entire batch before effects. |
| `resolveIdentity` | `identityId`, `recordLimit`, `indexerLimit` | Exact identity key and positive limits within offering. Preserve latest tied equivocations. |
| `locateShare` | `shareId`, `recordLimit`, `indexerLimit` | Exact share key; complete tied host groups within limits. A signed host claim is not a reachability proof. |
| `findTrust` | `subjectId`, `recordLimit`, `indexerLimit` | Exact subject, complete evaluator groups; no averaging of scores or change to local Ledger trust. |
| `listIdentities` | Optional `afterIdentityId`; `limit` | Exclusive unsigned-byte cursor and current list limit. |
| `listTrust` | Optional `afterEvaluatorId`, `afterSubjectId`, `afterRecordId`; `limit` | All three cursor fields present or absent; exclusive full-tuple order, including equivocation records. |
| Remote retention check | `indexId`, `recordId` | Authenticated placement owner before `storedUntil`; original included allowance still available. Accept price zero only for this entitlement. |

Additional local inputs are canonical record creation/validation requests,
authenticated connection observations (optional, from Transport through an
adapter), configured bootstrap indexers and bounded lookup budgets. An observation
is local metadata, not transferable proof. Imported scores never automatically
overwrite Ledger trust.

The requester-side iterative lookup adapter uses Services/Peer Control for each
separately authorized paid hop. Missing Discovery can be replaced by configured
contacts for core use, but cannot fake successful index/query results. Local
checks consume original requests, terms, complete responses, clock and original
indexed record bytes for retention checks.
