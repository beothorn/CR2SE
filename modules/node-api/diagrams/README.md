# Node API diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Client as Human client or agent
    participant Node as Local node
    participant Peer
    Client->>Node: session.open with version and capability token
    Node-->>Client: Limits and accepted API version
    Client->>Node: blob.create, bounded blob.write calls, blob.finish
    Node-->>Client: Finished session-owned blob handle
    Client->>Node: service.invoke with blob, issuer and maximum price
    Node->>Peer: Peer Protocol quote, acceptance and streamed input
    Peer-->>Node: Complete result
    Node-->>Client: service_result with output blob handle and final price
    Client->>Node: Bounded blob.read calls
    Node-->>Client: Base64 chunks and eof
    Client->>Node: blob.close
```
