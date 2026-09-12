# Node API pseudocode

This document translates [`NodeApi.md`](../NodeApi.md) into
implementation-neutral algorithms. The specification remains authoritative.
Embedded calls and loopback IPC expose equivalent logical behavior.

## 1. IPC state and framing

```text
ClientSession:
    socket
    decoder                     incremental UTF-8 JSON-message decoder
    outstandingRequestIds       Set<string-or-integer>
    writeLock                   Lock
    resourceLimits

Request:
    id                          JSON string
    operation                   nonempty JSON string
    operationFields             operation-specific top-level members
```

The server binds only an explicitly configured loopback address (`127.0.0.1`
or `::1`) by default. TCP is a byte stream, so the implementation uses the
message-boundary mechanism specified by Node API and must tolerate partial and
coalesced reads. It rejects invalid UTF-8, malformed JSON, duplicate object
members, trailing data, excessive nesting, and messages above its advertised
local limit before dispatch.

```text
function serveClient(socket, node, limits):
    require socket local endpoint is loopback-only
    session = new ClientSession(socket, limits)
    while bytes = socket.readSome():
        for messageBytes in session.decoder.feed(bytes):
            if length(messageBytes) > limits.maximumMessageBytes:
                sendErrorAndMaybeClose(session, NONE, "message_too_large")
                continue
            request = parseAndValidateRequest(messageBytes)
            if request.id in session.outstandingRequestIds:
                sendError(session, request.id, "duplicate_request_id")
                continue
            add request.id to outstandingRequestIds
            dispatchConcurrently(session, node, request)
    cancel session-owned unfinished work according to operation semantics

function finish(session, id, outcome):
    with session.writeLock:
        if outcome is success:
            writeOneMessage({id: id, ok: true, result: outcome.value})
        else:
            writeOneMessage({id: id, ok: false,
                error: {code: outcome.code, message: safeMessage,
                        optional details: boundedDetails}})
    remove id from outstandingRequestIds
```

Responses may complete out of order; `id` performs correlation. Exactly
one success or error is returned for every accepted request. Unknown fields are
handled according to the extension rules, and unknown operations return an
error without terminating an otherwise usable session.

## 2. Dispatch registry

```text
OPERATIONS = {
    "connection.open": connectionOpen,
    "connections.list": connectionsList,
    "connection.close": connectionClose,
    "connection.ping": connectionPing,
    "board.get": boardGet,
    "service.get": serviceGet,
    "service.invoke": serviceInvoke
}

function dispatch(session, node, request):
    handler = OPERATIONS.get(request.operation)
    if handler is NONE: return Error("unknown_operation")
    validate exact required parameter types before side effects
    return handler(node, request.operationFields, session)
```

## 3. Connection operations

```text
function connectionOpen(node, p, session):
    address = validateAddress(p.address)
    port = requireInteger(p.port, 1, 65535)
    expectedId = optionalValidateCr2seId(p.expected_peer_id)
    connection = Network.connect(address, port, expectedId)
    id = node.connections.insertWithUniqueOpaqueId(connection)
    return {connection_id: id, peer_id: connection.authenticatedRemoteId}

function connectionsList(node, p, session):
    require p has no unsupported required semantics
    return {connections: snapshot(node.connections).map(publicConnectionInfo)}

function connectionClose(node, p, session):
    connection = requireSessionVisibleConnection(p.connection_id)
    Network.gracefulClose(connection)
    node.connections.removeAfterTerminal(connection)
    return {}

function connectionPing(node, p, session):
    connection = requireUsableConnection(p.connection_id)
    start = monotonicNow()
    reachable = Network.ping(connection, boundedTimeout(p.timeout))
    return {reachable: reachable,
            optional roundTripMilliseconds: elapsed(start)}
```

Connection IDs are opaque local handles, not peer identities or addresses.
Closing, EOF, and concurrent operations must have deterministic cancellation or
failure outcomes and must never redirect an operation to another connection.

## 4. Remote Board and definitions

```text
function boardGet(node, p, session):
    connection = requireUsableConnection(p.connection_id)
    rawBoard = remoteProtocol(connection).getBoard()
    board = Board.decodeAndValidateBounded(rawBoard, node.boardPolicy)
    return {board: board.source}

function serviceGet(node, p, session):
    connection = requireUsableConnection(p.connection_id)
    offering_id = requireNonemptyUtf8(p.offering_id)
    currentBoard = node.obtainCurrentBoard(connection)
    offering = currentBoard.requireOffering(offering_id)
    rawDefinition = remoteProtocol(connection).getServiceDefinition(offering_id)
    definition = Services.validateDefinitionBounded(rawDefinition, limits)
    Services.requireDefinitionMatchesOffering(definition, offering)
    return {service_definition: definition.source}
```

Never execute implementation suggestions while retrieving metadata. Board and
definition limits apply before large allocation.

## 5. Service invocation

```text
function serviceInvoke(node, p, session):
    connection = requireUsableConnection(p.connection_id)
    offering_id = requireNonemptyUtf8(p.offering_id)
    boardSnapshot = node.obtainCurrentBoard(connection)
    offering = boardSnapshot.requireOffering(offering_id)
    require p.service == offering.service
    require p.service_version == offering.serviceVersion
    definition = node.obtainMatchingDefinition(connection, offering)

    input = Services.validateValue(p.arguments, definition.input, limits)
    agreedPrice = Board.determineAuthorizedPrice(offering, input)
    if p has maximum_price and agreedPrice > exactUint64(p.maximum_price):
        raise Error("price_exceeds_maximum")

    invocation = Services.prepareInvocation(
        connection.authenticatedRemoteId, offering, definition, input,
        agreedPrice)
    result = remoteProtocol(connection).invoke(invocation)
    validated = Services.validateAndFinalizeInvocation(invocation, result)
    return {service_result: validated.output}
```

Large logical values may be streamed by the peer protocol and implementation,
but the Node API must preserve their exact logical value and defined message
boundaries. If no standardized large-result mechanism applies, exceeding the
IPC limit is an explicit error rather than truncation.

## 6. Security and lifecycle

Loopback does not imply a trusted caller. Implementations enforce local access,
resource, concurrency, and optional authentication policy before expensive
work. Error details must not expose private keys, credentials, unrelated client
data, or unsafe provider diagnostics. On shutdown, stop accepting requests,
resolve or cancel every accepted request exactly once, close peer connections,
flush durable state, and then close client sockets.
