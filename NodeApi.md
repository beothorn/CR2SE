# CR2SE Node API

The CR2SE Node API defines how an application controls a local CR2SE node.

The [CR2SE Glossary](./Glossary.md) defines the common meaning of **Node API**, **node**, **peer**, **connection**, **Board**, **offering**, and **invocation** used by this specification.

This form is useful when one process manages communication with peers as a long-running node.
When an application acts more like a local client, it may embed a CR2SE implementation directly through libraries.

A CR2SE node maintains connections to other nodes, communicates with those nodes, and exposes services available through those connections.

Applications need a standard way to tell a local node to perform operations such as:

* connect to another node;
* disconnect from another node;
* list current connections;
* check whether a connection is responsive;
* ask a connected node for its board;
* retrieve the complete definition of a service advertised on that board;
* invoke a service offered by a connected node.

The Node API defines these operations independently of how a CR2SE implementation is written.

It also defines two ways for an application to access them:

1. **Embedded access**, where the application and CR2SE implementation run in the same process.
2. **Local IPC access**, where an application communicates with a separately running CR2SE node.

Both forms expose the same logical operations.

---

## 1. Node API and Network Protocol

The Node API and the CR2SE network protocol solve different problems.

The CR2SE network protocol defines communication between nodes:

```text
Node A                         Node B

        CR2SE Network
------------------------------------>
<------------------------------------
```

The Node API defines communication between an application and its local node:

```text
Application
    |
    | Node API
    v
Local CR2SE Node
    |
    | CR2SE Network
    v
Remote CR2SE Node
```

For example, an application may issue:

```text
connect to 192.0.2.10:8042
```

through the Node API.

The local node then establishes the corresponding CR2SE network connection.

Similarly, an application may ask:

```text
get the board from connection X
```

The Node API receives that request, while the local node is responsible for performing the required CR2SE communication with the remote node.

The Node API must therefore not be confused with the CR2SE peer-to-peer wire protocol defined in `Network.md`.

---

## 2. Logical API

The Node API is first defined as a set of logical operations.

An implementation must make these operations available regardless of whether the node is embedded or accessed through IPC.

Conceptually:

```text
                    Node API
                       |
          +------------+------------+
          |                         |
     Embedded API                Local IPC
          |                         |
          +------------+------------+
                       |
                  CR2SE Node
                       |
                CR2SE Network
                       |
                 Remote Nodes
```

The exact function names, classes, modules, callbacks, concurrency primitives, and other programming constructs used by an embedded implementation are implementation-specific.

Their behavior must correspond to the operations defined by this document.

The local IPC representation is standardized so that an application can communicate with a compliant standalone CR2SE implementation without knowing how that implementation was built.

---

## 3. Embedded Access

An implementation may embed a CR2SE node directly into an application.

In this case:

```text
Application
    |
    | direct API calls
    v
CR2SE implementation
```

No socket, JSON serialization, IPC connection, or local server is required.

For example, the application may directly perform the logical equivalent of:

```text
connect(address)

list_connections()

ping(connection)

get_board(connection)

get_service(connection, offering_id)

invoke_service(connection, service, arguments)

disconnect(connection)
```

These names are illustrative only.

The programming interface used inside a particular implementation is not part of the CR2SE specification.

What is standardized is the meaning of each operation and its inputs and outputs.

---

## 4. Local IPC Access

A CR2SE node may also run as a separate long-running process.

For example:

```text
Application A ----\
Application B -----+---- Local IPC ---- CR2SE Node ---- Remote peers
Application C ----/
```

Applications communicate with the node through a local IPC endpoint.

CR2SE standardizes this IPC interface so that independently implemented applications and nodes can interoperate.

A client must not need implementation-specific libraries to control a standalone CR2SE node.

---

## 5. Local IPC Transport

The standard CR2SE Node API IPC transport is **TCP over the loopback interface**.

The server must listen only on a loopback address.

For IPv4 this means:

```text
127.0.0.1
```

For IPv6 this means:

```text
::1
```

A Node API server must not expose the Node API on an external network interface by default.

For example:

```text
127.0.0.1:39471
```

is valid.

Listening on:

```text
0.0.0.0:39471
```

is not valid as the default Node API configuration because it would make the control interface reachable from other machines.

The port is configurable.

CR2SE does not reserve a single mandatory Node API port because multiple CR2SE nodes may run on the same machine.

---

## 6. Why Loopback TCP

The Node API uses loopback TCP rather than an operating-system-specific IPC mechanism because the API is intended to be portable.

Operating systems provide mechanisms such as local domain sockets and named pipes, but their APIs and behavior differ between platforms.

TCP provides a common abstraction available on the platforms on which CR2SE implementations are expected to run.

Because the connection is bound to the loopback interface, traffic remains local to the machine.

Implementations may additionally expose platform-specific IPC mechanisms, but portable clients must be able to use the standard loopback TCP interface.

---

## 7. Connection Lifetime

A Node API IPC connection is persistent.

A client connects once and may issue multiple operations over the same connection.

For example:

```text
Client                         CR2SE Node

       TCP connection
---------------------------------->

       connect request
---------------------------------->

       connect response
<----------------------------------

       list request
---------------------------------->

       list response
<----------------------------------

       board request
---------------------------------->

       board response
<----------------------------------

       service definition request
---------------------------------->

       service definition response
<----------------------------------

       service request
---------------------------------->

       service response
<----------------------------------
```

Opening a new TCP connection for every command is unnecessary.

A client may keep the connection open for as long as it needs to interact with the node.

Multiple applications may have independent Node API connections to the same node.

---

## 8. Bidirectional Communication

A Node API IPC connection is bidirectional.

Initially, version 1 primarily uses request and response messages:

```text
Client                  Node

request ----------------->

         <--------------- response
```

However, the transport is intentionally persistent and bidirectional so that future Node API versions can support node-initiated events.

Possible future examples include:

```text
connection opened
connection closed
incoming request
service result available
board changed
```

Clients must therefore not assume that the Node API will permanently remain a strictly synchronous request-then-response protocol.

The event model itself is not yet defined.

---

## 9. JSON Encoding

Node API IPC messages are encoded as JSON.

JSON is used because it is widely supported and can be read and generated without requiring CR2SE-specific serialization libraries.

Every message must be a valid JSON object.

For example:

```json
{
  "id": "17",
  "operation": "connections.list"
}
```

JSON strings are Unicode strings.

The bytes sent over the IPC connection must use UTF-8 encoding.

---

## 10. Message Boundaries

TCP is a byte stream and does not preserve message boundaries.

The Node API therefore needs a way to determine where one JSON message ends and the next begins.

Node API version 1 uses **newline-delimited JSON**.

Each message consists of:

```text
one JSON object
followed by
one LF byte
```

where LF is:

```text
0x0A
```

For example, the following represents two messages:

```text
{"id":"1","operation":"connections.list"}\n
{"id":"2","operation":"connection.ping","connection_id":"abc"}\n
```

The newline is a framing delimiter and is not part of the JSON document.

A sender must therefore serialize each Node API message as a single JSON object followed by LF.

Whitespace may exist inside the JSON document, but literal line breaks must not appear inside a Node API message.

Newlines contained in JSON string values must be escaped according to JSON rules.

This framing format is sometimes called JSON Lines or newline-delimited JSON.

---

## 11. Requests

A request asks the node to perform an operation.

Every request must contain:

```json
{
  "id": "17",
  "operation": "connections.list"
}
```

The fields are:

`id`

A client-generated identifier for this request.

`operation`

The Node API operation to execute.

Additional fields depend on the operation.

---

## 12. Request IDs

Each request contains an `id`.

The ID allows a client to associate a response with the request that produced it.

For example:

```text
Client                                  Node

id=100  connections.list ---------------->

id=101  connection.ping ----------------->

                    <-------------- id=101 response

                    <-------------- id=100 response
```

Responses are not required to arrive in the same order as requests.

This permits multiple operations to be active simultaneously.

Request IDs are JSON strings.

A client must not reuse an ID while a request with that ID is still active on the same IPC connection.

The meaning of an ID is local to one IPC connection.

Another client may independently use the same ID.

For example, both clients may issue a request with:

```json
"id": "1"
```

without conflict.

---

## 13. Successful Responses

Every request produces either a successful response or an error response.

A successful response contains:

```json
{
  "id": "17",
  "ok": true,
  "result": {}
}
```

`id` identifies the request.

`ok` is `true`.

`result` contains the operation-specific result.

The result may be any JSON value permitted by the operation.

---

## 14. Error Responses

If an operation cannot be completed, the node returns:

```json
{
  "id": "17",
  "ok": false,
  "error": {
    "code": "connection_not_found",
    "message": "The requested connection does not exist."
  }
}
```

The `code` field is intended for programs.

The `message` field is intended for humans and debugging.

Applications should make decisions based on `code`, not by parsing `message`.

Additional error information may be included in a `details` field:

```json
{
  "id": "17",
  "ok": false,
  "error": {
    "code": "connection_failed",
    "message": "Could not establish the connection.",
    "details": {
      "address": "192.0.2.10",
      "port": 8042
    }
  }
}
```

## 15. Concurrent Requests

A client may issue another request before receiving the response to a previous request.

For example:

```text
Client                              Node

request 1 -------------------------->

request 2 -------------------------->

request 3 -------------------------->

                  <----------------- response 2

                  <----------------- response 1

                  <----------------- response 3
```

The `id` field correlates each response with its request.

Implementations must not require clients to wait for one request to complete before issuing another.

An implementation may still impose limits on the number of simultaneous requests for resource-management purposes.

---

# Connection Operations

The following operations manage CR2SE connections.

---

## 16. `connection.open`

`connection.open` asks the local node to establish a CR2SE connection to another node.

Example:

```json
{
  "id": "1",
  "operation": "connection.open",
  "address": "192.0.2.10",
  "port": 8042
}
```

A successful response returns a connection identifier:

```json
{
  "id": "1",
  "ok": true,
  "result": {
    "connection_id": "7f90c317"
  }
}
```

The `connection_id` identifies this connection within the local node.

Applications should use the returned connection identifier for later operations rather than depending on the peer address as the unique identity of the connection.

This is important because more than one connection involving the same address may exist.

The `connection_id` is a string value with 8 characters.

Clients must treat it as an opaque string.

---

## 17. Connection Address

The initial version of `connection.open` accepts:

```text
address
port
```

separately.

For example:

```json
{
  "address": "192.0.2.10",
  "port": 8042
}
```

`address` may contain an IPv4 or IPv6 address.

Support for additional address forms, including names and future CR2SE addressing mechanisms, may be defined separately.

---

## 18. `connections.list`

`connections.list` returns the connections currently maintained by the local node.

Request:

```json
{
  "id": "2",
  "operation": "connections.list"
}
```

Example response:

```json
{
  "id": "2",
  "ok": true,
  "result": {
    "connections": [
      {
        "connection_id": "7f90c317",
        "address": "192.0.2.10",
        "port": 8042,
        "state": "connected"
      },
      {
        "connection_id": "93bf210a",
        "address": "192.0.2.11",
        "port": 8042,
        "state": "connected"
      }
    ]
  }
}
```

Additional metadata may be added to connection objects in future versions.

Clients must ignore fields they do not understand.

---

## 19. `connection.close`

`connection.close` asks the node to close an existing CR2SE connection.

Request:

```json
{
  "id": "3",
  "operation": "connection.close",
  "connection_id": "7f90c317"
}
```

Successful response:

```json
{
  "id": "3",
  "ok": true,
  "result": {}
}
```

Closing a CR2SE connection also terminates operations currently using that connection according to the CR2SE network protocol.

---

## 20. `connection.ping`

`connection.ping` checks whether communication with the remote node is operational.

Request:

```json
{
  "id": "4",
  "operation": "connection.ping",
  "connection_id": "7f90c317"
}
```

Example response:

```json
{
  "id": "4",
  "ok": true,
  "result": {
    "reachable": true
  }
}
```

Optionally, additional information may be added such as measured round-trip time.

The exact peer-level protocol used to implement ping must be defined by the relevant CR2SE peer protocol specification.

`connection.ping` describes the Node API operation, not the bytes exchanged between CR2SE peers.

---

# Remote Operations

Some Node API operations cause the local node to communicate with a connected remote node.

This distinction is important.

For example:

```text
connections.list
```

can be answered entirely by the local node.

In contrast, operations such as:

```text
board.get
service.get
service.invoke
```

require communication with another node.

Conceptually:

```text
Application
    |
    | board.get
    v
Local Node
    |
    | CR2SE request
    v
Remote Node
    |
    | CR2SE response
    v
Local Node
    |
    | Node API response
    v
Application
```

---

## 21. Board

A CR2SE node may offer services.

The **board** describes information about a node and the services it currently offers.

A board is represented as JSON.

The exact board schema is defined separately from this document.

The Node API treats the board as a JSON value and must not require clients to understand every possible service described by it.

This allows independently developed nodes to advertise services not known when this specification was written.

---

## 22. `board.get`

`board.get` asks a connected peer for its board.

Request:

```json
{
  "id": "5",
  "operation": "board.get",
  "connection_id": "7f90c317"
}
```

Example response:

```json
{
  "id": "5",
  "ok": true,
      "result": {
        "board": {
          "version": 1,
          "providedServices": [],
          "wantedServices": []
        }
      }
}
```

The value of `board` is the JSON board returned by the remote peer.

The Node API does not define the contents of the board beyond requiring the returned representation to be valid JSON.

The protocol used between peers to request and return the board must be standardized separately as part of CR2SE peer communication.

---

# Services

## 23. `service.get`

`service.get` asks a connected node for the complete definition of one service advertised on its Board.

Request:

```json
{
  "id": "6",
  "operation": "service.get",
  "connection_id": "7f90c317",
  "offering_id": "weather-current"
}
```

`offering_id` is the `id` of an entry in the remote peer's current Board. It is called an offering ID in the Board specification and is the service ID used for this lookup. The request needs only this ID because Board IDs are unique within one Board.

Example response:

```json
{
  "id": "6",
  "ok": true,
  "result": {
    "service_definition": {
      "id": "weather-current",
      "service": "example.weather.current",
      "serviceVersion": 1,
      "description": "Returns the current temperature for a location.",
      "input": {
        "type": "object",
        "fields": {
          "location": {
            "type": "string",
            "description": "Location whose current temperature is requested."
          }
        }
      },
      "output": {
        "type": "object",
        "fields": {
          "temperatureCelsius": {
            "type": "int32",
            "description": "Current temperature in whole degrees Celsius."
          }
        }
      },
      "check": {
        "description": "Repeat the observation using the same source. Return inconclusive if a comparable observation is unavailable.",
        "input": {
          "type": "object",
          "fields": {}
        },
        "output": {
          "type": "object",
          "fields": {
            "outcome": {
              "type": "string",
              "description": "Verification outcome: pass, fail, or inconclusive."
            }
          }
        }
      }
    }
  }
}
```

The value of `service_definition` is the definition specified by [Services.md](./Services.md). Its `id`, service identifier, version, and description must match the current Board entry. Its `input`, `output`, and `check` fields contain the logical types and semantic field descriptions; these fields are never embedded in the Board.

The operation applies to both `providedServices` and `wantedServices`. A publisher must return the definition for every entry on its current Board so an unfamiliar requester or provider can understand the advertised contract.

If `offering_id` is not on the current Board, the operation fails with error code `service_not_found`. A client that receives a definition inconsistent with its cached Board must not use it; it should refresh the Board and repeat selection.

The peer protocol used to retrieve the definition must be standardized separately as part of CR2SE peer communication.

---

## 24. Services Are Extensible

CR2SE must allow nodes to provide services that are not built into the CR2SE specification.

For example, one node might provide information, computation, storage, search, messaging, or another service.

CR2SE must not require every possible service to become a new Node API operation.

Therefore service invocation is generic.

The flow is:

```text
Application
    |
    | service.invoke
    v
Local Node
    |
    | CR2SE service request
    v
Remote Node
    |
    | service implementation
    v
Remote Node
    |
    | result
    v
Local Node
    |
    | Node API response
    v
Application
```

---

## 25. Service Identification

An offering in a peer's Board provides three identifiers relevant to invocation:

```text
offering ID
service identifier
service version
```

Their exact meaning is defined by the Board and Services specifications.

For example:

```json
{
  "offering_id": "weather-current",
  "service": "example.weather.current",
  "service_version": 1
}
```

The offering ID and service identifier are treated as opaque strings by the Node API. The version is a positive integer.

All three values are supplied so the remote peer can reject a stale or inconsistent selection. An invocation must not select only a service identifier because one Board may advertise several offerings of the same service version with different terms.

---

## 26. `service.invoke`

`service.invoke` asks a connected node to execute one of its advertised services.

Example:

```json
{
  "id": "6",
  "operation": "service.invoke",
  "connection_id": "7f90c317",
  "offering_id": "weather-current",
  "service": "example.weather.current",
  "service_version": 1,
  "arguments": {
    "location": "New York"
  }
}
```

The selected Board offering determines the credit issuer, price, preconditions, and offering-specific terms. Its separately retrieved service definition determines the input, output, and check contract. The remote peer must reject the invocation if those identifiers do not select the same currently advertised offering.

The `arguments` field may contain any valid JSON value accepted by that service.

For example, another service could accept:

```json
{
  "document": "example",
  "limit": 20,
  "options": {
    "include_metadata": true
  }
}
```

CR2SE does not define the contents of `arguments` for custom services.

The service itself defines them.

---

## 27. Service Results

A successful service invocation returns the service result as JSON.

For example:

```json
{
  "id": "6",
  "ok": true,
  "result": {
    "service_result": {
      "temperature": 21.4,
      "unit": "celsius"
    }
  }
}
```

`service_result` may be any valid JSON value.

For example:

```json
"hello"
```

is valid.

So is:

```json
42
```

and:

```json
[
  {
    "name": "result 1"
  },
  {
    "name": "result 2"
  }
]
```

A service's separately retrievable definition must document the structure and semantic meaning of its arguments and result.

---

## 28. Large Service Results

The JSON Node API is intended primarily for control operations and structured results.

Large binary resources must not be embedded directly into very large JSON values.

CR2SE already provides streaming mechanisms for transferring large data between peers.

The mechanism by which a service result references or exposes a large transferred resource will be defined separately.

### TODO: Large Results

Define how Node API operations expose:

* large binary responses;
* streamed responses;
* file transfers;
* progress information;
* cancellation.

---

# Multiple Local Nodes

## 29. Multiple Instances

A machine may run multiple independent CR2SE nodes simultaneously.

This is useful for testing and is also a valid deployment configuration.

Each node must therefore have its own Node API endpoint.

For example:

```text
CR2SE Node A
Node API: 127.0.0.1:39471

CR2SE Node B
Node API: 127.0.0.1:39472

CR2SE Node C
Node API: 127.0.0.1:39473
```

Clients select the node they intend to control by connecting to its Node API endpoint.

CR2SE does not require a machine to have one distinguished or globally canonical local node.

---

## 30. Endpoint Configuration

An implementation must provide a way to configure the Node API port when starting a standalone node.

The exact command-line syntax or configuration mechanism is implementation-specific.

Conceptually:

```text
start node with Node API on port 39471
```

is sufficient.

CR2SE standardizes the resulting behavior, not the user interface used to start the process.

---

# Embedded and IPC Equivalence

## 31. Equivalent Semantics

Embedded and IPC access must expose equivalent operations.

For example, these two conceptual operations mean the same thing:

```text
embedded:

connection.open(
    address = "192.0.2.10",
    port = 8042
)
```

and:

```json
{
  "id": "1",
  "operation": "connection.open",
  "address": "192.0.2.10",
  "port": 8042
}
```

The first is a direct call.

The second is the standardized IPC representation.

They must result in the same logical node operation.

This rule applies to every standardized Node API operation.

---

## 32. JSON Is Not Required Internally

An embedded implementation does not need to construct or parse JSON simply to use the Node API internally.

For example:

```text
Application
    |
    | native values
    v
Embedded CR2SE implementation
```

is valid.

JSON is the standardized representation for communication across the local IPC boundary.

This distinction avoids unnecessary serialization when CR2SE is embedded while preserving interoperability between independently implemented processes.

---

# Extensibility

## 33. Additional Fields

Future CR2SE versions may add fields to requests, responses, connection descriptions, errors, and other JSON objects.

Clients must ignore fields they do not understand unless a specification explicitly states otherwise.

For example, a future node might return:

```json
{
  "connection_id": "7f90c317",
  "address": "192.0.2.10",
  "port": 8042,
  "state": "connected",
  "latency_ms": 12,
  "peer": {
    "id": "..."
  }
}
```

A client that understands only:

```text
connection_id
address
port
state
```

must still be able to process the object.

---

## 34. Unknown Operations

A node receiving an operation it does not support must return an error.

For example:

```json
{
  "id": "81",
  "operation": "something.unknown"
}
```

may produce:

```json
{
  "id": "81",
  "ok": false,
  "error": {
    "code": "unknown_operation",
    "message": "The requested operation is not supported."
  }
}
```

The IPC connection should remain usable after an unknown but otherwise well-formed request.

---

## 35. Malformed Messages

If a complete newline-delimited message is not valid JSON, the node cannot reliably obtain a request ID.

The node may return:

```json
{
  "id": null,
  "ok": false,
  "error": {
    "code": "invalid_request",
    "message": "The message is not valid Node API JSON."
  }
}
```

A malformed application request should not normally require closing the IPC connection.

An implementation may close the connection when continuing would be unsafe, when framing limits are exceeded, or when repeated malformed input indicates a defective client.

---

## 36. Message Size Limit

Node API implementations must enforce a configurable maximum JSON message size.

This prevents a defective or malicious local client from causing unbounded memory allocation by sending an arbitrarily large message without a terminating newline.

The standard default limit remains to be defined.

### TODO: Node API Message Limit

Define:

* required minimum supported message size;
* recommended default maximum;
* error behavior when the maximum is exceeded.

---

# Security

## 37. Local Does Not Mean Trusted

The Node API controls a CR2SE node.

Depending on future CR2SE functionality, this may allow an application to:

* create network connections;
* disconnect peers;
* invoke remote services;
* initiate transfers;
* spend credits or other resources;
* access information available to the node.

Therefore a Node API implementation must not assume that every process capable of reaching its TCP port should automatically have unrestricted access.

Version 1 initially relies on loopback isolation, but a local authorization mechanism must be defined before the Node API is considered suitable for environments where untrusted local processes may exist.

### TODO: Local Authentication

Define a portable mechanism for authenticating Node API clients.

The mechanism should work with:

* standalone nodes;
* multiple node instances;
* command-line clients;
* graphical applications;
* automated local applications.

Until local authentication is defined, Node API servers must bind only to loopback addresses by default.

---

# Versioning

## 38. Node API Version

The Node API must have a version independent from the CR2SE network frame version.

Changes to the peer network protocol do not necessarily require changes to the Node API, and changes to the Node API do not necessarily require changing network framing.

The exact Node API version negotiation mechanism remains to be defined.

### TODO: Version Negotiation

Define:

* how a client discovers the Node API version;
* how incompatible versions are reported;
* whether requests explicitly contain a version;
* compatibility rules between minor extensions.

---

# Initial Operation Registry

## 39. Version 1 Operations

The initial Node API defines the following operations:

| Operation          | Scope  | Purpose                                           |
| ------------------ | ------ | ------------------------------------------------- |
| `connection.open`  | Local  | Establish a connection to another CR2SE node      |
| `connections.list` | Local  | List connections maintained by this node          |
| `connection.close` | Local  | Close an existing CR2SE connection                |
| `connection.ping`  | Remote | Check communication with a connected peer         |
| `board.get`        | Remote | Retrieve a connected peer's board                 |
| `service.get`      | Remote | Retrieve a definition by its Board offering ID    |
| `service.invoke`   | Remote | Invoke a service advertised by a connected peer   |

"Local" means the operation can be handled using state owned by the local node.

"Remote" means completing the operation normally requires communication with another CR2SE node.

---

# Complete Example

## 40. Example Session

Assume a CR2SE node exposes its Node API at:

```text
127.0.0.1:39471
```

An application opens one TCP connection to that endpoint.

It sends:

```json
{"id":"1","operation":"connection.open","address":"192.0.2.10","port":8042}
```

The node responds:

```json
{"id":"1","ok":true,"result":{"connection_id":"7f90c317"}}
```

The application lists connections:

```json
{"id":"2","operation":"connections.list"}
```

The node responds:

```json
{"id":"2","ok":true,"result":{"connections":[{"connection_id":"7f90c317","address":"192.0.2.10","port":8042,"state":"connected"}]}}
```

The application asks the remote node for its board:

```json
{"id":"3","operation":"board.get","connection_id":"7f90c317"}
```

The node performs the corresponding CR2SE peer communication and returns:

```json
{"id":"3","ok":true,"result":{"board":{"version":1,"providedServices":[{"id":"weather-current","service":"example.weather.current","serviceVersion":1,"description":"Returns the current temperature for a location.","creditIssuer":"ALICE_ID","price":1}],"wantedServices":[]}}}
```

After inspecting the Board, the application retrieves that service's complete definition by its Board ID:

```json
{"id":"4","operation":"service.get","connection_id":"7f90c317","offering_id":"weather-current"}
```

The remote node returns the typed contract separately from the Board:

```json
{"id":"4","ok":true,"result":{"service_definition":{"id":"weather-current","service":"example.weather.current","serviceVersion":1,"description":"Returns the current temperature for a location.","input":{"type":"object","fields":{"location":{"type":"string","description":"Location whose current temperature is requested."}}},"output":{"type":"object","fields":{"temperatureCelsius":{"type":"int32","description":"Current temperature in whole degrees Celsius."}}},"check":{"description":"Repeat the observation using the same source. Return inconclusive if a comparable observation is unavailable.","input":{"type":"object","fields":{}},"output":{"type":"object","fields":{"outcome":{"type":"string","description":"Verification outcome: pass, fail, or inconclusive."}}}}}}}
```

After validating the definition against the Board entry, the application invokes the service:

```json
{"id":"5","operation":"service.invoke","connection_id":"7f90c317","offering_id":"weather-current","service":"example.weather.current","service_version":1,"arguments":{"location":"New York"}}
```

The local CR2SE node sends the service request to the connected peer.

The result is returned through the Node API:

```json
{"id":"5","ok":true,"result":{"service_result":{"temperatureCelsius":21}}}
```

The application checks the connection:

```json
{"id":"6","operation":"connection.ping","connection_id":"7f90c317"}
```

Response:

```json
{"id":"6","ok":true,"result":{"reachable":true}}
```

Finally:

```json
{"id":"7","operation":"connection.close","connection_id":"7f90c317"}
```

Response:

```json
{"id":"7","ok":true,"result":{}}
```

All of these operations occur over the same persistent local Node API connection.

---

# Summary

The CR2SE Node API provides a language-independent boundary between applications and a CR2SE node.

Its main rules are:

```text
Logical operations
        |
        +---- Embedded access
        |
        +---- Local IPC
                |
                +---- loopback TCP
                +---- persistent connection
                +---- UTF-8
                +---- JSON
                +---- one JSON object per line
                +---- request IDs
                +---- concurrent requests
```

Embedded applications use the same logical operations without requiring IPC or JSON serialization.

Standalone nodes expose the standardized local IPC representation, allowing independently implemented applications to control independently implemented CR2SE nodes.

Remote functionality is exposed through generic operations such as `service.get` and `service.invoke`, so CR2SE nodes may advertise, describe, and implement new services without requiring every service to become part of the Node API specification.

The Node API defines how an application asks its local node to perform an operation.

The CR2SE peer protocols define how nodes communicate with each other to perform that operation.
