# Public Feeds diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant A as Publisher A
    participant Reader
    participant B as Publisher B
    A->>A: Locally sign and publish immutable messages
    B->>B: Locally sign and publish immutable messages
    Reader->>A: Paid read with selector, cursor and limit
    A-->>Reader: Own signed feed page
    Reader->>B: Independently paid read
    B-->>Reader: Own signed feed page
    Reader->>Reader: Verify identity, signatures, ordering and bounds
    Reader->>Reader: Deduplicate and merge by local display policy
    opt More messages within budget
        Reader->>A: Next paid page with exclusive cursor
        A-->>Reader: Next bounded page
    end
```
