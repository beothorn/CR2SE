# Identity diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant App as Local application
    participant Keys as Key store
    participant Peer as Remote node
    App->>Keys: Generate independent Ed25519 and X25519 pairs
    Keys->>Keys: Derive ID and sign encryption-key binding
    Keys-->>App: Public identity and protected private-key handles
    App->>Peer: Connect with expected identity
    Peer-->>App: Fresh signed handshake proof
    App->>App: Verify key-derived ID and proof
    Note over App,Peer: Authentication grants no trust or credits
```
