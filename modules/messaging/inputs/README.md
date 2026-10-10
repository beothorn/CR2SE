# Messaging inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Optional. Messaging owns placements, receipts and replay results. It consumes
[Services context](../../services/outputs/README.md), [Identity authority](../../identity/outputs/README.md),
[Cryptography primitives](../../cryptography/outputs/README.md), durable
byte/metadata ports, clock and randomness. Its storage is not the paid Storage
service; neither that service nor Discovery is a handler runtime dependency.

## Operations received from Services

Invocation inputs carry the matching `operation`; remote check inputs use the
check mode. IDs, hashes and public keys below are 32 bytes, signatures 64 bytes;
times, sizes, offsets and credit amounts are uint64, limits uint32.

| Operation | Fields beyond `operation` | Input expectations |
|---|---|---|
| `store` | `messageId`, `senderId`, `recipientId`, `senderCreatedAt`, `payloadEncoding`, `payloadSize`, `payloadHash`, `senderPublicKey`, `senderSignature`, `retentionSeconds`, `payload` | Authenticated sender equals derived sender ID; valid exact signed metadata, complete size/hash and retention bounds. |
| `discover` | Optional paired `afterAcceptedAt`, `afterPlacementId`; `limit` | Authenticated recipient; exclusive pair cursor and current result bound. No request can select another recipient. |
| `recover` | `placementId`, `messageId`, `payloadHash`, `recoveryId`, `recipientPublicKey`, `recipientSignature` | Authenticated recipient; exact recovery-request signature binds provider, placement, message, hash and recovery ID. Check matching retry before new terms/balance/state. |
| `status` | `placementId` | Authenticated sender; retained pending/recovered evidence before expiration. |
| `renew` | `placementId`, `expectedExpiresAt`, `additionalSeconds` | Sender; pending or recovered, active retention, exact prior expiration and checked duration/total limits. |
| `remove` | `placementId`, `removalId`, `expectedExpiresAt`, `minimumReleaseCredits` | Sender and pending placement, or exact authorized replay. Quote release credits before mutation, bounded by cumulative store/renew payments. |
| Remote check | `placementId`, `offset` | Sender, pending active placement and valid offset; accepted paid check. Expected payload byte remains local to requester. |

Only provider-issued credits are valid Messaging terms. Assessment supplies
`payloadSize` for recover/renew pricing and exact release credits for remove.
Services coordinates the remove charge and release-credit adjustment separately
in one recoverable decision. Unknown/unauthorized placement responses conceal
existence and metadata.

The requester may encrypt using Messaging's specific envelope. The placement
provider validates signed payload metadata without needing recipient private
keys. Discovery of pending messages here is a Messaging operation and does not
require the optional Discovery indexing module. Local verification consumes
original signed metadata, returned payload/receipts and expected byte/timing.
