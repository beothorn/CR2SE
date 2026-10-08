# Public File Sharing diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Reader
    participant Discovery
    participant A as Host A
    participant B as Host B
    Reader->>Discovery: Paid locateShare by manifest hash
    Discovery-->>Reader: Signed availability records
    Reader->>A: Paid manifest request with size and spending bounds
    A-->>Reader: Canonical manifest
    Reader->>Reader: Verify share ID, safe paths and piece hashes
    par Fetch first range
        Reader->>A: Paid consecutive piece request
        A-->>Reader: Piece bytes
    and Fetch another range
        Reader->>B: Independently paid piece request
        B-->>Reader: Piece bytes
    end
    Reader->>Reader: Verify each piece, then complete file hash
    Reader->>Reader: Publish files safely beneath selected local directory
```
