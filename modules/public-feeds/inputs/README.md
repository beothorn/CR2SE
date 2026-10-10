# Public Feeds inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Optional; wire service `cr2se.open-social-messaging` version 1. It owns the local
publisher's immutable signed messages. Dependencies are
[Services](../../services/outputs/README.md), [Identity](../../identity/outputs/README.md),
[Cryptography](../../cryptography/outputs/README.md), durable feed persistence,
clock and randomness. Messaging, File Sharing, Storage and Discovery runtimes
are not required. Attachments are embedded service data, not implicit downloads
from another family.

## Accepted operations

| Input / source | Values and expectations |
|---|---|
| Publish / authorized local application | UTF-8 body and bounded attachment metadata/bytes; local publisher identity and permitted time. Generate message ID, exact canonical bytes, hashes and signature before durable publication. |
| Import signed message / local application | Complete canonical message/attachment values and signature; validate as a reader and require ownership consistent with this publisher's feed. |
| `read` / Services | `operation:"read"`, `selector`, optional time/cursor fields, `limit:uint32`; authenticated reader, accepted price and offering limits. |
| Local check / requester | Requested publisher, original read input, accepted offering and complete response. All signatures, hashes, sizes, ordering and limits are checked before treating messages as authentic. |
| Aggregate / requester application | Independently verified feeds and local following/deduplication policy. No global broadcast or authority to spend beyond approved read budgets. |

`selector` is `latest`, `since` or `interval`. Latest forbids both time bounds;
since requires `fromInclusive:uint64` only; interval requires `fromInclusive`
and `toExclusive:uint64` with the specified valid range. Cursor fields
`beforePublishedAt:uint64` and `beforeMessageId:bytes[32]` are both present or
absent and form an exclusive cursor in newest-first ordering. Enforce current
result and canonical response-byte limits.

Publication is local administration, not a peer operation. A returned string,
attachment, HTML or model-generated description cannot authorize publication,
signing, execution or more paid calls. Known publisher contacts suffice; optional
Discovery lookup is an application composition choice.
