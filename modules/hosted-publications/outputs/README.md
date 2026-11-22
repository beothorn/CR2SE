# Hosted Publications outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Results returned through Services

Outputs carry the matching `operation`; fields keep the specification types.
Consumers are [Services](../../services/inputs/README.md), its Ledger/Peer
Control adapters, and the publisher or reader application.

| Operation | Successful output / guarantee |
|---|---|
| `store` | `placementId`, `publicationId`, `acceptedAt`, `expiresAt`, `price`. Complete publication and placement durable; unique placement ID. |
| `list` | `publisherId`, `entries`, `more`, `price`. Newest first by `(sequence, publicationId)` descending; only readable entries; empty page is a paid success; hidden items do not change the result shape. |
| `get` | Complete signed publication (metadata, key, signature, content) and `price`. Exact stored bytes. |
| `renew` | `placementId`, `previousExpiresAt`, `expiresAt`, `price`. One extension under the expected-expiration guard. |
| `remove` | `placementId`, `removalId`, `removed:true`, `releaseCredits`, `price`; both ledger effects applied once. |
| Remote check | `placementId`, `offset`, `value:bytes[1]`; requester derives the outcome. |
| Local validation | A verified publication (signature, hash, kind rules, manifest or message, decrypted content) or rejection with no usable plaintext; latest-sequence selection and equivocation report across hosts. |

Removal retains exact replay output for the ledger lifetime so neither the
charge nor the release credit applies twice. Renew and remove serialize per
placement; a get accepted while pending completes.

## Independent acceptance examples

- Store a public page and resource, restart the host, and read both back with
  identical bytes; the reader verifies the signature without trusting the host.
- A reader outside a restricted audience lists and gets nothing, with the same
  response shape as for a missing item.
- Repeat removal after a lost reply: one remove charge and one release credit.
