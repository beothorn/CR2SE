# Transport inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Required in the minimum node. Transport can be tested with byte-stream sockets,
Identity/Cryptography substitutes and a protocol consumer; no service handler,
Board, Ledger, Node API or Discovery process is required.

## Accepted calls and events

| Input / source | Values and expectations |
|---|---|
| Connect/listen/accept / authorized local connection control and platform TCP | Valid endpoint or accepted socket, local identity capability, optional expected peer ID, handshake deadline and resource limits. Known contacts must supply the expected ID. |
| Identity credential/signing result / [Identity](../../identity/outputs/README.md) | Valid public ID/key and fresh signature over Transport's exact transcript. No reusable ID-only proof. |
| Primitive results / [Cryptography](../../cryptography/outputs/README.md) | Fresh ephemeral X25519, random challenge, exact transcript derivations and frame MACs under the Transport construction. |
| Socket bytes / platform | Arbitrary partial/coalesced reads, EOF or I/O error. Treat unauthenticated bytes as untrusted and enforce the 65,536-byte frame payload limit before allocation. |
| Open stream / Peer Control or another installed protocol | Authenticated connection handle, protocol ID/version. Transport allocates the next exact parity-correct stream ID. |
| Send data/end/cancel / stream owner | Scoped stream handle, ordered bounded bytes or terminal control. Enforce lifecycle; send queues are finite. |
| Register protocol / composition | Supported protocol ID/version and authorized consumer adapter. This registers a local consumer, not a new wire frame type. |
| Ping/drain/close / local controller | Connection handle, matching ping data and deadlines. Drain obeys GOAWAY; cancellation does not undo service effects. |

Transport owns sockets, stream counters and session secrets. Inject monotonic
timers and bounded queues through platform ports. Identity IDs in application
payloads cannot substitute for the authenticated connection identity.
