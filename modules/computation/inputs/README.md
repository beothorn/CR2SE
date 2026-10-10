# Computation inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Optional in the minimum node. When enabled, Computation consumes authenticated
context, accepted metered terms and maximum reservation from
[Services](../../services/outputs/README.md). Its platform dependency is an
explicitly authorized runtime with timing, resource limits and attempt/result
journaling. It requires no Storage, Messaging, Discovery or Node API runtime.

## Accepted operations

| Input / source | Values and expectations |
|---|---|
| Evaluate / Services | `language:string`, `languageVersion:string`, `source:string`, `maxExecutionMilliseconds:uint64`. Select an exact advertised runtime pair; valid UTF-8 source within byte limit and duration within offering limits. No operation discriminator is added. |
| Accepted terms / Services | Exact `cr2se.computation.v1` pricing formula, issuer and maximum price, with maximum capacity reserved before execution. Use exact ceiling arithmetic, never floating-point pricing. |
| Runtime configuration / authorized local administrator | Permitted pairs, host facilities, concurrency and execution boundary. Peer descriptions cannot install a runtime or grant host access. |
| Runtime event / platform adapter | One correlated attempt, measured elapsed time, evaluation value/language error/time limit or host failure. Preserve the specification's evaluation/result-text convention; stdout is not an implicit substitute. |
| Local check / requester | Original input and completion record, same runtime pair and independent execution permission; prior determinism assessment where a mismatch is to count as failure. |

Receive and validate source before starting execution; source transfer is not
billed execution time. Persist attempt identity before running code. A failed
or lost runtime response cannot trigger automatic re-execution. Timeouts stop
or abandon the attempt under the runtime boundary and cannot later change the
record or add charges. Verification that needs another remote computation is a
new explicitly authorized paid invocation.
