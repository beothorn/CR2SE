# Static Pages diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Publisher
    participant Host
    participant Visitor
    Publisher->>Host: Locally publish static resource snapshot
    Visitor->>Host: Get canonical path with maximum bytes
    Host->>Host: Select one immutable content and metadata snapshot
    Host-->>Visitor: Fixed-price quote
    Visitor->>Host: Accept within spending budget
    Host-->>Visitor: Media type, size, content hash and exact bytes
    Visitor->>Visitor: Verify path, length, hash and price
    Visitor->>Visitor: Render under local content isolation policy
    Note over Visitor,Host: Each additional asset is a separate bounded paid retrieval
```
