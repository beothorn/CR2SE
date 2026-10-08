# Peer Protocol diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant R as Requester
    participant P as Provider
    R->>P: OPEN cr2se.peer version 1
    R->>P: propose with metadata and maximumPrice
    P-->>R: quote with quoteId and current terms
    R->>P: accept with hash of exact quote bytes
    R->>P: Detached body records in ID and offset order
    R->>P: input.end and Transport END
    P-->>R: result with output metadata and finalPrice
    P-->>R: Detached output body records
    P-->>R: result.end and Transport END
    Note over R,P: Records may cross frame boundaries, one exchange per stream
```

```mermaid
sequenceDiagram
    participant P as Prospective provider
    participant R as Wanted-offering publisher
    P->>R: OPEN and offer
    R->>R: Obtain input and authority from local application
    R->>P: propose as requester
    P-->>R: quote as provider
    R->>P: accept, input, input.end, END
    P-->>R: result, output, result.end, END
```
