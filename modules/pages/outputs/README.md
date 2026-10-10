# Static Pages outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Local publication result | Administrator: resource version/snapshot reference becomes available as a complete self-consistent object. References are local implementation details, not new wire fields. |
| Get result | [Services](../../services/inputs/README.md), then visitor: `path:string`, `mediaType:string`, `contentSize:uint64`, `contentHash:bytes[32]`, `content:bytes`, `price:uint64`. |
| Structured failure | Services/visitor: invalid or unavailable resource, bounds, authority or snapshot failure. No successful fallback page. |
| Local check | Visitor: pass/fail/inconclusive with original request and complete result; no remote check call or separate charge. |

Path equals requested path byte for byte; size equals complete returned bytes;
hash is SHA-256 of exactly those bytes; media type is valid; price equals the
accepted fixed price. Results come from one snapshot, even across concurrent
publication. Services handles Ledger and Peer Control through their contracts.
Interrupted output is not a successful result; uncertain committed state follows
the common local recovery rules. A repeated get is a new paid invocation and
can return newer content.

Publisher provenance comes from the authenticated connection. Pages adds no
resource signature, and copied output is not transferable proof of publisher
authorship. A successful local check establishes consistency with the request,
not safe HTML or permission to execute scripts/fetch links. Each asset is paid
separately under the visitor's authority.

## Independent acceptance examples

- Replace a resource during a fake streamed read: output size, hash and content
  all describe the pinned original snapshot.
- Request a missing path or invalid traversal form: fail without serving root
  or touching an unauthorized local path.
- Verify a bounded root/asset retrieval with only Services, crypto and content
  substitutes; no Discovery, File Sharing or server-side runtime is needed.
