# Node API pseudocode

The [specification](../README.md) defines exact requests and local limits. The
API is language-neutral; maps, locks, and transactions denote behavior, not a
required runtime or database.

```text
function serveLocalClient(socket):
    require configured loopback endpoint
    session = new unauthenticated session with bounded line decoder
    first = readJsonLine(maxBytes=1048576, maxDepth=32)
    require first.operation == "session.open" and first.version == 1
    require constantTimeMatchConfiguredClientToken(first.token)
    send success with version and blob/chunk/message limits
    while next complete bounded JSON line exists:
        reject invalid UTF-8, duplicate members, malformed JSON
        require nonempty string id, at most 128 UTF-8 bytes
        if id is already active: close session
        add id to active requests
        dispatch concurrently under session resource/spending authority
    cancel uncommitted work and close session-owned temporary resources

function finish(session, id, outcome):
    serialize complete JSON line under one writer lock
    send {id, ok:true, result} or {id, ok:false, error:{code,message}}
    remove id from active requests
```

A disconnected caller cannot receive a promised terminal response. Preserve
durable commitments instead of claiming rollback. Cancellation has a separate
request ID and does not itself complete the original request.

```text
function createBlob(session, length):
    require exact uint64 length within session and node quotas
    reserve bounded temporary capacity
    return session-owned opaque handle with expectedLength and offset=0

function writeBlob(session, id, offset, base64):
    blob = require session owns unfinished id
    data = strictlyDecodeBase64(base64); require 1 <= length(data) <= 65536
    require offset == blob.offset and data fits remaining declared length
    append data; increment offset; return written count

function finishBlob(session, id):
    require actual length == declared length
    mark immutable; return length

function readBlob(session, id, offset, length):
    require session owns finished blob
    require 1 <= length <= 65536 and offset <= blob.length
    return up to length bytes and eof=(offset + returnedCount == blob.length)
```

```text
function serviceInvoke(session, parameters):
    connection = require accessible authenticated connection handle
    require explicit credit_issuer and maximum_price within client policy
    offering = fetch and validate current Board selection
    definition = fetch matching definition and validate supported schema
    input = decode schema-bound arguments, pinning session-owned blob handles
    result = PeerProtocol.invoke(connection, offering, input,
                                 maximum_price, credit_issuer)
    on complete validated result:
        expose large bytes/text as finished session-owned blobs
        return {service_result:boundOutput, final_price:exactPrice}
    on explicit failure: return mapped uncharged error
    on uncertain interruption: return outcome_unknown
    unpin input blobs after terminal handling

function serviceOffer(session, parameters):
    require installed locally authorized handler for exact service/version
    require selected wanted offering and explicit issuer
    enforce maximum_resource_price and independent resource budgets
    return PeerProtocol.fulfillWanted(connection, offering, handler)

function cancel(session, requestId):
    target = active request owned by session
    if absent: return {cancel_requested:false}
    signal cancellation; send Transport CANCEL when applicable
    return {cancel_requested:true}
```

Board and definition retrieval never executes implementation suggestions.
`service.check` requests evidence only for standardized remote checks, then
computes the outcome using locally retained expected evidence. Missing expected
evidence gives inconclusive, not a provider-supplied pass. Ledger control calls
map to Peer Protocol and never expose another caller's balances or claim secrets.
