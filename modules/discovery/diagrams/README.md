# Discovery diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Publisher
    participant Indexer
    participant Seeker
    participant Candidate as Referred indexer
    Publisher->>Publisher: Sign expiring address, share or trust record
    Publisher->>Indexer: Paid atomic index operation
    Indexer-->>Publisher: indexId, recordId and storedUntil
    Publisher->>Indexer: One included retention check
    Indexer-->>Publisher: Exact retained record bytes
    Seeker->>Indexer: Paid bounded lookup
    Indexer-->>Seeker: Signed records and candidate indexers
    Seeker->>Seeker: Verify signatures, time, ordering and lookup budget
    opt Existing trust and usable credits at candidate
        Seeker->>Candidate: Separate authenticated paid lookup
        Candidate-->>Seeker: More bounded evidence
    end
    Note over Seeker,Candidate: A referral grants no trust, credit or reachability
```
