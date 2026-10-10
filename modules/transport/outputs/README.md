# Transport outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Authenticated connection | [Peer Control](../../peer-protocol/inputs/README.md) and local connection client, optionally [Node API](../../node-api/inputs/README.md): local/remote IDs, unique connection instance, scoped handle and state. Emit only after complete successful handshake and expected-ID match. |
| Stream opened | Registered protocol consumer: connection context, stream instance, protocol ID/version and direction state. Unknown protocols receive the specified stream error. |
| Data / half-close / terminal event | Stream consumer: verified ordered bytes, remote END, normal closure, cancellation or error. DATA frame boundaries do not delimit application values. |
| Outbound wire bytes | TCP adapter: exact full header/payload/tag records serialized without interleaving writers. |
| Ping / shutdown result | Authorized local controller: correlated reachability or timeout and drain/close outcome. A queued write is not a remote service acknowledgement. |
| Transport failure | Every affected consumer: connection/stream identity and machine-readable scope/code. Authentication/tag/framing failures close the connection; isolated stream failures preserve other usable streams. |

No payload reaches an authenticated consumer before its integrity tag verifies.
Normal stream completion requires END in both directions. TCP loss before that
is a failure, even if all expected-looking application bytes arrived. Peer
Control decides whether an invocation is outcome unknown. Transport never
settles credits or retries an application operation.

Queue saturation propagates backpressure or the specified resource failure,
not unbounded memory use. Closing erases session secrets; handles and counters
are not reused across connection instances, including after process restart.

## Independent acceptance examples

- Run the existing handshake/frame vectors through fragmented and coalesced
  fake sockets; both parties open streams over one authenticated connection.
- Reject a tag mutation or wrong expected ID without emitting application data.
- Test exact stream parity/sequence, half-close, cancellation, EOF and a slow
  consumer using a protocol stub; no Ledger or service implementation is needed.
