# Messaging diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Sender
    participant Provider
    participant Recipient
    Sender->>Sender: Optionally encrypt, then sign exact message bytes
    Sender->>Provider: Paid store for recipient with retention period
    Provider-->>Sender: Durable pending placement
    Note over Sender,Recipient: Recipient may be offline during placement
    Recipient->>Provider: Paid discover for authenticated recipient
    Provider-->>Recipient: Pending placement metadata
    Recipient->>Provider: Signed recover request with fresh recoveryId
    Provider->>Provider: Atomically record recovery and cache complete result
    Provider-->>Recipient: Signed message, payload and recovery receipt
    Recipient->>Recipient: Verify sender and payload, decrypt if needed
    Recipient->>Provider: Retry identical recoveryId after lost response
    Provider-->>Recipient: Identical cached result without another charge
    Sender->>Provider: Paid status query
    Provider-->>Sender: Recipient authorization and provider receipt
```

```mermaid
sequenceDiagram
    participant Sender
    participant Provider
    Sender->>Provider: Remove pending placement with removalId and minimum release
    Provider-->>Sender: Exact removal price and releaseCredits quote
    Sender->>Provider: Accept both amounts
    Provider->>Provider: Atomically remove, debit price, issue release credits, cache result
    Provider-->>Sender: Stable removal result
    Sender->>Provider: Retry same removalId
    Provider-->>Sender: Same result with no additional ledger change
```
