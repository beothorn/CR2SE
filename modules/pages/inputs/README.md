# Static Pages inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Optional; wire service `cr2se.page` version 1. Pages owns the publisher's resource
map and consistent content snapshots. It consumes
[Services context](../../services/outputs/README.md), authenticated publisher
identity from Peer Control, [Cryptography hashing](../../cryptography/outputs/README.md)
and a local content/snapshot port. No File Sharing, Storage, Computation or
Discovery runtime is required. A known publisher contact is sufficient.

## Accepted operations

| Input / source | Values and expectations |
|---|---|
| Publish/replace/remove resource / authorized local administrator | Canonical path, validated media type and immutable complete content. Maintain the specified HTML root and offering limits; no peer publication command is introduced. |
| Get / Services | `path:string`, `maximumBytes:uint64`, plus invocation context and accepted fixed price. There is no `operation` field in this service's get input. |
| Snapshot / local content adapter | One resource's path, media type, size/hash and immutable bytes or scoped reference. Pin this snapshot through complete transfer even if publication changes. |
| Local verification / visitor | Original requested path/byte limit, accepted offering/price and complete returned metadata/content, attributed to authenticated publisher. |

Validate canonical paths, UTF-8 byte lengths, media syntax, local path authority
and offering `maximumPathBytes`/`maximumResourceBytes`. Caller `maximumBytes`
must not exceed the offering limit, and content must fit both bounds. A path is
a logical resource name, not permission to read an arbitrary host file.

Missing/oversized/invalid resources fail without substituting an HTML error
document or another path. Input validation and snapshot acquisition precede
successful work. Assets and linked pages require separate authorized invocations
with their own prices; returned HTML cannot grant additional spending authority.
