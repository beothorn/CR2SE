# Computation diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Requester
    participant Provider
    participant Runtime as Locally authorized runtime
    Requester->>Provider: Runtime pair, source metadata and time limit
    Provider-->>Requester: Exact rate and maximum price
    Requester->>Provider: Accept maximum and send complete source
    Provider->>Provider: Validate input and reserve maximum
    Provider->>Runtime: Start evaluation and monotonic timer
    alt Value observed before limit
        Runtime-->>Provider: Evaluation value
        Provider->>Provider: Convert result and calculate metered price
    else Limit wins
        Provider->>Runtime: Stop execution
        Provider->>Provider: timeLimitReached at maximum price
    else Language error before limit
        Runtime-->>Provider: Execution error
        Provider->>Provider: executionError at metered price
    end
    Provider-->>Requester: Billable completion record
    Provider->>Provider: Settle final price and release unused reservation
    Requester->>Requester: Optional independent safe re-execution check
```
