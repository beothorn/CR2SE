# Node API

The Node API lets an application control its local node. It is not the peer wire
protocol. Libraries may expose embedded calls; standalone nodes expose the
portable loopback interface below. Both have the same logical behavior.

See [pseudocode](./pseudocode/README.md), [diagrams](./diagrams/README.md), and
[Peer Protocol](../peer-protocol/README.md) for remote exchanges.

## Connection, authentication, and version

Bind TCP only to an explicitly configured loopback address (`127.0.0.1` or `::1`).
There is no mandatory port; each node instance publishes its endpoint through
local configuration. A non-loopback administrative endpoint is outside this
binding and must not be enabled by default.

Each authorized client receives an independent random 32-byte capability token
through an OS-protected local configuration or secret store. Encode it as padded
Base64. Do not transmit it to peers or expose it in page content or logs.
Loopback itself does not authorize a caller. Match tokens in constant time and
rate-limit failed attempts. The first request must be:

```json
{"id":"1","operation":"session.open","version":1,"token":"<base64-token>"}
```

Respond with `version:1`, `maximum_message_bytes:1048576`,
`maximum_chunk_bytes:65536`, and `maximum_blob_bytes` as a uint64 decimal string
inside `result`. Default blob limit is 67,108,864 bytes; operators may configure
it. Require at least 65,536 bytes. A client must respect the reported limit.
Unsupported versions return `unsupported_version` and close. Invalid tokens
return a generic `not_authorized` and close without revealing node details.
Before successful session opening, no other operation is allowed.

Embedded libraries enforce the hosting application's authority instead of
requiring a loopback token. Hosting and provider configuration remain local
administrative responsibilities; peer text cannot change them.

## Framing and responses

Every message is one UTF-8 JSON object followed by LF (`0x0a`). Literal newlines
inside a message are forbidden; escape them in strings. A read may contain part
of a message or several messages. Enforce the 1,048,576-byte message limit,
excluding LF, before buffering more input. Depth is limited to 32.

Reject invalid UTF-8, duplicate object members, invalid JSON, and messages over
the limit. Framing/parse failures close the session; do not try to recover an
untrusted request ID. Complete valid requests have a nonempty string `id` of
at most 128 UTF-8 bytes and a nonempty `operation` string.

Request IDs are unique among in-flight requests on a session. A duplicate active
ID closes the session because a second response could not be correlated safely.
Responses may finish out of order, and exactly one terminal response is emitted
per accepted request while the session remains connected:

```json
{"id":"2","ok":true,"result":{}}
```

```json
{"id":"2","ok":false,"error":{"code":"not_available","message":"Unavailable"}}
```

Unknown operations return `unknown_operation`; unknown optional request fields
may be ignored. Unknown mandatory semantics require a new API version. Unknown
response fields may be ignored. Diagnostic strings never determine behavior.

## Values and blobs

Small arguments and results use the schema-based value encoding from Peer
Protocol: 64-bit integers are decimal strings, floats are bit-pattern objects,
and bytes are Base64 objects. Boards and definitions remain lossless JSON
documents with exact numeric fields. Do not round their uint64 values.

Large local values use session-owned opaque blob handles instead of detached
peer body IDs:

```json
{"$blob":"<handle>","length":"1000000"}
```

Use `$textBlob` for a UTF-8 string. A blob handle refers to local temporary
storage, never an arbitrary filesystem path. The node maps it to the peer body's
descriptor when invoking a service. Small byte values may remain inline.

| Operation | Request fields | Result |
|---|---|---|
| `blob.create` | `length` uint64 | `blob_id` |
| `blob.write` | `blob_id`, `offset` uint64, `data` padded Base64 | `written` uint32 |
| `blob.finish` | `blob_id` | `length` uint64 |
| `blob.read` | `blob_id`, `offset` uint64, `length` uint32 | `data` padded Base64, `eof` boolean |
| `blob.close` | `blob_id` | Empty object |

Writes are sequential, start at zero, and contain `1..65536` decoded bytes.
Reject gaps, overlap, and bytes beyond the declared size without changing the
blob. Finish succeeds only at the exact declared length, then makes it immutable.
Only finished blobs may be invoked or read. Read length is `1..65536`; require
`offset <= size`, return up to the requested count, and set eof when the returned
range reaches size. Reading at size returns empty data and eof. Empty blobs can
be finished immediately. Never expose another session's handle.

Large results become finished read-only blobs. Validate a full successful peer
result before publishing its handles. Quotas include all input, output, and
temporary bytes. Keep invocation inputs pinned until its terminal outcome.
Closing a pinned blob fails with `conflict`. Close all handles when the session
ends; unfinished temporary data is discarded. Applications needing recovery
copy successful outputs to their own durable storage before closing.

## Operations

Unless stated otherwise, all IDs and names below are strings, uint64 fields
are decimal strings, and ports/versions/limits are exact JSON uint32 numbers.
Handles are opaque and session-scoped, with no prescribed display length.

| Operation | Required fields | Result |
|---|---|---|
| `connection.open` | `address`, `port`; optional `expected_peer_id` | `connection_id`, authenticated `peer_id` |
| `connections.list` | None | `connections` array |
| `connection.close` | `connection_id` | Empty object |
| `connection.ping` | `connection_id` | `reachable` boolean |
| `board.get` | `connection_id` | `board` |
| `service.get` | `connection_id`, `offering_id` | `service_definition` |
| `service.invoke` | Invocation fields below | `service_result`, `final_price` |
| `service.check` | Same selection fields, `arguments`, `maximum_price`, `credit_issuer` | `check_result`, `final_price` |
| `service.offer` | `connection_id`, `offering_id`, `service`, `service_version`, `credit_issuer`, `maximum_resource_price` | `service_result`, `final_price` |
| `request.cancel` | `request_id` of an active request | `cancel_requested` boolean |
| `ledger.balance` | `connection_id` to issuer | `balance` uint64 |
| `ledger.transfer` | `connection_id`, `order`, `owner_public_key`, `signature`, `maximum_fee` | Peer transfer result |
| `ledger.transfer.get` | `connection_id`, `owner_id`, `transfer_id` | Peer transfer result |
| `ledger.claim.redeem` | `connection_id`, `envelope` | `claim_id`, `amount` |

Connection addresses may be IP literals or the canonical DNS names accepted by
Discovery. Validate ports `1..65535`. Set `expected_peer_id` when using a known
contact or signed address record. Reject mismatching authenticated identities.
Discovery of an endpoint never authorizes access to arbitrary private network
addresses; applications apply their local connection policy.

Each listed connection includes `connection_id`, `peer_id`, `address`, `port`,
and `state:"connected"`. Only the session's accessible connections are returned.
Close requests begin graceful Transport shutdown; remaining work may complete
or be cancelled at the configured deadline. Ping returns false on timeout or
connection loss, and never treats unrelated PONGs as success.

## Invocation and spending authority

```json
{
  "id":"6",
  "operation":"service.invoke",
  "connection_id":"peer-handle",
  "offering_id":"weather-current",
  "service":"example.weather.current",
  "service_version":1,
  "credit_issuer":"cr2se:3FEKTKCHTGJQLPTATWZZ3HFFBN6JGGCOYNV56CAPN5DECXQZSJOQ",
  "maximum_price":"5",
  "arguments":{"location":"Berlin"}
}
```

The issuer and spending bound are mandatory. Validate the selected definition
and quote against the caller's authority before accepting it. `maximum_price`
is a maximum debit, not permission to silently change issuer or contract. A
node may impose stricter per-client budgets. Computation uses this as its
maximum metered authorization. The response's `final_price` is uint64.

For third-party credits, the bound includes the agreed issuer transfer fee.
The node obtains that fee, generates a fresh transfer ID, and follows Peer
Protocol's single-invocation payment binding. Return `transfer_fee` as an
additional uint64 result field. If the issuer has not confirmed payment, report
`settlement_state:"unsettled"`; otherwise use `settlement_state:"settled"`.
The service output and payment state are separate. The node must not silently
repeat the work to resolve a payment problem.

`service.offer` fulfills a remote wanted offering using a provider implementation
already installed and authorized locally. `maximum_resource_price` caps the
quoted operation size in the offering's credit units; local runtime, storage,
and concurrency limits apply independently. Never compile or install a provider
from peer descriptions automatically. Return `unsupported` if no local handler
matches. A wanted publisher supplies its input through its configured local
application, not through an unsolicited peer command.

`service.check` uses remote check input schemas only where the contract defines
a remote check. The node returns locally computed `check_result`. It must have
the original expected evidence in its local invocation context; otherwise the
outcome is inconclusive. Local-only checks can be performed by libraries without
an IPC call. Discovery included checks permit `maximum_price:"0"`.

Ledger order, keys, signatures, transfer IDs, and redemption envelopes are
padded Base64 strings with the exact lengths/formats specified by Ledger and
Peer Protocol. Protect redemption material in the local client too.

## Cancellation, errors, and lifecycle

Cancellation requests stop pending work when possible and send Transport CANCEL
for an active exchange. `cancel_requested:true` does not promise rollback.
The original request still gets its own terminal response. Use `cancelled` if
no accepted effects are possible, and `outcome_unknown` if commitment is uncertain.
Do not automatically retry either side effects or unsettled payments.

Use peer failure codes where applicable, plus `unknown_operation`,
`unsupported_version`, `invalid_handle`, `cancelled`, and `outcome_unknown`.
Blob quota violations return `resource_limit`. Do not reveal keys, tokens,
other clients' data, or raw unsafe diagnostics in errors.

Optional progress events have `event:"progress"`, `request_id`, `phase`, and
uint64 `completed_bytes`; they have no `id` or `ok`. They are not terminal
responses. Clients may ignore them. Progress never implies successful payment.

On session loss, cancel uncommitted session work, discard temporary blobs, and
keep durable service/ledger commitments. Do not destroy the node's identity or
accepted provider obligations. On node shutdown, stop accepting work, journal
outstanding state, close connections, and flush durable state.
