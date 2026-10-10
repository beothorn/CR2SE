# Node API inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Optional in the minimum node. This module supplies the standard application
boundary. A core node can instead use authorized embedded calls or another
local administration interface. If the Node API is supplied, its specified
operations, authentication, values and failures must be implemented consistently.

## Accepted calls and events

| Input / source | Values and expectations |
|---|---|
| Session configuration / local administrator | Explicit loopback endpoint, independent random 32-byte client tokens and client spending/resource permissions. Embedded mode uses hosting-application authority. |
| Session opening / local client | `session.open`, version 1 and canonical Base64 token before any other operation. Unsupported version/invalid token fails closed. |
| Request / authenticated local client | UTF-8 JSON line, depth <=32, <=1,048,576 bytes before LF; nonempty unique in-flight `id` <=128 UTF-8 bytes and operation. Reject duplicate members. |
| Blob calls / local client | create/write/finish/read/close with session-owned handles, exact lengths, sequential write offsets and <=65,536-byte chunks. No arbitrary filesystem path handles. |
| Connection calls / local client | Open/list/close/ping with session authority, validated endpoint and expected ID for known contacts. Apply local connection policy. |
| Board/service calls / local client | board.get, service.get, invoke/check/offer selection and arguments. Invoke/check require issuer and maximum price; offer requires supported local provider and maximum resource price. |
| Ledger controls / local client | Balance, canonical signed transfer, transfer lookup or encrypted claim redemption under session authority; exact Peer Protocol/Ledger lengths and fees. |
| Cancel / local client | Original active request ID. Cancellation request is not proof of rollback. |
| Module responses / Transport, Peer Control and Services | Authenticated connections, attributed metadata, full valid results, settlement state, evidence/check results or explicit uncertainty, correlated with the original client request. |

All exact request field names are in the [operation tables](../README.md#operations)
and [blob tables](../README.md#values-and-blobs). Node API translates handles to
[Transport](../../transport/inputs/README.md), [Peer Control](../../peer-protocol/inputs/README.md)
and [Services](../../services/inputs/README.md) contracts. It does not inspect
their sockets, databases or keys. Authorized Services dispatch reaches optional
families; no family is a mandatory Node API runtime dependency.

Pin complete input blobs through terminal invocation state; outputs use fresh
session-scoped handles. Enforce quotas over temporary, input and output bytes.
Descriptions cannot authorize installation, spending or key access.
