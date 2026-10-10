# Peer Control / Peer Protocol inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Required in the minimum node. Peer Control is the role implemented by this
existing Peer Protocol module; `cr2se.peer` version 1 remains the wire name.
It owns exchange framing and ordering, not service resources or balances.

## Accepted calls and events

| Input / source | Values and expectations |
|---|---|
| Authenticated stream events / [Transport](../../transport/outputs/README.md) | Local/remote IDs, unique connection/stream context, `cr2se.peer` version 1, ordered verified bytes, END or failure. Context is trusted adapter data, never a payload assertion. |
| Local metadata request / application, optionally Node API | Connection handle and `board.get` or offering-specific `service.get`. Apply control-rate/resource bounds. |
| Local invoke/check/offer / Services requester adapter or local client | Connection, offering/publisher, exact service/version, typed arguments, explicit issuer and total spending/resource bound. Wanted work also requires installed provider capability and authorized publisher input. |
| Board/definition response / [Board](../../board/outputs/README.md) | One consistent local snapshot, or an attributed remote document for consumption. Exact JSON fits the control limit. |
| Assessment, accepted context, result or failure / [Services](../../services/outputs/README.md) | Validated terms and price, reservation/acceptance decision, complete typed output/body references, final price and durable outcome state. Peer Control must not invent missing economic authorization. |
| Ledger controls/results / [Ledger](../../ledger/outputs/README.md) | Typed balance, transfer, claim and fee-acceptance decisions under authenticated caller context. |
| Cancellation/deadline / local caller or Transport | Correlated exchange and reason; commitment status must be consulted before reporting a safe failure. |

Enforce control records of 1..1,048,576 bytes, binary chunks of 1..65,536 data
bytes, depth 32, canonical numeric/Base64 forms, descriptor lengths and exact
body offsets. Reject bad order or malformed framing at the specified stream
scope. Retain exact quote JSON bytes for `quoteHash`; reserialization is not an
equivalent acceptance input.

All other modules can be substituted through these ports. Node API is one
optional caller; Discovery is one optional service reached through Services.
No family-specific database or transport socket internals are required.
