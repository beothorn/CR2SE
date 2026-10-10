# Services outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Validated definitions/capability descriptions | [Board](../../board/inputs/README.md) and composition: exact schema, identifiers and modes. Presence of a definition alone does not authorize advertising an unavailable provider. |
| Negotiation decision and price data | [Peer Control](../../peer-protocol/inputs/README.md): validated requester/provider roles, terms, fixed price or Computation formula/maximum, provider-size factors and explicit rejection where needed. |
| Reserve/prepare/commit/abort/status request | [Ledger](../../ledger/inputs/README.md): exact operation, terms, amount and authority, using the common durable protocol. |
| Assess/execute/evidence/verify and lifecycle request | Selected family [handler](../../../ModuleContracts.md#common-service-handler-boundary): complete context and bounded values through its inputs contract. No direct table or socket access. |
| Complete result / failure / outcome unknown | Peer Control or local client, optionally [Node API](../../node-api/inputs/README.md): validated typed output, final price, durable references and independent payment state. |
| Local check outcome | Requester: pass/fail/inconclusive with available evidence. No automatic trust change or refund. |

Services coordinates family effects and Ledger settlement with a local
transaction or the [recoverable protocol](../../../ModuleContracts.md#durable-effects-across-process-boundaries).
It records accepted terms and never reprices committed work after a Board update.
Fixed-price success matches the quote; Computation settles only its bounded
final amount. Explicit uncommitted failure releases capacity. Uncertainty must
retain enough state to determine local commitment without re-executing work.

Services does not turn optional modules into mandatory runtime dependencies.
An absent or incompatible handler fails before acceptance. Existing accepted
work remains recoverable if a handler is being disabled or upgraded.

## Independent acceptance examples

- A fake family returns an invalid output or an over-bound price: Services
  rejects it rather than authorizing a successful settlement.
- With Board/Ledger substitutes, test provided and wanted roles, exact quote
  acceptance and a missing handler; no unauthorized execution occurs.
- Crash after the durable decision but before one participant acknowledges:
  recovery delivers the same decision and never executes or charges twice.
  Compare behavior through direct calls and a serialized adapter.
