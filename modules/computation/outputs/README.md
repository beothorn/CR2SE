# Computation outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Completion records

Results go to [Services](../../services/inputs/README.md), then through Peer
Control to the requester. Every completion contains `outcome:string`,
`billedMilliseconds:uint64` and `price:uint64`.

| Outcome | Additional fields / guarantee |
|---|---|
| `result` | Required UTF-8 `result`, including empty text; no diagnostic. Evaluation result is converted according to the selected runtime contract. |
| `executionError` | Optional bounded UTF-8 `diagnostic`; no result. Language-level failure is a billable completion. |
| `timeLimitReached` | Neither result nor diagnostic. Billed duration equals requested maximum and price equals accepted maximum. |
| Service failure | No completion or charge for invalid input, refused/unsupported runtime, inability to start or other explicit uncommitted protocol failure. A lost accepted attempt may instead be outcome unknown. |

For any completion, billed time is `1..maxExecutionMilliseconds`, price matches
the accepted formula and does not exceed the reserved maximum. Services/Ledger
settle that amount and release the remainder. The handler supplies retained
completion/effect references to local coordination; it never edits balances.

A local independent check returns pass/fail/inconclusive under the specification.
Matching result text permits pass; differing text permits fail only when
determinism was established. Errors, time limits or unavailable runtime are
inconclusive. This does not attest reported timing or program safety.

The service promises no remote job lookup or recovery after delivery. Internal
durable completion status prevents local duplicate execution and supports
settlement recovery; it does not create a new peer replay operation. External
effects of evaluated code cannot be rolled back by a Ledger transaction.

## Independent acceptance examples

- Fake runtime produces a result, language error and time limit; check exact
  outcome fields, ceiling price and maximum reservation release for each.
- Refuse an unadvertised language version before running any source.
- Lose a runtime/IPC reply after the attempt starts: recover its durable
  completion or uncertainty, without starting the same attempt again.
