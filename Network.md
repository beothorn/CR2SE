# CR2SE Network Protocol

CR2SE version 1 is a binary application protocol carried over persistent TCP
connections. A connection is bidirectional and multiplexes independent logical
streams. Both nodes authenticate their CR2SE identities during connection
establishment, and every later frame is protected against modification,
insertion, and replay within that connection.

This document is the authoritative wire contract. The
[CR2SE Glossary](./Glossary.md) defines **node**, **peer**, **connection**,
**initiator**, and **acceptor**. [Identity](./Identity.md) defines CR2SE IDs and
Ed25519 identities. [Encryption](./Encryption.md) defines the cryptographic
primitives used here.

The words **must**, **must not**, **should**, and **may** are normative.

---

## 1. Layering and roles

TCP provides one reliable, ordered byte stream. It does not preserve write or
message boundaries. A CR2SE implementation must therefore read and write the
exact byte counts specified below and must handle partial socket operations.

The node that opens TCP is the **initiator**. The node that accepts TCP is the
**acceptor**. These roles determine handshake transcript ordering and stream-ID
parity only. After authentication, either node may open streams and request
services.

The protocol layers are:

```text
application protocols and services
              |
bidirectional CR2SE streams
              |
CR2SE frames + connection integrity tag
              |
             TCP
```

Connection integrity does not provide confidentiality. Frame headers and
payloads remain visible. An application may encrypt its payload as specified in
`Encryption.md`.

---

## 2. Integer and text encoding

All multi-byte integers are unsigned and encoded in network byte order
(big-endian). Integer ranges are inclusive.

Lengths always count bytes, not characters. Unless a field says otherwise,
text is valid UTF-8 without a byte-order mark. A receiver must reject invalid
UTF-8 in a field declared as text. Diagnostic text is not protocol state and
must not be parsed to determine behavior.

---

## 3. Frame format

Every frame starts with this 12-byte header:

| Offset | Size | Field |
|---:|---:|---|
| 0 | 1 byte | Version |
| 1 | 1 byte | Type |
| 2 | 2 bytes | Flags |
| 4 | 4 bytes | Stream ID |
| 8 | 4 bytes | Payload Length |
| 12 | N bytes | Payload |
| 12 + N | 16 bytes after authentication only | Integrity Tag |

Before authentication completes, only handshake frames are permitted and the
frame size is:

```text
12 + Payload Length
```

After authentication completes, every frame includes a 16-byte connection
integrity tag and the frame size is:

```text
12 + Payload Length + 16
```

`Payload Length` does not include the header or integrity tag.

The fields have these version 1 requirements:

- `Version` must be `0x01`.
- `Flags` must be zero. A nonzero value is a connection error.
- `Payload Length` must be at most 65,536 bytes.
- `Stream ID` and `Type` must obey the registry and state rules below.

The 64 KiB payload limit applies to every frame, including implementations
configured to tolerate more. A conforming sender must not send a larger frame,
and a conforming receiver must support the full 65,536-byte limit. Large values
are divided among `DATA` frames. At the maximum size, the 12-byte header adds
approximately 0.018% overhead, or approximately 0.043% together with the
mandatory 16-byte integrity tag. Bounded frames also improve multiplexing
fairness and limit per-frame memory exposure.

An implementation must validate the header and payload length before allocating
or reading a payload buffer. It must use checked arithmetic when calculating a
total frame size.

---

## 4. Version 1 frame type registry

Unassigned type values are invalid in version 1. Application extensions do not
allocate frame types; they use a namespaced protocol identifier in `OPEN`.

| Value | Name | Stream ID | Payload |
|---:|---|---|---|
| `0x01` | `HELLO` | 0 | exactly 100 bytes |
| `0x02` | `AUTH` | 0 | exactly 64 bytes |
| `0x03` | `PING` | 0 | exactly 8 bytes |
| `0x04` | `PONG` | 0 | exactly 8 bytes |
| `0x05` | `GOAWAY` | 0 | connection shutdown payload |
| `0x06` | `ERROR` | 0 or a known nonzero stream | error payload |
| `0x10` | `OPEN` | nonzero | stream opening payload |
| `0x11` | `DATA` | nonzero | 1 through 65,536 opaque bytes |
| `0x12` | `END` | nonzero | empty |
| `0x13` | `CANCEL` | nonzero | error payload |

Values `0x00`, `0x07..0x0f`, and `0x14..0xff` are unassigned and invalid.
Future meanings require a future CR2SE network version.

---

## 5. Mandatory authenticated handshake

Both nodes must authenticate before opening application streams. The handshake
uses fresh nonces, ephemeral X25519 keys, and signatures by the nodes' persistent
Ed25519 identity keys.

The handshake provides:

- proof that each peer controls the private key for its advertised CR2SE ID;
- role binding, so an initiator proof cannot be reflected as an acceptor proof;
- freshness through a new random nonce and ephemeral key on every connection;
- session keys bound to both identities, roles, nonces, and ephemeral keys;
- integrity and per-direction replay protection for every later frame.

It does not hide frame content.

### 5.1 HELLO payload

Each node's first transmitted frame must be `HELLO`. Its payload is exactly:

| Offset | Size | Field | Version 1 value |
|---:|---:|---|---|
| 0 | 1 | Handshake Version | `0x01` |
| 1 | 1 | Identity Version | `0x01` |
| 2 | 1 | Identity Key Algorithm | `0x01` (Ed25519) |
| 3 | 32 | Ed25519 Public Key | sender's identity public key |
| 35 | 1 | Key Agreement Algorithm | `0x01` (X25519) |
| 36 | 32 | Ephemeral X25519 Public Key | new for this connection |
| 68 | 32 | Nonce | CSPRNG output, new for this connection |

The sender must generate a fresh ephemeral X25519 key pair and a fresh 32-byte
nonce for every TCP connection. The ephemeral private key must not be reused and
must be erased when no longer needed.

The receiver derives the advertised CR2SE ID from the Ed25519 public key using
`Identity.md`. If it connected expecting a particular identity, the derived ID
must equal that expected ID. A mismatch is authentication failure.

The remote ID may equal the local ID because several nodes may legitimately
operate as one CR2SE identity. An implementation must not reject such a
connection solely because the IDs match; TCP roles still keep the transcript
and directional keys distinct.

### 5.2 Transcript and AUTH payload

Let `initiatorHello` and `acceptorHello` be the complete HELLO payloads, ordered
by TCP role rather than arrival order. Define:

```text
helloTranscript =
    uint32_be(length(initiatorHello))
    || initiatorHello
    || uint32_be(length(acceptorHello))
    || acceptorHello

authMessage(role) =
    ASCII("CR2SE-NETWORK-AUTH-V1")
    || 0x00
    || role
    || helloTranscript

role = 0x01 for the initiator
role = 0x02 for the acceptor
```

`ASCII(...)` contributes exactly the displayed ASCII bytes without quotes or a
terminating zero. The explicit `0x00` is a domain-separator byte.

After receiving and validating the peer's `HELLO`, each node sends one `AUTH`
frame. Its payload is exactly the 64-byte Ed25519 signature made by the sender's
identity key over `authMessage(senderRole)`.

The receiver verifies the signature with the Ed25519 public key in the peer's
`HELLO`. Invalid signatures, duplicate `HELLO` or `AUTH` frames, an `AUTH` before
the peer's `HELLO`, and non-handshake frames before authentication are
connection errors.

HELLO and AUTH frames do not have integrity tags. Each direction becomes tagged
immediately after the `AUTH` frame in that direction. Because TCP preserves
order, a receiver verifies that `AUTH` before interpreting the next frame from
the same peer.

A node must not send any frame other than `HELLO`, `AUTH`, or a best-effort
connection `ERROR` until it has received and verified the peer's `AUTH`.

### 5.3 Session key derivation

After the peer's `AUTH` verifies, each node calculates the X25519 shared secret
using its ephemeral private key and the peer's ephemeral public key. It must
reject an all-zero shared secret.

Define:

```text
salt = SHA-256(
    ASCII("CR2SE-NETWORK-KEYS-V1")
    || 0x00
    || helloTranscript
)

prk = HKDF-Extract-SHA-256(salt, x25519SharedSecret)

initiatorToAcceptorKey = HKDF-Expand-SHA-256(
    prk, ASCII("CR2SE-NETWORK-V1-I2A-KEY"), 32)

acceptorToInitiatorKey = HKDF-Expand-SHA-256(
    prk, ASCII("CR2SE-NETWORK-V1-A2I-KEY"), 32)

initiatorToAcceptorNoncePrefix = HKDF-Expand-SHA-256(
    prk, ASCII("CR2SE-NETWORK-V1-I2A-NONCE"), 16)

acceptorToInitiatorNoncePrefix = HKDF-Expand-SHA-256(
    prk, ASCII("CR2SE-NETWORK-V1-A2I-NONCE"), 16)
```

The initiator uses the I2A key and prefix to send and the A2I values to receive.
The acceptor uses them in the opposite directions.

### 5.4 Post-handshake integrity tag

Each direction maintains an independent unsigned 64-bit sequence number. The
first frame after that direction's `AUTH` uses sequence `0`; each later frame
uses the next integer. Sequence numbers are implicit and are not transmitted.

For a protected frame:

```text
nonce = directionNoncePrefix || uint64_be(sequence)
authenticatedData = exact12ByteHeader || payload

integrityTag = XChaCha20-Poly1305(
    key = directionKey,
    nonce = nonce,
    plaintext = empty,
    authenticatedData = authenticatedData
)
```

With empty plaintext, the XChaCha20-Poly1305 result is exactly its 16-byte
authentication tag. The payload is authenticated data and remains plaintext.
The sender appends this tag after the payload.

The receiver reconstructs the nonce from its expected sequence number and must
authenticate the header and payload before dispatching the frame. It must not
dispatch, log as trusted, or otherwise act on an unauthenticated payload. A tag
failure requires immediate TCP termination without sending an error frame.

The sequence advances only after successful authentication of a complete frame.
A connection must close before either direction would wrap its sequence number.
Keys and nonce prefixes belong to one connection and must never be reused on
another connection.

---

## 6. Stream IDs

Stream ID `0` is reserved for connection-level frames.

The initiator creates streams with odd IDs beginning at `1`. The acceptor
creates streams with even IDs beginning at `2`. Each endpoint allocates its own
IDs sequentially, increasing by exactly two. Gaps and reuse are forbidden on
the same TCP connection.

A received `OPEN` must contain exactly the next expected ID for the remote
peer. Wrong parity, a gap, reuse, or a non-increasing ID is a connection error.

When the next local ID cannot fit in `uint32`, the node sends `GOAWAY` with
`ID_EXHAUSTED`, drains active streams, closes TCP, and opens a new connection if
needed.

---

## 7. Opening and identifying a stream

`OPEN` creates one bidirectional stream. Its payload is:

```text
uint16_be(protocolIdLength)
protocolId                         protocolIdLength bytes
uint32_be(protocolVersion)
```

Requirements are:

- `protocolIdLength` is `1..255`.
- `protocolId` is lowercase ASCII matching
  `[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?`.
- Adjacent dots, a leading dot, and a trailing dot are invalid.
- `protocolVersion` is `1..2^32-1`.
- The payload contains no trailing bytes.

The `cr2se.` prefix is reserved for protocols standardized by CR2SE. Custom
protocols should use a stable reverse-domain prefix controlled by their author,
for example `org.example.thumbnail`.

The receiver processes `OPEN` before later frames on the stream because TCP is
ordered. If it does not support the named protocol and version, it sends a
stream `ERROR` with `UNSUPPORTED_PROTOCOL`. The opener may send `DATA`
immediately without waiting for an acknowledgement; consequently it must be
prepared for that error and stop producing data when it arrives.

Application protocol payloads are arbitrary bytes. Concatenating the payloads
of successive `DATA` frames in one direction produces that direction's logical
byte sequence. Frame boundaries have no application meaning unless the named
application protocol explicitly assigns them meaning.

---

## 8. Stream lifecycle

A new stream begins with both send directions open:

```text
                 OPEN
                  |
          both directions open
             /             \
      local END          remote END
             \             /
       one direction remains open
                  |
           other side END
                  |
             normally closed

At any nonterminal point:
    CANCEL or stream ERROR -> terminal
```

The rules are:

1. Only the stream creator sends `OPEN`.
2. Either peer may send `DATA` while its own send direction is open.
3. `DATA` order within each direction is the TCP/frame order.
4. `END` has no payload and half-closes the sender's direction.
5. A peer must not send `DATA` or another `END` after its own `END`.
6. The stream closes normally only after both directions have received `END`.
7. `CANCEL` terminates both directions immediately. It may be sent while either
   direction remains open.
8. A stream `ERROR` terminates both directions immediately.
9. Closing a stream does not close the TCP connection.

After a stream becomes terminal, both peers must discard later non-`OPEN`
frames carrying that stream ID. This rule accommodates frames already queued
before a `CANCEL` or `ERROR` arrived. An `OPEN` reusing any prior ID remains a
connection error. An implementation may close a connection when a peer keeps
sending excessive data for terminal streams.

A non-`OPEN` frame for an ID that was never created is a connection error.

---

## 9. Multiplexing and backpressure

Frames from different streams may be interleaved. Frame bytes themselves must
never be interleaved: one complete header, payload, and tag is written before
bytes of the next frame.

Implementations should schedule active streams fairly so a large transfer does
not permanently starve small operations. They may combine several complete
frames in one socket write.

Version 1 has no per-stream wire-level flow-control frame. TCP provides
connection-level backpressure. Implementations must use bounded queues and must
not buffer unbounded data for a slow application consumer. They may cancel a
stream whose local resource limit is exceeded.

---

## 10. Connection control

### 10.1 PING and PONG

An authenticated node may send `PING` on stream `0` with any 8-byte token. The
peer must answer with one `PONG` containing the identical token. A `PONG` does
not need to preserve ordering relative to application work beyond normal frame
ordering.

Receipt of an unsolicited or duplicate `PONG` is not a protocol error; it is
ignored. Timeout selection and the number of outstanding pings are local policy.

### 10.2 GOAWAY

`GOAWAY` begins graceful connection shutdown. Its payload is:

```text
uint32_be(lastAcceptedRemoteStreamId)
uint16_be(errorCode)
uint16_be(reasonLength)
reason                           reasonLength UTF-8 bytes
```

`reasonLength` is `0..1024`, and there must be no trailing bytes.
`lastAcceptedRemoteStreamId` is the greatest stream ID opened by the receiver
of `GOAWAY` that the sender accepted, or zero if none.

The value must be zero or have the receiver's local stream parity, and it must
not exceed the greatest stream ID the receiver actually opened. A repeated
`GOAWAY` may reduce this value but must not increase it.

After sending or receiving `GOAWAY`, a node must not create new streams on that
connection. Streams at or below the reported ID may finish. Locally created
streams above the reported ID are treated as refused. If a peer opens a stream
after `GOAWAY`, the receiver sends `REFUSED_STREAM` for that stream and otherwise
continues draining.

A node receiving `GOAWAY` should send its own `GOAWAY` if it has not already
done so. Once no accepted streams remain active, either node may close TCP.

---

## 11. Error and cancellation payloads

`ERROR` and `CANCEL` use:

```text
uint16_be(errorCode)
uint16_be(reasonLength)
reason                           reasonLength UTF-8 bytes
```

`reasonLength` is `0..1024`; no trailing bytes are permitted. The reason is
optional diagnostic text and must not contain secrets or be used as a
machine-readable decision value.

Version 1 codes are:

| Value | Name | Meaning |
|---:|---|---|
| `0x0000` | `NO_ERROR` | graceful `GOAWAY` only |
| `0x0001` | `PROTOCOL_ERROR` | malformed or forbidden protocol behavior |
| `0x0002` | `AUTHENTICATION_FAILED` | identity or handshake verification failed |
| `0x0003` | `FRAME_SIZE_ERROR` | payload exceeds the version 1 limit |
| `0x0004` | `UNSUPPORTED_PROTOCOL` | `OPEN` protocol ID/version is unsupported |
| `0x0005` | `STREAM_STATE_ERROR` | invalid transition on an existing stream |
| `0x0006` | `REFUSED_STREAM` | stream was not accepted, including after `GOAWAY` |
| `0x0007` | `INTERNAL_ERROR` | implementation failed while handling the connection |
| `0x0008` | `ID_EXHAUSTED` | no local stream IDs remain |
| `0x0009` | `CANCELLED` | operation was intentionally cancelled |
| `0x000a` | `RESOURCE_LIMIT` | bounded local resource limit was reached |

`NO_ERROR` is invalid in `ERROR` or `CANCEL`. `CANCEL` normally uses
`CANCELLED`, but may use `RESOURCE_LIMIT` or `INTERNAL_ERROR` when applicable.
Application-specific failures belong to the application byte protocol, not this
registry.

An unregistered error code or a code used where this section forbids it is a
malformed payload and therefore a connection error.

An `ERROR` on stream `0` is a connection error: the sender closes TCP after a
best-effort complete write. An `ERROR` on a known nonzero stream terminates
only that stream.

---

## 12. Required error handling

The following require immediate TCP termination:

- unsupported `Version`;
- nonzero flags;
- unknown frame type;
- payload length above 65,536;
- invalid frame type/stream-ID combination;
- malformed connection-control or handshake payload;
- invalid handshake order, value, signature, or expected identity;
- wrong-parity, skipped, reused, or out-of-order stream ID;
- a frame for a stream that never existed;
- failed integrity-tag verification;
- truncated header, payload, or integrity tag;
- sequence-number exhaustion.

If framing is trustworthy and the direction's integrity state is known, the
node should send an appropriate connection `ERROR` before closing. It must close
without an error when the version is unsupported, the integrity tag fails, or
safe encoding of a response is uncertain.

Invalid `DATA`, `END`, or application sequencing on an existing active stream
causes a stream `ERROR` with `STREAM_STATE_ERROR`; other streams remain usable.
A malformed `OPEN` payload causes a stream `ERROR` with `PROTOCOL_ERROR` after
its stream ID has passed the parity and exact-sequence checks. The rejected ID
is consumed and cannot be reused.

TCP ending immediately terminates every active stream. A stream that had not
already received `END` in both directions reports transport failure, not normal
completion. EOF in the middle of a frame is always truncation.

Once a header is rejected, the implementation must not scan subsequent bytes
for a possible frame boundary. It closes the connection, preventing loss of
synchronization.

---

## 13. Resource and concurrency requirements

Implementations must:

- cap concurrent connections, active streams, queued outbound bytes, and
  per-stream buffered bytes according to local policy;
- enforce the frame limit before allocation;
- process payloads incrementally at the application layer when logical values
  are large;
- serialize writers so bytes from different frames cannot mix;
- treat all peer-provided diagnostic text, protocol IDs, and payloads as
  untrusted input;
- impose a handshake timeout and may impose idle or ping timeouts;
- erase ephemeral private keys and derived session keys when the connection
  ends;
- never treat a frame as belonging to the authenticated peer until its tag has
  verified.

A local resource limit should cancel only the affected stream when safe. A node
may use `GOAWAY` or close TCP when connection-wide limits or repeated abuse make
continued processing unsafe.

---

## 14. Version 1 compliance summary

A compliant implementation:

```text
uses TCP;
reads and writes exact frame byte counts;
encodes integers big-endian;
uses the fixed 12-byte header;
limits payloads to 65,536 bytes;
performs the mandatory mutual identity handshake;
authenticates every post-handshake frame with its implicit sequence number;
uses odd initiator and even acceptor stream IDs in increasing order;
supports bidirectional, half-closed streams;
supports all registered version 1 frame types and error behavior;
does not assign custom frame types;
uses OPEN protocol identifiers for standard and extension protocols;
does not reuse stream IDs, session keys, nonces, or sequence numbers;
and treats premature TCP termination as failure for unfinished streams.
```

The corresponding implementation-neutral algorithms are in
[`pseudoCode/Network.md`](./pseudoCode/Network.md). Deterministic cryptographic
interoperability values are in
[`pseudoCode/NetworkTestVectors.md`](./pseudoCode/NetworkTestVectors.md).
