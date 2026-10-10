# Node API outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Session result | Local client: version and message/chunk/blob limits, only after authorized opening. |
| Terminal response | Local client: original `id`, `ok:true,result` or `ok:false,error`; exactly one per accepted request while connected, possibly out of order. |
| Connection/metadata result | Local client: scoped connection handles and authenticated peer IDs, current Board or selected definition. No cross-session handle access. |
| Invocation result | Local client: complete `service_result`, `final_price`, and third-party `transfer_fee`/`settlement_state` when applicable. Large bytes/text use finished read-only local blobs. |
| Check result | Local client: requester-computed `check_result` and final price, using retained original expectations; otherwise inconclusive. |
| Blob result | Local client: handle, written count, complete length, Base64 data/eof or close acknowledgement according to operation. Finish makes exact-length contents immutable. |
| Progress / cancellation response | Local client: optional correlated progress without terminal `id`/`ok`, or `cancel_requested`. Neither asserts completion, payment or rollback. |
| Authorized module command | [Transport](../../transport/inputs/README.md), [Peer Control](../../peer-protocol/inputs/README.md) or [Services](../../services/inputs/README.md): original client authority, bounded typed arguments, correlation and cancellation context. |

No result exposes raw private keys, client tokens, other sessions' blobs or
untrusted internal diagnostics. Parse/framing failure closes the session; valid
requests get structured operation failures. Unknown operations/capabilities
return the specified error without dispatch to a substitute family.

Publish output handles only after validating the full peer result. Session loss
discards temporary blobs and cancels uncommitted work, while accepted durable
Ledger/service effects survive. Application recovery data must be copied out
before closing. The node's internal result journal cannot rely on that client
blob session as its only copy.

## Independent acceptance examples

- Fake Transport/Peer Control/Services ports suffice to test token/version
  rejection, out-of-order responses and exact uint64/blob translations.
- Try another session's blob and malformed/gapped writes: no unauthorized access
  or mutation; pinned blobs cannot be closed until released.
- Cancel after uncertain remote commitment or drop the client session: report
  uncertainty where connected, keep durable obligations, and never repeat work.
