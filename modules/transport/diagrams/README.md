# Transport diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant I as TCP initiator
    participant A as TCP acceptor
    I->>A: Open TCP connection
    I->>A: HELLO with public key, ephemeral key, nonce
    A->>I: HELLO with public key, ephemeral key, nonce
    I->>A: AUTH signature over role and both HELLOs
    A->>I: AUTH signature over role and both HELLOs
    Note over I,A: Verify signatures and derive directional keys and counters
    I->>A: Tagged OPEN stream 1 for cr2se.peer version 1
    I->>A: Tagged DATA records
    A->>I: Tagged DATA records
    I->>A: Tagged END for stream 1
    A->>I: Tagged END for stream 1
    Note over I,A: TCP remains open for other streams, content is visible
```

```mermaid
stateDiagram-v2
    [*] --> BothOpen: OPEN
    BothOpen --> LocalEnded: local END
    BothOpen --> RemoteEnded: remote END
    LocalEnded --> Closed: remote END
    RemoteEnded --> Closed: local END
    BothOpen --> Aborted: CANCEL or ERROR
    LocalEnded --> Aborted: CANCEL or ERROR
    RemoteEnded --> Aborted: CANCEL or ERROR
    Closed --> [*]
    Aborted --> [*]
```
