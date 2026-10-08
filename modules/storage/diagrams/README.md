# Storage diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Owner
    participant A as Provider A
    participant B as Provider B
    Owner->>Owner: Encrypt private data and hash exact stored bytes
    Owner->>A: Agree store price and upload bytes
    A->>A: Validate hash and durably create lease
    A-->>Owner: Lease ID, acceptance and expiration, price
    Owner->>B: Independently agree and store a replica
    B-->>Owner: Independent lease ID and expiration
    Owner->>Owner: Back up keys and recovery catalog
    Owner->>A: Paid unpredictable byte challenge
    A-->>Owner: Byte evidence
    Owner->>Owner: Compare with locally held expected byte
    alt Provider A unavailable
        Owner->>B: Paid range retrieval under current terms
        B-->>Owner: Exact stored bytes
    else Renewal desired
        Owner->>A: Renew with expectedExpiresAt and agreed current price
        A-->>Owner: Atomically extended expiration
    end
```
