# Storage outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Results returned through Services

All invocation outputs carry their matching `operation`. Prices are exact
uint64 and equal the accepted fixed quote; peer envelopes carry check prices.
IDs/hashes are 32 bytes and all times below are uint64 Unix seconds.

| Operation | Successful output | Required guarantee |
|---|---|---|
| `store` | `leaseId`, `sizeBytes`, `contentHash`, `acceptedAt`, `expiresAt`, `price` | Unique random lease ID; exact bytes and owner/terms are durable before success. `expiresAt = acceptedAt + retentionSeconds`, overflow checked. |
| `retrieve` | `leaseId`, `offset`, `data`, `contentHash`, `price` | Exactly requested range; hash describes the entire object. A timely accepted transfer completes even if the lease expires during transfer. |
| `renew` | `leaseId`, `previousExpiresAt`, `expiresAt`, `price` | One serialized extension with matching expected expiration; failed renewal leaves prior lease intact. |
| `remove` | `leaseId`, `removed:true`, `price` | Ends logical availability and obligation; no refund. Removing an already inactive lease fails. |
| Remote check | `leaseId`, `offset`, `value:bytes[1]` | Exact evidence, no provider-computed outcome. Only complete valid evidence permits the check charge. |
| Local check | `outcome`, `leaseId`, `offset`, optional returned `value` | Requester computes pass/fail/inconclusive under the specified timing/evidence rules. |

Consumers are [Services](../../services/inputs/README.md), which coordinates
[Ledger](../../ledger/inputs/README.md) effects and [Peer Control](../../peer-protocol/inputs/README.md)
delivery, then the requester application. Store/renew results update the
requester's recovery catalog; they establish one agreement at one provider.
They do not establish a replica set or reveal other leases.

The handler returns staged state/result references and durable lifecycle status
to Services. A changed Board does not remove a lease. On restart, leases,
expiration guards and committed local settlement recover together. Lost remote
output may remain outcome unknown; generic store/retrieve/remove have no
cross-connection deduplication promise. Renewal's expected-expiration guard
prevents repeating the same extension, but does not retrieve a lost result.

## Independent acceptance examples

- With fake Services/Ledger ports, stage an upload with a wrong hash: no active
  lease and no successful settlement. A valid upload survives provider restart.
- Retrieve a range at expiration boundary and verify complete data/hash metadata;
  a different authenticated identity learns nothing about the lease.
- Race two renewals with the same expected expiration: one succeeds. Lose a
  local commit acknowledgement and recover the same effect without another charge.
