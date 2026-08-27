# CR2SE Transfer Protocol

CR2SE requires a binary application protocol for persistent, bidirectional communication between peers over TCP.

The [CR2SE Glossary](./Glossary.md) defines the common meaning of **node**, **peer**, **connection**, **initiator**, and **acceptor** used by this specification.

It is designed for applications where two connected peers may independently initiate operations and where multiple operations may be active at the same time over the same connection.

Examples include:

- requesting information from another peer;
- searching for peers or resources;
- transferring small messages;
- transferring large files;
- receiving requests while another request is already being processed.

CR2SE defines the bytes exchanged between peers and their meaning. It is language and platform independent. An implementation may therefore be written in Rust, C, Java, or any other language capable of opening TCP connections and reading and writing bytes.

This document defines the protocol, not a particular implementation.

---

1. Transport

CR2SE uses TCP as its transport protocol.

TCP provides a persistent, reliable, ordered, bidirectional byte stream between two endpoints.

Once a TCP connection has been established, either endpoint can send data. CR2SE therefore does not assign permanent client and server roles to connected peers.

The endpoint that opens the TCP connection is called the initiator.

The endpoint that accepts the TCP connection is called the acceptor.

These terms describe how the connection was established. They do not restrict what either peer may do after the connection is established.

Initiator                            Acceptor
    |                                  |
    | -------- TCP connection -------> |
    |                                  |
    | -------- CR2SE frames ---------> |
    | <------- CR2SE frames ---------- |
    | -------- CR2SE frames ---------> |
    | <------- CR2SE frames ---------- |
    |                                  |

A CR2SE connection is intended to be persistent. Multiple operations should normally reuse an existing connection rather than opening a new TCP connection for every operation.

---

2. TCP Is a Byte Stream

TCP transports an ordered sequence of bytes. It does not preserve application message boundaries.

For example, an implementation may perform two writes:

write("hello")
write("world")

The receiver must not assume that two corresponding reads will return:

read() -> "hello"
read() -> "world"

It could receive:

read() -> "hel"
read() -> "loworld"

or:

read() -> "hellowor"
read() -> "ld"

All of these are valid TCP behavior.

CR2SE therefore needs its own mechanism for determining where one protocol message ends and another begins.

That mechanism is the frame.

---

3. Frames

A frame is the smallest independently encoded unit in CR2SE.

Every frame consists of:

1. a fixed-size header;
2. zero or more payload bytes.

The header describes the frame and specifies the exact size of its payload.

┌─────────────────────────────┐
│ Header                      │
│ fixed size                  │
├─────────────────────────────┤
│ Payload                     │
│ payload_length bytes        │
└─────────────────────────────┘

Because the header has a known size, a receiver can:

1. read the complete header;
2. decode the payload length;
3. read exactly that many payload bytes;
4. process the complete frame;
5. begin reading the next frame.

No delimiter or end marker is required.

Payloads are arbitrary binary data. Their contents do not affect frame boundaries.

---

4. Byte Order

All multi-byte integers in CR2SE use network byte order, also known as big-endian.

For example, the 32-bit integer:

0x12345678

is transmitted as:

12 34 56 78

Implementations must convert between their native integer representation and CR2SE network byte order when necessary.

---

5. Frame Format

Every CR2SE frame begins with the following 12-byte header.

Offset| Size| Field
0| 1 byte| Version
1| 1 byte| Type
2| 2 bytes| Flags
4| 4 bytes| Stream ID
8| 4 bytes| Payload Length
12| N bytes| Payload

Graphically:

byte offset

0        ┌──────────────────────────┐
         │ Version          1 byte  │
1        ├──────────────────────────┤
         │ Type             1 byte  │
2        ├──────────────────────────┤
         │ Flags            2 bytes │
4        ├──────────────────────────┤
         │ Stream ID        4 bytes │
8        ├──────────────────────────┤
         │ Payload Length   4 bytes │
12       ├──────────────────────────┤
         │                          │
         │ Payload                  │
         │                          │
         │ Payload Length bytes     │
         │                          │
         └──────────────────────────┘

The header size is always exactly 12 bytes.

The total frame size is:

12 + Payload Length

bytes.

---

6. Version

"Version" is an unsigned 8-bit integer identifying the CR2SE protocol version used to encode the frame.

This specification defines:

Version = 1

Every frame in CR2SE version 1 must contain:

0x01

in the Version field.

A receiver must not interpret a frame according to version 1 rules if the Version field contains a version it does not support.

How version negotiation and unsupported versions are handled will be defined separately.

---

7. Type

"Type" is an unsigned 8-bit integer identifying the meaning of the frame.

The type determines how the rest of the frame should be interpreted.

CR2SE will reserve part of the type space for protocol-defined frame types while allowing applications and extensions to define custom types.

This allows CR2SE to provide common behavior without requiring every application protocol to become part of the CR2SE specification.

TODO: Type Registry

Define:

- the standard CR2SE frame types;
- the numeric range reserved for CR2SE;
- the numeric range available for custom types;
- behavior when receiving an unknown type;
- whether custom type allocation requires additional identification or namespacing;
- rules for future extensions.

Likely standard operations include concepts such as:

OPEN
DATA
END
CANCEL

These names are currently illustrative and are not yet assigned protocol values.

---

8. Flags

"Flags" is a 16-bit bit field containing additional properties of a frame.

Each bit may represent a boolean property.

For example, a future specification could define:

bit 0 -> some property
bit 1 -> another property
...

No flags are currently defined.

For CR2SE version 1, until individual flags are specified, senders must set undefined flag bits to zero.

Receivers must ignore undefined flag bits.

This allows future protocol revisions to introduce optional behavior without changing the frame header layout.

TODO: Flags

Define any flags required by the standard CR2SE frame types.

---

9. Payload Length

"Payload Length" is an unsigned 32-bit integer specifying the number of payload bytes immediately following the header.

A value of zero means that the frame has no payload.

For example:

Payload Length = 5

means that exactly five bytes follow the 12-byte header.

The next byte after those five bytes is the first byte of the next CR2SE frame.

Although the field can mathematically represent payloads approaching 4 GiB, implementations must not use enormous individual frames for transferring large objects.

Large data is divided into multiple frames as described later.

Maximum Frame Size

CR2SE implementations must enforce a configurable maximum accepted payload size.

This prevents a malicious or defective peer from declaring an unreasonable payload length and causing an implementation to allocate excessive memory.

A standard default maximum will be defined before version 1 is finalized.

TODO: Maximum Payload Size

Define:

- required maximum payload size supported by compliant implementations;
- recommended default maximum;
- behavior when the limit is exceeded.

---

10. Stream ID

"Stream ID" is an unsigned 32-bit integer identifying a logical stream within a CR2SE connection.

A stream represents one independent operation or conversation between two peers.

For example, one TCP connection could simultaneously contain:

Stream 1  -> peer search
Stream 2  -> file transfer
Stream 3  -> metadata request
Stream 4  -> another file transfer

Frames belonging to different streams may be interleaved.

For example:

stream=1  search request
stream=2  file request
stream=1  search result
stream=2  file data
stream=2  file data
stream=1  search result
stream=3  metadata request
stream=2  file data

The receiver uses the Stream ID to route each frame to the operation to which it belongs.

This is called multiplexing: multiple logical communications share one physical TCP connection.

---

11. Stream ID Allocation

Both peers may create streams independently.

To prevent both peers from accidentally choosing the same Stream ID, stream IDs are divided according to which endpoint established the TCP connection.

The initiator creates streams using odd IDs:

1
3
5
7
...

The acceptor creates streams using even IDs:

2
4
6
8
...

Therefore:

Initiator                         Acceptor

stream 1  ---------------------->

          <---------------------- stream 2

stream 3  ---------------------->

          <---------------------- stream 4

Stream ID "0" is reserved for connection-level protocol operations and must not be used for ordinary application streams.

Stream IDs must not be reused during the lifetime of the same TCP connection.

The behavior when the available Stream ID space is exhausted will be defined before version 1 is finalized.

---

12. Streams Are Bidirectional

A CR2SE stream is bidirectional.

After a stream has been created, both peers may send frames belonging to that stream.

For example:

Peer A                              Peer B

        stream 17 request
------------------------------------>

        stream 17 response
<------------------------------------

        stream 17 data
<------------------------------------

        stream 17 data
<------------------------------------

A stream is therefore not inherently a "request stream" or "response stream".

The protocol implemented on top of the stream determines the meaning and permitted ordering of its data.

---

13. Multiplexing

Frames from different streams may be transmitted in any order permitted by their respective stream protocols.

Consider two operations:

Stream 1 -> search
Stream 3 -> file transfer

CR2SE does not require:

all stream 1 frames
all stream 3 frames

Instead, an implementation may send:

stream 1
stream 3
stream 3
stream 1
stream 3
stream 1

This allows a large operation to coexist with small or latency-sensitive operations.

For example, transferring a multi-gigabyte file should not require waiting until the transfer finishes before sending a small search result.

CR2SE defines multiplexing at the frame level. TCP itself still provides one ordered byte stream, so packet loss at the TCP layer may temporarily delay all CR2SE streams on that connection.

---

14. Large Data Transfers

Large objects must not be encoded as a single enormous CR2SE frame.

Instead, they are divided into multiple payloads and transmitted through multiple frames belonging to the same stream.

Conceptually:

OPEN stream=17

DATA stream=17
    [chunk]

DATA stream=17
    [chunk]

DATA stream=17
    [chunk]

...

END stream=17

The exact standard frame types are still to be defined, but the principle is part of CR2SE:

«Large objects are streamed through multiple bounded frames rather than represented by one frame containing the complete object.»

This allows implementations to process data incrementally.

For example, a receiver may:

receive frame
      |
      v
process/write payload
      |
      v
discard payload buffer
      |
      v
receive next frame

The complete object therefore does not need to fit in memory.

The meaning of the transferred bytes, such as whether they represent a file, serialized object, search result, or another resource, belongs to the protocol operating on that stream.

---

15. Small Data Transfers

Small messages use exactly the same framing mechanism.

For example, a five-byte payload is simply:

Payload Length = 5
Payload        = 5 bytes

CR2SE therefore does not require separate transport mechanisms for large and small data.

Both are sequences of frames.

The difference is that a small operation may require only one frame while a large operation may require thousands or millions of frames.

---

16. Example Frame

Consider a frame with:

Version        = 1
Type           = 2
Flags          = 0
Stream ID      = 17
Payload Length = 5
Payload        = "hello"

Its bytes are:

01 02 00 00 00 00 00 11 00 00 00 05 68 65 6c 6c 6f

Broken down:

01
│
└─ Version = 1

02
│
└─ Type = 2

00 00
│
└─ Flags = 0

00 00 00 11
│
└─ Stream ID = 17

00 00 00 05
│
└─ Payload Length = 5

68 65 6c 6c 6f
│
└─ Payload = "hello"

The receiver first reads exactly 12 bytes.

After decoding the header, it discovers:

Payload Length = 5

It then reads exactly five additional bytes.

At that point one complete CR2SE frame has been received.

The receiver then starts reading another 12-byte header.

---

17. Partial Reads and Writes

CR2SE implementations must not assume that a single operating-system read or write operation processes an entire frame.

For example, requesting 12 bytes from a TCP socket may return fewer than 12 bytes even though the connection remains valid.

An implementation must continue reading until the complete header has been obtained.

Similarly, after obtaining the payload length, it must continue reading until exactly that number of payload bytes has been obtained.

The same rule applies to writing. An implementation must ensure that all bytes of a frame are written even if the underlying API performs a partial write.

The mechanism used to achieve this is language and library specific and is outside the CR2SE specification.

---

18. Payload Encoding

CR2SE does not impose a universal serialization format on frame payloads.

A payload is an arbitrary sequence of bytes:

00 ... FF

The protocol associated with the stream determines how those bytes are interpreted.

A payload could therefore contain:

- raw file bytes;
- UTF-8 text;
- a custom binary structure;
- Protocol Buffers;
- CBOR;
- JSON;
- another application-specific representation.

CR2SE framing does not need to understand the payload representation.

This separation allows applications to use CR2SE without forcing them to adopt a particular serialization library or data model.

---

19. Connection and Stream Layers

CR2SE separates connection transport from the meaning of individual operations.

Conceptually:

┌───────────────────────────────────────┐
│ Application protocols                 │
│                                       │
│ storage / search / messaging / ...    │
├───────────────────────────────────────┤
│ CR2SE streams                         │
│                                       │
│ independent logical operations        │
├───────────────────────────────────────┤
│ CR2SE frames                          │
│                                       │
│ header + payload                      │
├───────────────────────────────────────┤
│ TCP                                   │
│                                       │
│ reliable ordered byte stream          │
└───────────────────────────────────────┘

This separation is intentional.

The framing layer should not need to understand storage, searching, files, users, or other application concepts.

Likewise, an application protocol should not need to determine where one TCP read ends and another begins.

---

20. Connection Lifetime

A CR2SE TCP connection is intended to carry multiple streams over time.

Opening an operation does not require opening another TCP connection.

For example:

TCP connection established
        |
        +-- stream 1
        |
        +-- stream 3
        |
        +-- stream 5
        |
        +-- stream 7
        |
        ...
        |
TCP connection closed

Closing one stream does not close the TCP connection.

The connection may remain available for future streams.

A TCP connection ending terminates all streams carried by that connection.

---

21. Connection Symmetry

CR2SE peers are symmetric after connection establishment.

The terms initiator and acceptor only determine:

- which peer opened the TCP connection;
- which peer allocates odd or even Stream IDs.

They do not determine which peer may issue requests.

For example:

Initiator                          Acceptor

   ---- request stream 1 ---------->

   <--- request stream 2 -----------

   ---- response stream 2 --------->

   <--- response stream 1 ----------

Both peers may therefore simultaneously request services from each other over the same TCP connection.

---

22. Protocol Errors

Malformed input must not cause an implementation to lose synchronization and continue interpreting arbitrary bytes as valid frames.

Examples of protocol errors include:

- invalid or unsupported protocol versions;
- invalid frame types;
- illegal Stream IDs;
- invalid stream state transitions;
- payload lengths exceeding configured limits;
- invalid use of reserved fields.

The exact distinction between stream-level errors and connection-level errors is not yet defined.

TODO: Error Handling

Define:

- connection-level errors;
- stream-level errors;
- whether an error frame exists;
- behavior for malformed headers;
- behavior for unsupported versions;
- behavior for unknown standard frame types;
- behavior for unknown custom frame types;
- behavior for invalid stream state transitions;
- conditions requiring immediate TCP connection termination.

---

23. Stream Lifecycle

CR2SE streams require a defined lifecycle so that both peers agree about whether a Stream ID is active.

The intended model is approximately:

        OPEN
          |
          v
       ACTIVE
       /     \
      /       \
    END      CANCEL
     |          |
     v          v
   CLOSED     CLOSED

The final state machine has not yet been specified.

TODO: Stream Lifecycle

Define:

- how a stream is opened;
- what information is included when opening it;
- when each peer may send data;
- normal stream completion;
- cancellation;
- remote cancellation;
- invalid state transitions;
- behavior when the TCP connection disappears;
- whether half-closed streams are supported.

---

24. Standard and Custom Types

CR2SE must support both standardized behavior and application-specific extensions.

Standard types provide interoperability between independent CR2SE implementations.

Custom types allow applications to introduce functionality without modifying the core CR2SE specification.

The 8-bit Type field provides 256 possible numeric values:

0 through 255

Part of this space will be assigned to CR2SE itself and part will be available for extensions.

The exact division has not yet been finalized.

TODO: Standard Types

Define the initial standard type registry.

Candidate concepts include:

OPEN
DATA
END
CANCEL
ERROR

For every standard type, specify:

- numeric value;
- allowed Stream IDs;
- payload format;
- permitted flags;
- valid stream states;
- expected receiver behavior.

TODO: Custom Types

Define the extension mechanism.

It must answer:

- which Type values applications may use;
- how independently developed applications avoid collisions;
- how a peer identifies the protocol associated with a custom stream;
- what happens when a peer does not understand an extension;
- whether extensions are negotiated when opening a stream.

---

25. Security

CR2SE version 1 currently specifies framing and stream transport only.

Authentication, peer identity, encryption, integrity protection beyond TCP's transport checks, and authorization are not yet specified.

Applications must therefore not assume that a TCP connection alone proves the identity of the remote peer.

TODO: Security

Define whether security belongs:

- directly in CR2SE;
- in an optional CR2SE layer;
- in the application protocol above CR2SE;
- or in a secure transport below CR2SE.

This decision must be made before CR2SE is recommended for communication over untrusted networks.

---

26. Protocol Definition vs Implementation

This repository defines a wire protocol.

A wire protocol specifies the bytes that independent implementations exchange and the rules used to interpret them.

It should therefore be possible to implement CR2SE independently in different languages:

C implementation
       |
       | CR2SE
       |
Java implementation

or:

Rust implementation
       |
       | CR2SE
       |
C implementation

without either implementation knowing how the other is internally structured.

An implementation is compliant when the bytes it sends and its interpretation of received bytes follow this specification.

Implementation details such as:

- threads;
- async runtimes;
- socket libraries;
- queues;
- memory management;
- internal object models;

are outside the protocol specification unless they affect observable wire behavior.

---

27. Design Principles

CR2SE follows these principles.

TCP is the transport.

All compliant implementations communicate using TCP.

Connections are persistent and bidirectional.

Either peer may initiate operations after a connection has been established.

TCP connection boundaries are not message boundaries.

CR2SE defines explicit binary framing.

Frames are length-prefixed.

Arbitrary binary payloads require no escaping or delimiter detection.

One connection carries multiple logical streams.

Streams are identified by Stream IDs.

Streams may be active concurrently.

Frames belonging to different streams may be interleaved.

Large data is chunked.

Large resources are transferred through multiple bounded frames.

The framing layer is application independent.

CR2SE transports bytes without needing to understand their application-level meaning.

The wire format is language independent.

No part of the protocol depends on the memory layout or serialization behavior of a specific programming language.

---

28. Version 1 Work Remaining

The basic CR2SE framing model is defined, but version 1 is not yet complete.

The main remaining protocol decisions are:

- [ ] Define standard frame types and their numeric values.
- [ ] Define the custom type range and extension mechanism.
- [ ] Define the stream lifecycle and state machine.
- [ ] Define stream opening semantics.
- [ ] Define stream completion and cancellation.
- [ ] Define error handling.
- [ ] Define maximum payload requirements.
- [ ] Define connection-level behavior using Stream ID "0".
- [ ] Define protocol/version negotiation.
- [ ] Define connection shutdown behavior.
- [ ] Define behavior when Stream IDs are exhausted.
- [ ] Define security and peer authentication requirements.
- [ ] Provide normative binary examples and interoperability test vectors.

---

29. Status

CR2SE is currently under design.

The following decisions should be considered stable unless the specification is explicitly revised:

Transport              TCP
Connection             persistent and bidirectional
Peer roles             symmetric after establishment
Framing                 binary, length-prefixed
Header size             12 bytes
Integer byte order      big-endian
Version field           unsigned 8-bit
Type field              unsigned 8-bit
Flags field             unsigned 16-bit
Stream ID               unsigned 32-bit
Payload Length          unsigned 32-bit
Initiator Stream IDs    odd
Acceptor Stream IDs     even
Stream ID 0             reserved
Payload                 arbitrary bytes
Large transfers         multiple bounded frames
Multiplexing            multiple streams per TCP connection

The next major specification task is to define the frame types and stream lifecycle.
