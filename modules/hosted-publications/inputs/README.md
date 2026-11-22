# Hosted Publications inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Optional. Hosted Publications owns placements and removal replay results. It
consumes [Services context](../../services/outputs/README.md),
[Identity authority](../../identity/outputs/README.md),
[Cryptography primitives](../../cryptography/outputs/README.md), durable
byte/metadata ports, clock and randomness. Its storage is not the paid Storage
service; neither that service, Messaging nor Discovery is a handler dependency.

## Operations received from Services

Invocation inputs carry the matching `operation`. IDs and hashes are 32 bytes,
public keys 32, signatures 64; times, sizes, offsets and credits are uint64,
limits uint32, kinds and visibilities strings.

| Operation | Fields beyond `operation` | Input expectations |
|---|---|---|
| `store` | `publicationId`, `publisherId`, `kind`, `sequence`, `publishedAt`, `visibility`, `audience`, `contentSize`, `contentHash`, `publisherPublicKey`, `publisherSignature`, `retentionSeconds`, `content` | Authenticated publisher equals derived publisher ID; exact signature over the signing bytes; resource sequence zero; public has empty audience, restricted a sorted unique audience within limits and a matching envelope entry count; no pending duplicate ID or conflicting sequence. |
| `list` | `publisherId`, `kind`, optional paired `beforeSequence`/`beforePublicationId`, `limit` | Any authenticated reader; kind is page or feed-post; exclusive pair cursor; readable-only filtering. |
| `get` | `publisherId`, `publicationId`, `maximumBytes` | Any authenticated reader permitted by visibility; content within the bound. |
| `renew` | `placementId`, `expectedExpiresAt`, `additionalSeconds` | Publisher; pending active placement; exact expected expiration and limits. |
| `remove` | `placementId`, `removalId`, `expectedExpiresAt`, `minimumReleaseCredits` | Publisher and pending placement, or exact authorized replay. Quote release credits first, bounded by cumulative store/renew payments. |
| Remote check | `placementId`, `offset` | Publisher, pending active placement, offset below content size. |

Only provider-issued credits are valid terms. Assessment supplies content size
for get/renew pricing and exact release credits for remove. Services coordinates
the remove charge and release-credit adjustment separately in one recoverable
decision. Unknown and unauthorized publications are indistinguishable.

The publisher builds the signed publication, manifest, feed message and
envelope locally (Identity signs, Cryptography encrypts); a host never needs a
reader's private key or the publisher's. Readers consume original signed bytes,
returned content and the expected check byte.
