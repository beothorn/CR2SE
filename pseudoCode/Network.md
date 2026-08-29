# Network pseudocode

This document translates the normative wire contract in
[`Network.md`](../Network.md) into implementation-neutral pseudocode. The
specification remains authoritative. Names such as `Map`, `Queue`, `Lock`, and
callbacks describe responsibilities, not required classes or concurrency APIs.

The pseudocode assumes conventional, constant-time implementations of Ed25519,
X25519, SHA-256, HKDF-SHA-256, and XChaCha20-Poly1305.

Calls written as `applicationHandler.on...` enqueue an application event; they
must not execute untrusted or re-entrant application code while a connection,
stream, reader, or writer lock is held.

---

## 1. Constants and data structures

```text
VERSION                  = 0x01
HEADER_SIZE              = 12
MAX_PAYLOAD_SIZE         = 65_536
INTEGRITY_TAG_SIZE       = 16
MAX_REASON_SIZE          = 1_024
UINT32_MAX               = 4_294_967_295
UINT64_MAX               = 18_446_744_073_709_551_615

TYPE_HELLO               = 0x01
TYPE_AUTH                = 0x02
TYPE_PING                = 0x03
TYPE_PONG                = 0x04
TYPE_GOAWAY              = 0x05
TYPE_ERROR               = 0x06
TYPE_OPEN                = 0x10
TYPE_DATA                = 0x11
TYPE_END                 = 0x12
TYPE_CANCEL              = 0x13

NO_ERROR                 = 0x0000
PROTOCOL_ERROR           = 0x0001
AUTHENTICATION_FAILED    = 0x0002
FRAME_SIZE_ERROR         = 0x0003
UNSUPPORTED_PROTOCOL     = 0x0004
STREAM_STATE_ERROR       = 0x0005
REFUSED_STREAM           = 0x0006
INTERNAL_ERROR           = 0x0007
ID_EXHAUSTED             = 0x0008
CANCELLED                = 0x0009
RESOURCE_LIMIT           = 0x000a

ROLE_INITIATOR           = 0x01
ROLE_ACCEPTOR            = 0x02

HELLO_SIZE               = 100
AUTH_SIZE                = 64

Frame:
    type                  uint8
    streamId              uint32
    payload               bytes

Stream:
    id                    uint32
    protocolId            ASCII string
    protocolVersion       uint32
    localCanSend          boolean
    remoteCanSend         boolean
    terminal              boolean
    terminalResult        NORMAL | CANCELLED | ERROR | TRANSPORT_FAILURE
    applicationHandler    handler or NONE
    sendOrderLock         Lock

Connection:
    socket
    role                  INITIATOR | ACCEPTOR
    localIdentity
    expectedRemoteId      32 bytes or NONE
    remoteId              32 bytes or NONE
    phase                 HANDSHAKE | ACTIVE | DRAINING | CLOSED

    sendKey               32 bytes or NONE
    receiveKey            32 bytes or NONE
    sendNoncePrefix       16 bytes or NONE
    receiveNoncePrefix    16 bytes or NONE
    nextSendSequence      uint64
    nextReceiveSequence   uint64

    nextLocalStreamId     uint32 or EXHAUSTED
    nextExpectedRemoteStreamId uint32 or EXHAUSTED
    highestLocalOpenedId  uint32, initially 0
    highestRemoteOpenedId uint32, initially 0
    highestRemoteAcceptedId uint32, initially 0
    streams               Map<uint32, Stream>

    sentGoAway            boolean
    receivedGoAway        boolean
    receivedGoAwayLimit   uint32 or NONE
    openLock              Lock
    sendLock              Lock
    stateLock             Lock
```

Because each role's stream IDs are sequential and the parities do not overlap,
the two high-water marks are sufficient to distinguish an old closed stream
from an ID that never existed. An implementation need not retain every closed
stream object forever.

---

## 2. Exact socket I/O

TCP reads and writes may be partial. These helpers are required conceptually.

```text
function readExact(socket, byteCount):
    result = new byte buffer with capacity byteCount

    while length(result) < byteCount:
        part = socket.read(byteCount - length(result))

        if part is ERROR:
            raise TransportFailure

        if part is EOF:
            if length(result) == 0:
                raise CleanEof
            else:
                raise TruncatedFrame

        append part to result

    return result


function writeAll(socket, bytes):
    offset = 0

    while offset < length(bytes):
        count = socket.write(bytes[offset .. end])

        if count is ERROR or count == 0:
            raise TransportFailure

        offset = offset + count
```

`CleanEof` is normal only at a frame boundary. During a handshake or while any
stream is unfinished, it still causes those operations to fail.

---

## 3. Header encoding and preliminary validation

```text
function encodeHeader(type, streamId, payloadLength):
    require type fits uint8
    require streamId fits uint32
    require 0 <= payloadLength <= MAX_PAYLOAD_SIZE

    return byte(VERSION)
        || byte(type)
        || uint16_be(0)              // Flags
        || uint32_be(streamId)
        || uint32_be(payloadLength)


function decodeHeader(headerBytes):
    require length(headerBytes) == HEADER_SIZE

    header.version       = uint8_at(headerBytes, 0)
    header.type          = uint8_at(headerBytes, 1)
    header.flags         = uint16_be_at(headerBytes, 2)
    header.streamId      = uint32_be_at(headerBytes, 4)
    header.payloadLength = uint32_be_at(headerBytes, 8)

    if header.version != VERSION:
        raise UnsupportedVersion

    if header.flags != 0:
        raise ConnectionProtocolError("nonzero flags")

    if header.payloadLength > MAX_PAYLOAD_SIZE:
        raise FrameSizeError

    if header.type not in {
        TYPE_HELLO, TYPE_AUTH, TYPE_PING, TYPE_PONG, TYPE_GOAWAY,
        TYPE_ERROR, TYPE_OPEN, TYPE_DATA, TYPE_END, TYPE_CANCEL
    }:
        raise ConnectionProtocolError("unknown frame type")

    return header
```

The payload limit is checked before allocating or reading a payload buffer.

---

## 4. HELLO construction and parsing

```text
function createLocalHello(localIdentity):
    ephemeralKeyPair = X25519.generateKeyPair(CSPRNG)
    nonce = CSPRNG.randomBytes(32)

    payload = byte(0x01)                         // Handshake Version
        || byte(0x01)                            // Identity Version
        || byte(0x01)                            // Ed25519
        || localIdentity.ed25519PublicKey         // 32 bytes
        || byte(0x01)                            // X25519
        || ephemeralKeyPair.publicKey             // 32 bytes
        || nonce                                  // 32 bytes

    assert length(payload) == HELLO_SIZE

    return {
        payload: payload,
        ephemeralPrivateKey: ephemeralKeyPair.privateKey
    }


function parseRemoteHello(payload, expectedRemoteId):
    if length(payload) != HELLO_SIZE:
        raise AuthenticationFailure("invalid HELLO length")

    if payload[0] != 0x01:
        raise AuthenticationFailure("unsupported handshake version")

    if payload[1] != 0x01 or payload[2] != 0x01:
        raise AuthenticationFailure("unsupported identity format")

    if payload[35] != 0x01:
        raise AuthenticationFailure("unsupported key agreement")

    ed25519PublicKey    = payload[3 .. 34]
    ephemeralPublicKey = payload[36 .. 67]
    nonce               = payload[68 .. 99]

    remoteId = SHA256(
        byte(0x01)
        || byte(0x01)
        || ed25519PublicKey
    )

    if expectedRemoteId != NONE and remoteId != expectedRemoteId:
        raise AuthenticationFailure("unexpected remote identity")

    return {
        payload: payload,
        remoteId: remoteId,
        ed25519PublicKey: ed25519PublicKey,
        ephemeralPublicKey: ephemeralPublicKey,
        nonce: nonce
    }
```

Public-key parsing must use the cryptographic library's validation rules. The
nonce need not be globally stored; its freshness comes from generating it with
a CSPRNG for each connection and signing both HELLO payloads.

---

## 5. Authentication transcript and keys

```text
function makeHelloTranscript(initiatorHello, acceptorHello):
    return uint32_be(length(initiatorHello))
        || initiatorHello
        || uint32_be(length(acceptorHello))
        || acceptorHello


function makeAuthMessage(roleByte, helloTranscript):
    return ASCII("CR2SE-NETWORK-AUTH-V1")
        || byte(0x00)
        || byte(roleByte)
        || helloTranscript


function deriveSessionMaterial(
    role,
    localEphemeralPrivateKey,
    remoteEphemeralPublicKey,
    helloTranscript
):
    sharedSecret = X25519(
        localEphemeralPrivateKey,
        remoteEphemeralPublicKey
    )

    if sharedSecret == 32 zero bytes:
        raise AuthenticationFailure("invalid X25519 shared secret")

    salt = SHA256(
        ASCII("CR2SE-NETWORK-KEYS-V1")
        || byte(0x00)
        || helloTranscript
    )

    prk = HKDF_SHA256.extract(salt, sharedSecret)

    i2aKey = HKDF_SHA256.expand(
        prk, ASCII("CR2SE-NETWORK-V1-I2A-KEY"), 32)
    a2iKey = HKDF_SHA256.expand(
        prk, ASCII("CR2SE-NETWORK-V1-A2I-KEY"), 32)
    i2aPrefix = HKDF_SHA256.expand(
        prk, ASCII("CR2SE-NETWORK-V1-I2A-NONCE"), 16)
    a2iPrefix = HKDF_SHA256.expand(
        prk, ASCII("CR2SE-NETWORK-V1-A2I-NONCE"), 16)

    securelyErase(sharedSecret)
    securelyErase(prk)

    if role == INITIATOR:
        return {
            sendKey: i2aKey,
            receiveKey: a2iKey,
            sendNoncePrefix: i2aPrefix,
            receiveNoncePrefix: a2iPrefix
        }
    else:
        return {
            sendKey: a2iKey,
            receiveKey: i2aKey,
            sendNoncePrefix: a2iPrefix,
            receiveNoncePrefix: i2aPrefix
        }
```

---

## 6. Raw handshake frame I/O

Handshake frames have no integrity tag.

```text
function writeRawHandshakeFrame(connection, type, payload):
    require connection.phase == HANDSHAKE
    require type in {TYPE_HELLO, TYPE_AUTH, TYPE_ERROR}
    require type != TYPE_ERROR or connection error payload is valid

    header = encodeHeader(type, 0, length(payload))

    with connection.sendLock:
        writeAll(connection.socket, header || payload)


function readRawHandshakeFrame(connection):
    headerBytes = readExact(connection.socket, HEADER_SIZE)
    header = decodeHeader(headerBytes)

    if header.streamId != 0:
        raise ConnectionProtocolError("stream frame before authentication")

    if header.type not in {TYPE_HELLO, TYPE_AUTH, TYPE_ERROR}:
        raise ConnectionProtocolError("non-handshake frame before authentication")

    payload = readExact(connection.socket, header.payloadLength)
    return Frame(header.type, 0, payload)
```

---

## 7. Complete connection handshake

Both peers execute the same algorithm with different roles. Sending HELLO before
waiting for the remote HELLO prevents deadlock.

```text
function performHandshake(connection):
    connection.phase = HANDSHAKE

    localHello = createLocalHello(connection.localIdentity)

    try:
        writeRawHandshakeFrame(connection, TYPE_HELLO, localHello.payload)

        firstIncoming = readRawHandshakeFrame(connection)

        if firstIncoming.type == TYPE_ERROR:
            raise RemoteConnectionError(parseErrorPayload(firstIncoming.payload))

        if firstIncoming.type != TYPE_HELLO:
            raise AuthenticationFailure("peer did not send HELLO first")

        remoteHello = parseRemoteHello(
            firstIncoming.payload,
            connection.expectedRemoteId
        )

        if connection.role == INITIATOR:
            initiatorHello = localHello.payload
            acceptorHello = remoteHello.payload
            localRoleByte = ROLE_INITIATOR
            remoteRoleByte = ROLE_ACCEPTOR
        else:
            initiatorHello = remoteHello.payload
            acceptorHello = localHello.payload
            localRoleByte = ROLE_ACCEPTOR
            remoteRoleByte = ROLE_INITIATOR

        transcript = makeHelloTranscript(initiatorHello, acceptorHello)

        session = deriveSessionMaterial(
            connection.role,
            localHello.ephemeralPrivateKey,
            remoteHello.ephemeralPublicKey,
            transcript
        )

        localSignature = Ed25519.sign(
            connection.localIdentity.privateKey,
            makeAuthMessage(localRoleByte, transcript)
        )

        assert length(localSignature) == AUTH_SIZE
        writeRawHandshakeFrame(connection, TYPE_AUTH, localSignature)

        // Every frame sent after this AUTH will use session.sendKey.
        connection.sendKey = session.sendKey
        connection.sendNoncePrefix = session.sendNoncePrefix
        connection.nextSendSequence = 0

        secondIncoming = readRawHandshakeFrame(connection)

        if secondIncoming.type == TYPE_ERROR:
            raise RemoteConnectionError(parseErrorPayload(secondIncoming.payload))

        if secondIncoming.type != TYPE_AUTH:
            raise AuthenticationFailure("peer did not send AUTH second")

        if length(secondIncoming.payload) != AUTH_SIZE:
            raise AuthenticationFailure("invalid AUTH length")

        valid = Ed25519.verify(
            remoteHello.ed25519PublicKey,
            makeAuthMessage(remoteRoleByte, transcript),
            secondIncoming.payload
        )

        if not valid:
            raise AuthenticationFailure("invalid AUTH signature")

        // Every frame received after this AUTH must have a valid tag.
        connection.receiveKey = session.receiveKey
        connection.receiveNoncePrefix = session.receiveNoncePrefix
        connection.nextReceiveSequence = 0
        connection.remoteId = remoteHello.remoteId

        if connection.role == INITIATOR:
            connection.nextLocalStreamId = 1
            connection.nextExpectedRemoteStreamId = 2
        else:
            connection.nextLocalStreamId = 2
            connection.nextExpectedRemoteStreamId = 1

        connection.phase = ACTIVE
        securelyErase(localHello.ephemeralPrivateKey)
        return connection.remoteId

    catch AuthenticationFailure as failure:
        // Send a raw ERROR only if local AUTH has not already been sent.
        // Otherwise framing mode may be ambiguous to an invalid peer.
        bestEffortAuthenticationErrorWhenSafe(connection, failure)
        closeConnection(connection, AUTHENTICATION_FAILED)
        raise failure

    catch any transportOrProtocolFailure as failure:
        closeConnection(connection, failure)
        raise failure
```

The implementation starts its normal protected reader only after
`performHandshake` succeeds. Handshake timeouts are enforced around the entire
operation.

---

## 8. Protected frame encoding

The XChaCha20-Poly1305 call uses empty plaintext and authenticates the visible
header and payload as additional data.

```text
function makeIntegrityTag(key, noncePrefix, sequence, header, payload):
    nonce = noncePrefix || uint64_be(sequence)
    authenticatedData = header || payload

    result = XChaCha20_Poly1305.encrypt(
        key = key,
        nonce = nonce,
        plaintext = empty bytes,
        authenticatedData = authenticatedData
    )

    assert length(result.ciphertext) == 0
    assert length(result.tag) == INTEGRITY_TAG_SIZE
    return result.tag


function verifyIntegrityTag(
    key, noncePrefix, sequence, header, payload, receivedTag
):
    nonce = noncePrefix || uint64_be(sequence)

    return XChaCha20_Poly1305.decryptAndVerify(
        key = key,
        nonce = nonce,
        ciphertext = empty bytes,
        tag = receivedTag,
        authenticatedData = header || payload
    ) succeeds and returns empty bytes


function sendProtectedFrame(connection, type, streamId, payload):
    require connection.phase in {ACTIVE, DRAINING}
    require connection.sendKey != NONE
    require length(payload) <= MAX_PAYLOAD_SIZE

    with connection.sendLock:
        if connection.nextSendSequence == UINT64_MAX:
            // Do not risk a later wrap. The connection is no longer usable.
            closeConnectionWithoutFrame(connection, "send sequence exhausted")
            raise SequenceExhausted

        header = encodeHeader(type, streamId, length(payload))
        sequence = connection.nextSendSequence
        tag = makeIntegrityTag(
            connection.sendKey,
            connection.sendNoncePrefix,
            sequence,
            header,
            payload
        )

        writeAll(connection.socket, header || payload || tag)
        connection.nextSendSequence = sequence + 1
```

Only one writer may assign a sequence number and write frame bytes at a time.
An async implementation normally satisfies this with a single outbound writer
task and a bounded queue.

---

## 9. Protected frame decoding

```text
function readProtectedFrame(connection):
    require connection.receiveKey != NONE

    headerBytes = readExact(connection.socket, HEADER_SIZE)

    try:
        header = decodeHeader(headerBytes)
    catch UnsupportedVersion:
        closeConnectionWithoutFrame(connection, "unsupported version")
        raise
    catch FrameSizeError:
        // Do not allocate or attempt to drain the claimed payload.
        bestEffortConnectionError(connection, FRAME_SIZE_ERROR)
        closeConnection(connection, FRAME_SIZE_ERROR)
        raise
    catch ConnectionProtocolError:
        bestEffortConnectionError(connection, PROTOCOL_ERROR)
        closeConnection(connection, PROTOCOL_ERROR)
        raise

    payload = readExact(connection.socket, header.payloadLength)
    receivedTag = readExact(connection.socket, INTEGRITY_TAG_SIZE)

    sequence = connection.nextReceiveSequence

    if not verifyIntegrityTag(
        connection.receiveKey,
        connection.receiveNoncePrefix,
        sequence,
        headerBytes,
        payload,
        receivedTag
    ):
        // Never answer an integrity failure; no received fields are trusted.
        closeConnectionWithoutFrame(connection, "integrity failure")
        raise IntegrityFailure

    if sequence == UINT64_MAX:
        closeConnectionWithoutFrame(connection, "receive sequence exhausted")
        raise SequenceExhausted

    connection.nextReceiveSequence = sequence + 1
    return Frame(header.type, header.streamId, payload)
```

Semantic processing happens only after the integrity tag succeeds.

---

## 10. Payload codecs

```text
function encodeErrorPayload(errorCode, reason):
    reasonBytes = UTF8.encode(reason)

    require errorCode != NO_ERROR
    require errorCode is a defined version 1 error code
    require length(reasonBytes) <= MAX_REASON_SIZE

    return uint16_be(errorCode)
        || uint16_be(length(reasonBytes))
        || reasonBytes


function parseErrorPayload(payload, allowNoError = false):
    if length(payload) < 4:
        raise MalformedPayload

    errorCode = uint16_be_at(payload, 0)
    reasonLength = uint16_be_at(payload, 2)

    if reasonLength > MAX_REASON_SIZE:
        raise MalformedPayload

    if length(payload) != 4 + reasonLength:
        raise MalformedPayload

    reasonBytes = payload[4 .. end]
    if not UTF8.isValid(reasonBytes):
        raise MalformedPayload

    if errorCode == NO_ERROR and not allowNoError:
        raise MalformedPayload

    if errorCode is not a defined version 1 error code:
        raise MalformedPayload

    return {code: errorCode, reason: UTF8.decode(reasonBytes)}


function encodeGoAwayPayload(lastAcceptedRemoteStreamId, errorCode, reason):
    reasonBytes = UTF8.encode(reason)

    require errorCode is a defined version 1 error code, including NO_ERROR
    require length(reasonBytes) <= MAX_REASON_SIZE

    return uint32_be(lastAcceptedRemoteStreamId)
        || uint16_be(errorCode)
        || uint16_be(length(reasonBytes))
        || reasonBytes


function parseGoAwayPayload(payload):
    if length(payload) < 8:
        raise MalformedPayload

    lastAcceptedId = uint32_be_at(payload, 0)
    diagnostic = parseErrorPayload(payload[4 .. end], allowNoError = true)

    return {
        lastAcceptedRemoteStreamId: lastAcceptedId,
        errorCode: diagnostic.code,
        reason: diagnostic.reason
    }


function encodeOpenPayload(protocolId, protocolVersion):
    idBytes = ASCII.encode(protocolId)

    require 1 <= length(idBytes) <= 255
    require isValidProtocolId(idBytes)
    require 1 <= protocolVersion <= UINT32_MAX

    return uint16_be(length(idBytes))
        || idBytes
        || uint32_be(protocolVersion)


function parseOpenPayload(payload):
    if length(payload) < 7:
        raise MalformedPayload

    idLength = uint16_be_at(payload, 0)

    if idLength < 1 or idLength > 255:
        raise MalformedPayload

    if length(payload) != 2 + idLength + 4:
        raise MalformedPayload

    idBytes = payload[2 .. 2 + idLength - 1]
    protocolVersion = uint32_be_at(payload, 2 + idLength)

    if not isValidProtocolId(idBytes) or protocolVersion == 0:
        raise MalformedPayload

    return {
        protocolId: ASCII.decode(idBytes),
        protocolVersion: protocolVersion
    }


function isValidProtocolId(bytes):
    if any byte is not one of lowercase a-z, digit 0-9, dot, or hyphen:
        return false

    if first or last byte is dot or hyphen:
        return false

    if bytes contains two adjacent dots:
        return false

    return true
```

The last function is an equivalent procedural check for the grammar in the
specification. Implementations may use an exact anchored regular expression.

---

## 11. Stream creation

```text
function openStream(connection, protocolId, protocolVersion, handler):
    // This lock preserves OPEN wire order when callers open concurrently.
    with connection.openLock:
        idsExhausted = false

        with connection.stateLock:
            if connection.phase != ACTIVE:
                raise ConnectionDrainingOrClosed

            if connection.sentGoAway or connection.receivedGoAway:
                raise ConnectionDrainingOrClosed

            if connection.nextLocalStreamId == EXHAUSTED:
                idsExhausted = true
            else:
                streamId = connection.nextLocalStreamId

                if streamId > UINT32_MAX - 2:
                    connection.nextLocalStreamId = EXHAUSTED
                else:
                    connection.nextLocalStreamId = streamId + 2

                connection.highestLocalOpenedId = streamId

                stream = Stream(
                    id = streamId,
                    protocolId = protocolId,
                    protocolVersion = protocolVersion,
                    localCanSend = true,
                    remoteCanSend = true,
                    terminal = false,
                    applicationHandler = handler,
                    sendOrderLock = new Lock()
                )

                connection.streams[streamId] = stream

        if idsExhausted:
            beginGoAway(connection, ID_EXHAUSTED, "stream IDs exhausted")
            raise StreamIdsExhausted

        payload = encodeOpenPayload(protocolId, protocolVersion)

        try:
            sendProtectedFrame(connection, TYPE_OPEN, streamId, payload)
        catch failure:
            terminateStreamLocally(stream, TRANSPORT_FAILURE, failure)
            raise

        return stream
```

Creating the local stream state before making `OPEN` visible ensures an
immediate remote response can be routed correctly.

---

## 12. Sending stream data

```text
function sendBytes(connection, stream, byteSource):
    while byteSource has bytes:
        chunk = byteSource.takeAtMost(MAX_PAYLOAD_SIZE)

        if length(chunk) == 0:
            continue

        with stream.sendOrderLock:
            with connection.stateLock:
                if stream.terminal:
                    raise StreamClosed

                if not stream.localCanSend:
                    raise LocalDirectionAlreadyEnded

            sendProtectedFrame(connection, TYPE_DATA, stream.id, chunk)


function endLocalDirection(connection, stream):
    completed = false

    with stream.sendOrderLock:
        with connection.stateLock:
            if stream.terminal:
                raise StreamClosed

            if not stream.localCanSend:
                raise LocalDirectionAlreadyEnded

        try:
            sendProtectedFrame(connection, TYPE_END, stream.id, empty bytes)
        catch failure:
            terminateStreamLocally(stream, TRANSPORT_FAILURE, failure)
            raise

        with connection.stateLock:
            // sendOrderLock prevented later local DATA from passing this END.
            stream.localCanSend = false

            if not stream.remoteCanSend and not stream.terminal:
                markNormallyClosed(stream)
                completed = true

    if completed:
        stream.applicationHandler.onComplete()


function cancelStream(connection, stream, errorCode = CANCELLED, reason = ""):
    require errorCode in {CANCELLED, RESOURCE_LIMIT, INTERNAL_ERROR}

    with stream.sendOrderLock:
        with connection.stateLock:
            if stream.terminal:
                return

            markTerminal(stream, CANCELLED)

        payload = encodeErrorPayload(errorCode, reason)
        sendProtectedFrame(connection, TYPE_CANCEL, stream.id, payload)
```

An outbound implementation must preserve each stream's local `DATA`/`END`
ordering even when it schedules frames fairly across streams.

---

## 13. Reader loop and dispatch

```text
function runConnectionReader(connection):
    require connection.phase in {ACTIVE, DRAINING}

    try:
        while connection.phase != CLOSED:
            frame = readProtectedFrame(connection)
            dispatchAuthenticatedFrame(connection, frame)

            if connection.phase == DRAINING and no active streams remain:
                closeConnection(connection, NO_ERROR)
                return

    catch CleanEof:
        closeConnection(connection, "TCP EOF")

    catch TruncatedFrame or TransportFailure:
        closeConnection(connection, "truncated or failed TCP stream")

    catch ConnectionProtocolError as failure:
        failConnection(connection, PROTOCOL_ERROR, failure.message)


function dispatchAuthenticatedFrame(connection, frame):
    validateTypeAndStreamIdCombination(frame)

    if frame.streamId == 0:
        dispatchConnectionFrame(connection, frame)
        return

    if frame.type == TYPE_OPEN:
        receiveOpen(connection, frame)
        return

    stream = connection.streams.get(frame.streamId)

    if stream == NONE:
        if wasPreviouslyCreated(connection, frame.streamId):
            // The terminal stream object was already compacted away.
            discard frame
            return

        failConnection(connection, PROTOCOL_ERROR, "frame for unknown stream")
        return

    if stream.terminal:
        // It may have been queued before CANCEL or ERROR crossed the wire.
        discard frame
        return

    switch frame.type:
        case TYPE_DATA:
            receiveData(connection, stream, frame.payload)

        case TYPE_END:
            receiveEnd(connection, stream, frame.payload)

        case TYPE_CANCEL:
            receiveCancel(connection, stream, frame.payload)

        case TYPE_ERROR:
            receiveStreamError(connection, stream, frame.payload)

        default:
            failConnection(connection, PROTOCOL_ERROR,
                "connection frame used on stream")


function wasPreviouslyCreated(connection, streamId):
    if streamId == 0:
        return false

    if streamId has local stream parity:
        return streamId <= connection.highestLocalOpenedId

    if streamId has remote stream parity:
        return streamId <= connection.highestRemoteOpenedId

    return false
```

```text
function validateTypeAndStreamIdCombination(frame):
    connectionTypes = {
        TYPE_HELLO, TYPE_AUTH, TYPE_PING, TYPE_PONG, TYPE_GOAWAY
    }

    streamTypes = {TYPE_OPEN, TYPE_DATA, TYPE_END, TYPE_CANCEL}

    if frame.type in connectionTypes and frame.streamId != 0:
        raise ConnectionProtocolError

    if frame.type in streamTypes and frame.streamId == 0:
        raise ConnectionProtocolError

    // ERROR is allowed on stream 0 or a known/rejected nonzero stream.

    if frame.type in {TYPE_HELLO, TYPE_AUTH}:
        // These are never valid after the handshake.
        raise ConnectionProtocolError
```

---

## 14. Receiving OPEN

```text
function receiveOpen(connection, frame):
    remoteUsesOddIds = (connection.role == ACCEPTOR)

    if frame.streamId == 0:
        failConnection(connection, PROTOCOL_ERROR, "OPEN on stream zero")
        return

    if isOdd(frame.streamId) != remoteUsesOddIds:
        failConnection(connection, PROTOCOL_ERROR, "wrong stream parity")
        return

    if connection.nextExpectedRemoteStreamId == EXHAUSTED:
        failConnection(connection, PROTOCOL_ERROR, "remote stream IDs exhausted")
        return

    if frame.streamId != connection.nextExpectedRemoteStreamId:
        failConnection(connection, PROTOCOL_ERROR,
            "stream ID gap, reuse, or reordering")
        return

    with connection.stateLock:
        connection.highestRemoteOpenedId = frame.streamId

        if frame.streamId > UINT32_MAX - 2:
            connection.nextExpectedRemoteStreamId = EXHAUSTED
        else:
            connection.nextExpectedRemoteStreamId = frame.streamId + 2

    try:
        openInfo = parseOpenPayload(frame.payload)
    catch MalformedPayload:
        with connection.stateLock:
            stream = Stream(
                id = frame.streamId,
                protocolId = "",
                protocolVersion = 0,
                localCanSend = false,
                remoteCanSend = false,
                terminal = true,
                terminalResult = ERROR,
                applicationHandler = NONE,
                sendOrderLock = new Lock()
            )
            connection.streams[frame.streamId] = stream

        sendProtectedFrame(
            connection,
            TYPE_ERROR,
            frame.streamId,
            encodeErrorPayload(PROTOCOL_ERROR, "malformed OPEN")
        )
        return

    with connection.stateLock:
        stream = Stream(
            id = frame.streamId,
            protocolId = openInfo.protocolId,
            protocolVersion = openInfo.protocolVersion,
            localCanSend = true,
            remoteCanSend = true,
            terminal = false,
            sendOrderLock = new Lock()
        )
        connection.streams[frame.streamId] = stream

        if connection.sentGoAway or connection.receivedGoAway:
            markTerminal(stream, ERROR)
            rejection = REFUSED_STREAM
        else if not applicationRegistry.supports(
            openInfo.protocolId,
            openInfo.protocolVersion
        ):
            markTerminal(stream, ERROR)
            rejection = UNSUPPORTED_PROTOCOL
        else if active stream resource limit would be exceeded:
            markTerminal(stream, ERROR)
            rejection = RESOURCE_LIMIT
        else:
            stream.applicationHandler = applicationRegistry.createHandler(
                connection.remoteId,
                openInfo.protocolId,
                openInfo.protocolVersion
            )
            connection.highestRemoteAcceptedId = frame.streamId
            rejection = NONE

    if rejection != NONE:
        sendProtectedFrame(
            connection,
            TYPE_ERROR,
            frame.streamId,
            encodeErrorPayload(rejection, "")
        )
    else:
        stream.applicationHandler.onOpen(stream)
```

The handler receives `connection.remoteId` as an already authenticated identity.
It does not repeat the network identity proof.

---

## 15. Receiving stream frames

```text
function receiveData(connection, stream, payload):
    if length(payload) == 0:
        failStream(connection, stream, STREAM_STATE_ERROR, "empty DATA")
        return

    with connection.stateLock:
        if not stream.remoteCanSend:
            failStream(connection, stream, STREAM_STATE_ERROR,
                "DATA after END")
            return

    accepted = stream.applicationHandler.onBytes(payload)

    if not accepted because bounded local queue is full:
        cancelStream(connection, stream, RESOURCE_LIMIT, "consumer too slow")


function receiveEnd(connection, stream, payload):
    if length(payload) != 0:
        failStream(connection, stream, STREAM_STATE_ERROR,
            "END payload must be empty")
        return

    with connection.stateLock:
        if not stream.remoteCanSend:
            failStream(connection, stream, STREAM_STATE_ERROR,
                "duplicate END")
            return

        stream.remoteCanSend = false
        locallyEnded = not stream.localCanSend

        if locallyEnded:
            markNormallyClosed(stream)

    stream.applicationHandler.onRemoteEnd()

    if locallyEnded:
        stream.applicationHandler.onComplete()


function receiveCancel(connection, stream, payload):
    diagnostic = parseErrorPayload(payload)
        or failConnection(connection, PROTOCOL_ERROR, "malformed CANCEL")

    if diagnostic.code not in {CANCELLED, RESOURCE_LIMIT, INTERNAL_ERROR}:
        failConnection(connection, PROTOCOL_ERROR, "invalid CANCEL code")
        return

    with connection.stateLock:
        markTerminal(stream, CANCELLED)

    stream.applicationHandler.onCancelled(diagnostic)


function receiveStreamError(connection, stream, payload):
    diagnostic = parseErrorPayload(payload)
        or failConnection(connection, PROTOCOL_ERROR, "malformed ERROR")

    with connection.stateLock:
        markTerminal(stream, ERROR)

    stream.applicationHandler.onNetworkError(diagnostic)


function failStream(connection, stream, errorCode, reason):
    with stream.sendOrderLock:
        with connection.stateLock:
            if stream.terminal:
                return
            markTerminal(stream, ERROR)

        sendProtectedFrame(
            connection,
            TYPE_ERROR,
            stream.id,
            encodeErrorPayload(errorCode, reason)
        )

    stream.applicationHandler.onNetworkError({errorCode, reason})
```

A malformed network `ERROR` or `CANCEL` is connection-wide because the receiver
cannot safely interpret the peer's requested state transition.

---

## 16. Connection-control dispatch

```text
function dispatchConnectionFrame(connection, frame):
    switch frame.type:
        case TYPE_PING:
            if length(frame.payload) != 8:
                failConnection(connection, PROTOCOL_ERROR, "invalid PING")
                return

            sendProtectedFrame(connection, TYPE_PONG, 0, frame.payload)

        case TYPE_PONG:
            if length(frame.payload) != 8:
                failConnection(connection, PROTOCOL_ERROR, "invalid PONG")
                return

            outstandingPings.consumeIfPresent(frame.payload)
            // Unknown and duplicate tokens are ignored.

        case TYPE_GOAWAY:
            receiveGoAway(connection, frame.payload)

        case TYPE_ERROR:
            diagnostic = parseErrorPayload(frame.payload)
                or closeConnectionWithoutFrame(connection, "malformed ERROR")

            closeConnection(connection, diagnostic)

        default:
            failConnection(connection, PROTOCOL_ERROR,
                "invalid connection-level frame")
```

```text
function receiveGoAway(connection, payload):
    info = parseGoAwayPayload(payload)
        or failConnection(connection, PROTOCOL_ERROR, "malformed GOAWAY")

    if info.errorCode not in all defined error codes:
        failConnection(connection, PROTOCOL_ERROR, "unknown GOAWAY code")
        return

    if info.lastAcceptedRemoteStreamId != 0:
        if parity(info.lastAcceptedRemoteStreamId) != local stream parity:
            failConnection(connection, PROTOCOL_ERROR, "invalid GOAWAY ID")
            return

    if info.lastAcceptedRemoteStreamId > connection.highestLocalOpenedId:
        failConnection(connection, PROTOCOL_ERROR, "GOAWAY names unopened stream")
        return

    if connection.receivedGoAwayLimit != NONE:
        if info.lastAcceptedRemoteStreamId > connection.receivedGoAwayLimit:
            failConnection(connection, PROTOCOL_ERROR,
                "GOAWAY limit increased")
            return

    refusedHandlers = empty list

    with connection.stateLock:
        connection.receivedGoAway = true
        connection.receivedGoAwayLimit = info.lastAcceptedRemoteStreamId
        connection.phase = DRAINING

        for each locally-created, nonterminal stream:
            if stream.id > info.lastAcceptedRemoteStreamId:
                markTerminal(stream, ERROR)
                append stream.applicationHandler to refusedHandlers

    for each handler in refusedHandlers:
        handler.onNetworkError(REFUSED_STREAM)

    if not connection.sentGoAway:
        beginGoAway(connection, NO_ERROR, "")

    closeIfDrained(connection)


function beginGoAway(connection, errorCode = NO_ERROR, reason = ""):
    with connection.stateLock:
        if connection.sentGoAway or connection.phase == CLOSED:
            return

        connection.sentGoAway = true
        connection.phase = DRAINING
        lastAccepted = connection.highestRemoteAcceptedId

    payload = encodeGoAwayPayload(lastAccepted, errorCode, reason)
    sendProtectedFrame(connection, TYPE_GOAWAY, 0, payload)
    closeIfDrained(connection)
```

---

## 17. Connection failures and cleanup

```text
function failConnection(connection, errorCode, reason):
    if connection.phase == CLOSED:
        return

    if errorCode permits a response and connection.sendKey != NONE:
        bestEffortConnectionError(connection, errorCode, reason)

    closeConnection(connection, errorCode)
    raise ConnectionClosed(errorCode, reason)


function bestEffortConnectionError(connection, errorCode, reason = ""):
    try:
        payload = encodeErrorPayload(errorCode, truncateUtf8(reason, 1024))
        sendProtectedFrame(connection, TYPE_ERROR, 0, payload)
    catch any failure:
        // Closing TCP remains mandatory; reporting the error is optional.
        do nothing


function bestEffortAuthenticationErrorWhenSafe(connection, failure):
    if connection.sendKey != NONE:
        // Local AUTH was already written, so do not risk a framing-mode dispute.
        return

    try:
        payload = encodeErrorPayload(
            AUTHENTICATION_FAILED,
            truncateUtf8(failure.message, 1024)
        )
        writeRawHandshakeFrame(connection, TYPE_ERROR, payload)
    catch any failure:
        do nothing


function markTerminal(stream, result):
    stream.localCanSend = false
    stream.remoteCanSend = false
    stream.terminal = true
    stream.terminalResult = result


function markNormallyClosed(stream):
    require not stream.localCanSend
    require not stream.remoteCanSend
    markTerminal(stream, NORMAL)


function terminateStreamLocally(stream, result, detail):
    if stream.terminal:
        return

    markTerminal(stream, result)

    if stream.applicationHandler != NONE:
        stream.applicationHandler.onNetworkError(detail)


function closeIfDrained(connection):
    with connection.stateLock:
        drained = no nonterminal stream remains

    if drained:
        closeConnection(connection, NO_ERROR)


function closeConnectionWithoutFrame(connection, cause):
    closeConnection(connection, cause)


function closeConnection(connection, cause):
    handlersToFail = empty list

    with connection.stateLock:
        if connection.phase == CLOSED:
            return

        connection.phase = CLOSED

        for each nonterminal stream:
            markTerminal(stream, TRANSPORT_FAILURE)
            if stream.applicationHandler != NONE:
                append stream.applicationHandler to handlersToFail

    connection.socket.close()

    for each handler in handlersToFail:
        handler.onNetworkError({TRANSPORT_FAILURE, cause})

    securelyErase(connection.sendKey)
    securelyErase(connection.receiveKey)
    securelyErase(connection.sendNoncePrefix)
    securelyErase(connection.receiveNoncePrefix)
```

No parser attempts to find a new frame boundary after a malformed header,
truncated frame, or failed integrity tag.

---

## 18. Suggested implementation task split

This is not a required thread model, but it keeps the invariants simple:

```text
connection task
    perform handshake
    own connection lifecycle

reader task
    read exactly one complete frame at a time
    authenticate before dispatch
    mutate receive-side stream state in frame order

writer task
    accept frames through a bounded queue
    assign the next send sequence
    serialize complete frame bytes
    schedule stream queues fairly

application handlers
    consume bounded DATA chunks
    produce bounded DATA chunks
    never read from or write directly to the TCP socket
```

State transitions shared by application handlers, reader, and writer need a
lock, event loop, actor mailbox, or equivalent serialization mechanism.

---

## 19. Minimum conformance cases

An implementation should test at least these cases against its frame parser and
state machine:

```text
header split across every possible TCP read boundary;
payload and integrity tag split across many reads;
several frames returned by one socket read;
partial socket writes;
zero-length END and nonempty DATA;
DATA payloads of 1 and 65,536 bytes;
rejection of payload length 65,537 before allocation;
big-endian encoding of every integer field;
initiator odd IDs and acceptor even IDs;
interleaved frames on several streams;
independent half-close in both orders;
queued DATA arriving after CANCEL and being discarded;
stream-ID reuse, wrong parity, gaps, and out-of-order IDs;
OPEN after GOAWAY being refused;
active streams draining after GOAWAY;
HELLO or AUTH duplication and order violations;
expected CR2SE ID mismatch;
modified HELLO, AUTH, header, payload, and tag;
replay of a protected frame at a later sequence number;
directional key or nonce-prefix reversal;
unknown frame type and nonzero flags;
EOF at a frame boundary and at every truncated-frame position;
bounded buffering when an application consumer stops reading.
```

Cryptographic interoperability tests must check the fixed Ed25519 keys, X25519
ephemeral keys, HELLO nonces, transcript, HKDF output, and tag bytes in
[`NetworkTestVectors.md`](./NetworkTestVectors.md).
