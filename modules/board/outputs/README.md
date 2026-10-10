# Board outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Publication result and local snapshot reference | Local administrator or [Services](../../services/inputs/README.md); complete Board and definitions become visible together, or the prior snapshot remains unchanged. |
| Board snapshot | [Peer Control](../../peer-protocol/inputs/README.md), Services and local applications: exact validated JSON with provided/wanted direction and explicit issuer. No private keys or balances. |
| Definition | Peer Control and Services: matching offering identity fields and complete input/output/check schemas from the selected snapshot. |
| Selection/usability decision | Services or local client: selected immutable offering and definition, or unsupported/stale/missing result with reason. It does not reserve capacity or authorize spending. |
| Cache provenance/invalidation | Local consumers: authenticated publisher, receipt/snapshot association and changed selection. Forwarded unknown metadata is preserved when claiming to relay the original. |

Board publication changes only future negotiations. Accepted terms remain
available in Services' durable invocation context. Concurrent local reads must
not mix one revision's offering with another revision's definition. Remote
Board and definition requests can race with publication; Services detects
mismatches and reselects before accepting work.

## Independent acceptance examples

- Publish two offerings with distinct IDs and matching definitions, then read
  both concurrently while replacing the snapshot: no mixed local revision.
- Reject duplicate IDs, rounded/out-of-range prices or a mismatching definition
  without altering the prior publication.
- Validate an unknown optional family's offering as metadata, mark it unusable
  for a client lacking its semantics, and still select a known Storage offering.
