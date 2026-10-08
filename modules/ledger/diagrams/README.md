# Ledger diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Bob as New contributor Bob
    participant Alice as Community peer Alice
    Bob->>Alice: Read wanted offerings through bounded control exchange
    Bob->>Bob: Choose finite work and accept Alice credits
    Bob->>Alice: Offer to perform wanted work
    Alice->>Bob: Propose input and payment
    Bob-->>Alice: Quote bounded work
    Alice->>Bob: Accept and supply input
    Bob-->>Alice: Successful result
    Alice->>Alice: Issue Alice credits to Bob
    Bob->>Bob: Record owned Alice credits
    Alice->>Alice: Check contribution and choose nonzero trust in Bob
    Bob->>Alice: Request Alice service using earned credits
    Alice-->>Bob: Result, both reduce Bob's Alice-credit balance
```

```mermaid
sequenceDiagram
    participant Owner
    participant Issuer
    participant NewOwner as New owner
    Owner->>Issuer: Signed 121-byte order and maximum fee
    Issuer-->>Owner: Exact fee quote
    Owner->>Issuer: Accept fee
    Issuer->>Issuer: Atomically move net credits and record replay ID
    Issuer-->>Owner: Stored transfer result
    Owner->>Issuer: Retry same order after lost response
    Issuer-->>Owner: Same result without a second debit
    NewOwner->>Issuer: Query authorized transfer result
    Issuer-->>NewOwner: Authenticated accounting result
```
