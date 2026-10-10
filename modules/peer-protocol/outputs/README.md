# Peer Control / Peer Protocol outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Open/data/end/cancel/error command | [Transport](../../transport/inputs/README.md): existing `cr2se.peer` records on one scoped exchange stream. No new frame types. |
| Board/definition query or attributed received document | [Board](../../board/inputs/README.md), [Services](../../services/inputs/README.md), local requester: authenticated publisher provenance, exact document and selection. |
| Proposal/quote/acceptance/input events | Services: immutable peer context, exact offered contract, mode, bounded metadata, quote bytes/hash and complete body state. Detached bodies never precede accepted terms. |
| Ledger control command | [Ledger](../../ledger/inputs/README.md): decoded exact order/envelope and authenticated requester plus fee acceptance, without implied administrative authority. |
| Complete invocation result | Services/requester or [Node API](../../node-api/inputs/README.md): typed metadata and exact complete bodies, final price, peer/terms association and separately tracked settlement state. |
| Failure/unknown outcome | Services and local caller: existing peer error, transport error or uncertainty, with exchange identity. No automatic repeat of side effects. |

A received success requires all declared body bytes, `result.end`, and normal
stream completion. Partial outputs are provisional. A quote authorizes nothing
until accepted with its exact hash and a valid reservation. A local send result
does not prove the remote application received it.

Recognized Messaging recovery/removal retries may return the original result
directly after a matching proposal as specified; they require the family's
validated caller/request match and original price. They do not create a new
charge. No generic cross-connection job/status/resume operation is added.

## Independent acceptance examples

- Use fake authenticated streams and Board/Services/Ledger ports to run metadata,
  fixed quotes, wanted-role reversal and ledger fee acceptance.
- Reproduce existing encoding vectors, including full uint64 values and bodies
  split at arbitrary frame boundaries. Gaps, overlaps and missing ends fail.
- Disconnect after acceptance: report uncertainty when effects may be committed.
  An unsupported family is rejected without dispatch or balance change.
