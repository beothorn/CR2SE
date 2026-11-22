# Hosted Publications diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Publisher as Publisher (phone, outbound only)
    participant HostA as Host A
    participant HostB as Host B
    participant Reader
    Publisher->>Publisher: Sign resources, then the page manifest
    Publisher->>HostA: Paid store (resources, then page)
    Publisher->>HostB: Paid store (same signed bytes)
    HostA-->>Publisher: Durable placement
    HostB-->>Publisher: Durable placement
    Note over Publisher: Publisher goes offline
    Reader->>HostA: Paid list (page, newest first)
    HostA-->>Reader: Entries with sequence and hash
    Reader->>HostA: Paid get (manifest)
    Reader->>HostB: Paid get (resource by publication ID)
    Reader->>Reader: Verify signatures, hashes, manifest; choose highest sequence
```

```mermaid
sequenceDiagram
    participant Publisher
    participant Host
    participant Reader
    participant Stranger
    Publisher->>Publisher: Encrypt content once, wrap key per audience reader
    Publisher->>Host: Paid store restricted publication
    Reader->>Host: Paid get (audience member)
    Host-->>Reader: Signed envelope
    Reader->>Reader: Verify, unwrap content key, decrypt
    Stranger->>Host: Paid list / get
    Host-->>Stranger: Same result as for a missing item
```

```mermaid
sequenceDiagram
    participant Publisher
    participant Host
    Publisher->>Host: Remove with removalId and minimum release
    Host-->>Publisher: Quote (releaseCredits, removePrice, issuer)
    Publisher->>Host: Accept
    Host->>Host: Remove placement, charge removePrice, apply releaseCredits once
    Host-->>Publisher: removed with exact output
    Publisher->>Host: Retry same removalId after a lost reply
    Host-->>Publisher: Identical output, no new charge
```
