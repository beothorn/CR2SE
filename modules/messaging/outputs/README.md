# Messaging outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Results returned through Services

Outputs carry matching `operation`; fields retain the input/specification types.
Consumers are [Services](../../services/inputs/README.md), its Ledger/Peer
Control adapters, and the sender or recipient application as authorized.

| Operation | Successful output / guarantee |
|---|---|
| `store` | `placementId`, `messageId`, `acceptedAt`, `expiresAt`, `price`. Complete payload and placement durable; unique placement ID, one independent provider agreement. |
| `discover` | `messages`, `more`, `price`. Entries contain placement/message/sender IDs, sender time, encoding, size/hash and acceptance/expiry; ordered by `(acceptedAt, placementId)`, recipient-only, bounded and exclusive cursor. Empty page is a paid success. |
| `recover` | Complete original signed message metadata and payload, `placementId`, `recoveryId`, `recoveredAt`, recipient key/signature and provider signature. Atomic pending-to-recovered transition and exact receipt. Price is in the peer envelope, not an invented output field. |
| `status` | Placement/message/sender/recipient IDs, hash, pending/recovered state, expiration and price; recovered adds recorded recovery ID/time and both signatures/recipient key. No payload or proof of human reading. |
| `renew` | `placementId`, `previousExpiresAt`, `expiresAt`, `price`; one extension under the expected-expiration guard. |
| `remove` | `placementId`, `removalId`, `removed:true`, `releaseCredits`, `price`; exact quoted charge and release credits, logical removal with both ledger effects applied once. |
| Remote check | `placementId`, `offset`, `value:bytes[1]`; requester derives the check outcome. |
| Local validation/check | Validated sender/receipt/payload or pass/fail/inconclusive as appropriate; decrypt only after authentication. No automatic refund or trust change. |

Local prepared effects/results go to Services for recoverable settlement.
Recovery caches the **complete** successful output until current `expiresAt`,
including after renewal. Same caller and exact request/recovery ID return it
without a second charge; conflicting recovery fails. Removal retains exact
replay output for the ledger lifetime so neither charge nor release credit can
apply twice. Renew and remove/recover state transitions serialize per placement.

## Independent acceptance examples

- Store with a fake Services context and verify restart preserves complete
  payload, sender signature and expiration; reject another identity's access.
- Lose a recovery response: exact retry returns byte-identical cached output,
  price and receipt; another recovery ID cannot recover again.
- Repeat removal after a lost local/remote reply: one remove charge and one
  release-credit adjustment. Race removal with recovery: only a valid state
  transition succeeds, with matching durable accounting.
