# Services inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Required in the minimum node because Storage and every optional family use the
same typed contract and invocation lifecycle. Services owns dispatch and local
coordination; it does not own family resources, Board publication or balances.

## Accepted calls and events

| Input / source | Values and expectations |
|---|---|
| Register requester codec/provider handler / composition | Exact service/version, schema, supported modes, assessment/execution/check ports and resource policy. Register only locally authorized implementations. |
| Validate definition/value / local caller, Board validator or Peer Control | Complete schema and logical value, field descriptions, bounds and operation semantics. Preserve exact integers and distinguish omission from null. Pure validation does not require running handlers. |
| Select terms / [Board](../../board/outputs/README.md) | Immutable offering and matching definition, publisher, direction and snapshot association. Unknown mandatory semantics make that selection unusable. |
| Invoke/check/offer / local requester or [Peer Control](../../peer-protocol/outputs/README.md) | Trusted peer context, exact selection, arguments/body descriptors, explicit issuer, price/resource bound and local caller authority. Wanted publisher input comes from an authorized local source. |
| Quote/acceptance/body event / Peer Control | Exact quote bytes/hash and terms, validated acceptance and complete ordered input. No execution before reservation and full service-required validation. |
| Handler assessment/result / installed family | Price factors/provider-dependent sizes, acceptance limits, typed output, final price, staged state effects and result reference. Validate against accepted contract; no arbitrary ledger changes. |
| Reservation/settlement response / [Ledger](../../ledger/outputs/README.md) | Operation-bound hold, failure or durable status; enforce maximum price including agreed third-party fee. |
| Check evidence and expectations / family/client | Original input, accepted terms, complete output/evidence, expected byte or manifest and timing where needed. Missing evidence yields inconclusive, not automatic pass. |
| Cancellation/status/recovery / local coordinator | Original durable operation key and exact recorded references. A dependency timeout is not an abort decision. |

Services uses platform durable journaling and bounded clocks/queues. Handlers
are supplied through the [common service ports](../../../ModuleContracts.md#common-service-handler-boundary).
It can be tested using a synthetic handler, immutable Board snapshots, fake
Peer Control events and a contract-compatible Ledger. No optional family or
Node API runtime is required.
