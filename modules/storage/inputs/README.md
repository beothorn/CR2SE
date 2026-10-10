# Storage inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Required in the minimum node. Storage owns immutable byte leases, not the local
database used by other modules. Its provider needs durable byte/metadata ports,
clock/randomness and [Cryptography](../../cryptography/outputs/README.md) hashing.
[Services](../../services/outputs/README.md) supplies authenticated invocation
context, current accepted terms, reservation and commit coordination. No Node
API, Discovery or other family is required.

## Operations received from Services

The following are logical fields; integers are exact declared widths and IDs/
hashes are 32 bytes. `operation` selects store/retrieve/renew/remove. Remote
checks use `mode:"check"` and the check schema, not an invoke discriminator.

| Operation | Input | Expectations before successful execution |
|---|---|---|
| `store` | `sizeBytes:uint64`, `retentionSeconds:uint64`, `contentHash:bytes`, `data:bytes` | Positive size within offering; bounded retention; exact byte length and SHA-256 match. Metadata is assessed before the upload body. |
| `retrieve` | `leaseId:bytes`, `offset:uint64`, `length:uint64` | Authenticated lease owner, active lease at timely acceptance; positive length within current limits and `length <= sizeBytes - offset` with `offset < sizeBytes`. |
| `renew` | `leaseId`, `expectedExpiresAt:uint64`, `additionalSeconds:uint64` | Owner, active lease, exact current expiration, duration/total-retention limits and checked addition. Serialize against concurrent renew/remove. |
| `remove` | `leaseId` | Owner and active lease. No implied refund or secure physical erasure. |
| Remote check | `leaseId`, `offset:uint64` | Owner, active lease, valid offset, accepted current `checkPrice` and check timing/frequency limits. The expected byte stays with the requester. |
| Local verification | Original request/terms, complete output, original hash/expected byte and timing | Check expectations come from requester-owned evidence, not a provider's claimed outcome. |

Authority derives from invocation context; knowing a lease ID is insufficient.
Unknown/unauthorized leases must not disclose size, hash, expiration or state.
No fields from another operation are accepted when the service forbids them.

Quote assessment supplies retained `sizeBytes` for renewal pricing. Each later
operation uses current offered terms, while existing lease commitments remain
unchanged. Full-input validation and durable acceptance occur after quote
acceptance; reserving payment does not itself create a lease.

The provider implements common prepare/commit/abort/status ports for staged
lease changes and retained results. Encryption is a requester choice: the
provider sees opaque bytes and never needs the requester's decryption key.
The requester keeps its own provider contacts and recovery catalog.
