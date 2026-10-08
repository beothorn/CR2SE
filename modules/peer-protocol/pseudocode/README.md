# Peer Protocol pseudocode

The [specification](../README.md) owns the wire format. All writes below produce
complete records, split across Transport DATA frames as needed.

Use the [fixed encoding vectors](./TestVectors.md) to check record boundaries
and typed values independently of the Transport cryptographic vectors.

```text
function readRecord(stream):
    kind, length = readExactly(1 byte, 4 big-endian bytes)
    validate kind and length before allocation
    body = readExactly(length)
    if kind == CONTROL:
        return parseBoundedLosslessJson(body, rejectDuplicates=true, depth=32)
    return validateBodyChunk(body)

function invoke(connection, selection, input, spendingBound):
    stream = open(connection, "cr2se.peer", 1)
    metadata, bodies = bindValue(input, selection.inputSchema)
    send propose(selection, metadata, spendingBound)
    response = readControl()
    if valid service-defined cached retry:
        send END; receiveAndValidateOriginalResultWithoutNewDebit(response)
        return
    require response is quote
    validate identities, contract, terms, price formula and spendingBound
    reserve local spending or issuance capacity
    send accept(response.quoteId, SHA256(exactReceivedQuoteJson))
    send bodies in descriptor order
    send input.end; send END
    result = receiveMetadataBodiesAndTerminalMarker()
    validate full result and final price
    apply corresponding local settlement once
    return result
on explicit uncommitted failure:
    release reservation; return service failure
on interruption after acceptance:
    retain journal; return OUTCOME_UNKNOWN; do not retry side effects

function serveInvocation(stream, proposal):
    if service-specific durable retry matches:
        return cached output with no new charge
    validate offering, metadata, trust, issuer mode, and capacity
    quote = constructBoundedQuote()
    send quote
    require accept.quoteId and accept.quoteHash match exact sent quote
    reserve balance or issuance capacity atomically
    receive bounded bodies and input.end; require requester END
    validate complete input before effectful work
    output = service.performUnderAcceptedTerms()
    journal durable output/effect and local settlement consistently
    send result, bodies, result.end, END
    preserve committed journal if sending fails

function fulfillWanted(connection, wantedOffering):
    send offer on a fresh peer stream
    proposal = receive publisher's authorized input proposal or failure
    serveInvocation(stream, proposal) // local node is provider
```

For every read, enforce both record limits and total authorized bytes. Use
bounded queues, deadlines, and temporary storage. Cancelled streams do not
authorize erasing committed leases or repeating payments.
