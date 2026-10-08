# Board diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Client
    participant Publisher
    Client->>Publisher: board.get
    Publisher-->>Client: Compact provided and wanted offerings
    Client->>Client: Select supported version, issuer, pricing and preconditions
    Client->>Publisher: service.get by offering ID
    Publisher-->>Client: Input, output, behavior and check definition
    Client->>Client: Verify definition matches offering
    Client->>Publisher: Propose invocation with spending bound
    alt Terms still usable
        Publisher-->>Client: Exact current quote
        Client->>Publisher: Accept quoted snapshot
    else Contract changed
        Publisher-->>Client: terms_changed
        Client->>Client: Refresh selection without executing
    end
```
