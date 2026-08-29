# CR2SE Computation

CR2SE Computation is a standard, paid service for executing requester-supplied
source code for a bounded amount of time and returning the value produced by
that execution when one is produced.

The requester selects a programming language, an exact language version, the
source code, and a maximum execution time. Before execution, the requester
accepts the greatest price that the execution can cost. A computation that
finishes sooner costs less, subject to the offering's minimum price. A
computation stopped at the maximum execution time produces no computation
result but still costs the agreed maximum price.

An **accepted invocation** is a request that the provider has validated and
agreed to execute under an agreed maximum price. A **computation result** is the
value produced by successfully evaluating its source code. It is distinct from
a **completion record**, which reports how an accepted invocation ended and how
many credits were charged. Every accepted invocation that reaches a defined
completion outcome returns a completion record, including an invocation that
reaches its time limit without producing a computation result.

Execution of untrusted code is inherently dangerous. This specification does
not require a sandbox and does not define process isolation, operating-system
permissions, resource isolation other than elapsed time, network access,
filesystem access, confidentiality, or protection from malicious code. Those
decisions, and their consequences, belong entirely to each implementation.

Common terms such as **identity**, **service requester**, **service provider**,
**offering**, **credit issuer**, **check**, and **trust** are defined in the
[CR2SE Glossary](./Glossary.md). The common service rules are defined in
[Services](./Services.md), and Board advertisements are defined in
[Board](./Board.md).

---

## 1. Version 1 service

The version 1 Computation service is identified by:

```text
service:        cr2se.computation
serviceVersion: 1
pricing model:  cr2se.computation.v1
```

One invocation performs one evaluation of one source-code string. Version 1
does not define jobs that can be paused, resumed, or queried after the
invocation ends.

Computation version 1 is a bounded metered service. The bound is agreed before
execution; the final price is calculated from the measured execution time. This
is a deliberate Computation-specific exception to the common rule that an exact
final service price is known before execution. The exact credit issuer, pricing
formula, and maximum possible price are still known and accepted before any
code is executed. No charge above that accepted maximum is permitted.

---

## 2. Runtime

A **runtime** is the provider's implementation of one programming language at
one version. A runtime is identified by the pair:

```text
(language, languageVersion)
```

`language` is a non-empty lowercase ASCII identifier. It may contain the
letters `a` through `z`, the digits `0` through `9`, full stops, hyphens, and
underscores. It must begin with a letter or digit. Examples are:

```text
javascript
python
lua
```

`languageVersion` is a non-empty UTF-8 string naming the exact version accepted
by the provider. It is compared byte for byte. A provider must not interpret an
unsupported version as a nearby version. Examples are:

```text
ECMAScript 2024
3.13.1
5.4.7
```

A **runtime pair** is the `language` and `languageVersion` pair. An offering
advertises every runtime pair that may be requested through that offering. The
request selects exactly one advertised pair.

Names alone do not grant access to any library, command, file, environment
variable, network endpoint, clock, random source, or host function. Such
facilities are implementation-defined. A requester that depends on a facility
outside the selected language specification can rely on it only by a separate
agreement with that provider.

### Source and evaluation

`source` is a UTF-8 string containing the code to evaluate. The selected
runtime parses and evaluates that string according to the selected language
version.

The observable value of evaluation is called the computation result. The
selected language version's standard string conversion converts that value to
a UTF-8 string. That string is called the **result text**. The conversion must
not depend on a provider's locale or user-interface preferences.

For `language = "javascript"`, the source is evaluated as JavaScript source
text and the value of its final evaluated expression is converted using the
ECMAScript `String` operation. A JavaScript source that evaluates `1+1`
therefore has the result text:

```text
2
```

If a language version has no defined evaluation value or standard string
conversion, it cannot be advertised by a version 1 Computation offering. A
convention in which the result is captured standard output is not
interchangeable with version 1 Computation's final evaluation value; it must be
defined as a custom service or by a later Computation version.

---

## 3. Time

`maxExecutionMilliseconds` is the maximum execution time selected by the
requester. It is an unsigned integer number of whole milliseconds.

An **execution clock** is a provider-local monotonic clock. A monotonic clock
does not move backward when civil time is corrected. Unix time and other wall
clocks must not be used to measure execution duration.

The provider starts the execution clock immediately before it gives the source
to the selected runtime. The provider stops the clock when the runtime first
does one of the following:

```text
produces an evaluation value;
reports a language-level execution error;
is stopped because the maximum execution time was reached.
```

Parsing, compilation, runtime startup, and language initialization performed
after the execution clock starts are included. Validation, price agreement,
queueing before the clock starts, and transmission of the completion record
after the clock stops are excluded.

The **measured milliseconds** are the whole milliseconds obtained by rounding
the measured duration upward and then taking at least one. A duration reported
as zero by a coarse clock and a duration greater than zero but no greater than
one millisecond therefore both produce one measured millisecond.

The **billed milliseconds** are:

```text
minimum(measured milliseconds, maxExecutionMilliseconds)
```

The provider must attempt to stop execution when the limit is reached. Exact
preemption at a millisecond boundary is not assumed. Provider work performed
after the limit because stopping is delayed cannot increase the billed
milliseconds or the price.

If the runtime and time-limit mechanism become observable together, the time
limit wins unless the provider observed the evaluation value strictly before
the limit. A value observed at or after the limit is discarded and the outcome
is `timeLimitReached`.

Time measurement cannot be verified exactly by a remote requester. A provider
may lie about it, and different conforming machines may take different amounts
of time to execute the same source. The bounded price prevents an unbounded
charge; trust remains the mechanism for deciding whether to use that provider
again.

---

## 4. Completion outcomes

An accepted computation ends with exactly one of these completion outcomes:

```text
result
    The runtime produced an evaluation value before the time limit. The
    completion record contains its result text.

timeLimitReached
    The maximum execution time was reached before an evaluation value was
    produced. The completion record contains no result text.

executionError
    The runtime reported a language-level error before the time limit. The
    completion record contains no result text and may contain diagnostic text.
```

All three are successful completions of the Computation service protocol and
are billable. `timeLimitReached` and `executionError` do not claim that the
requester's source computed its intended value.

A **service failure** is different. It means that the provider did not return a
valid completion record for an accepted invocation. A service failure is not
charged under the common service rules. Examples include provider process
failure, loss of the connection before the complete record is returned, and a
malformed record.

A provider rejection before acceptance is also not charged. Rejection is
permitted for unsupported runtimes, invalid input, insufficient accepted
credits, trust, capacity, security policy, or any other local policy.

This distinction makes a reached time limit unambiguous: it is not a service
failure, it returns a valid `timeLimitReached` completion record, and it is
charged.

---

## 5. Pricing representation

CR2SE credits are unsigned integers and fractional credits do not exist.
Execution rates nevertheless need to express values such as one credit per
thousand milliseconds. Computation therefore represents its time rate as an
exact fraction:

```json
{
  "numerator": 1,
  "denominator": 1000
}
```

The fraction fields are:

```text
numerator: uint64
    Number of credits in the rate. Range: 0 .. 2^64-1.

denominator: uint64
    Number of billed milliseconds covered by that rate.
    Range: 1 .. 2^64-1; zero is invalid.
```

The example means exactly one credit per one thousand billed milliseconds. The
fraction is a rate used in an integer price calculation. It is not a fractional
credit transfer.

`minimumPrice` is a `uint64` in the range `1 .. 2^64-1`. It is the smallest
final price of an accepted computation.

`executionTimeFactor` is the exact fractional rate per billed millisecond. Its
numerator may be zero. A zero numerator makes every accepted computation cost
`minimumPrice` while retaining the same time-limit behavior.

Floating-point values must not be used for these fields or for protocol price
calculation.

---

## 6. Offering limits and shape

The `info` object of an offering contains:

```text
minimumExecutionMilliseconds
    Smallest maxExecutionMilliseconds accepted by the offering.
    Range: 1 .. 2^64-1.

maximumExecutionMilliseconds
    Largest maxExecutionMilliseconds accepted by the offering.
    Range: 1 .. 2^64-1.

maximumSourceBytes
    Largest UTF-8 encoding of source accepted by the offering, measured in
    bytes. Range: 1 .. 2^64-1.

runtimes
    Non-empty array of runtime-pair objects supported by the offering.
```

The required relation is:

```text
minimumExecutionMilliseconds <= maximumExecutionMilliseconds
```

A complete version 1 provided or wanted offering has this form:

```json
{
  "id": "computation-standard",
  "service": "cr2se.computation",
  "serviceVersion": 1,
  "description": "Evaluate requester-supplied source code for a bounded time.",
  "creditIssuer": "PROVIDER_ID",
  "pricing": {
    "model": "cr2se.computation.v1",
    "minimumPrice": 1,
    "executionTimeFactor": {
      "numerator": 1,
      "denominator": 1000
    }
  },
  "preconditions": [
    "cr2se.identity"
  ],
  "info": {
    "minimumExecutionMilliseconds": 1,
    "maximumExecutionMilliseconds": 60000,
    "maximumSourceBytes": 1000000,
    "runtimes": [
      {
        "language": "javascript",
        "languageVersion": "ECMAScript 2024"
      }
    ]
  }
}
```

A version 1 Computation offering must use `pricing`; it must not use the fixed
Board `price` field. It must contain every pricing and `info` field shown above.
An offering may impose other Board preconditions using the common Board rules.

The provider must not advertise a runtime pair that it cannot execute with the
semantics defined in section 2.

---

## 7. Price calculation

Let:

```text
D = billed milliseconds
T = requested maxExecutionMilliseconds
F.n / F.d = executionTimeFactor
M = minimumPrice
```

In the formulas below, `ceil(value)` means the smallest integer greater than or
equal to `value`, and `max(left, right)` selects the greater value.

The final price is:

```text
finalPrice = max(M, ceil(D * F.n / F.d))
```

The maximum price accepted before execution is:

```text
maximumPrice = max(M, ceil(T * F.n / F.d))
```

Because `D <= T`, `finalPrice <= maximumPrice`.

For example, with one credit per thousand milliseconds and a minimum price of
one credit:

```text
T = 60000
maximumPrice = max(1, ceil(60000 / 1000)) = 60 credits
```

If the computation finishes after 1201 billed milliseconds:

```text
finalPrice = max(1, ceil(1201 / 1000)) = 2 credits
```

If it reaches the 60000 millisecond limit:

```text
finalPrice = maximumPrice = 60 credits
outcome = timeLimitReached
```

All inputs and final prices are unsigned integers. Implementations must use
arbitrary-precision integers or an equivalent overflow-safe algorithm. If
`maximumPrice` exceeds `2^64-1`, the request is invalid and must be rejected
before acceptance. An offering whose advertised maximum permits such overflow
is invalid.

For positive integers, an implementation may calculate a ceiling division as:

```text
ceil(a / b) = (a + b - 1) div b
```

provided the intermediate calculation cannot overflow.

### Price agreement and settlement

Before execution, both peers validate the request and independently calculate
`maximumPrice`. The provider must state that value, and the requester must
accept that exact value. Acceptance authorizes a final debit no greater than
`maximumPrice`; it does not debit the maximum in advance.

Before accepting, the provider must determine that the requester can pay
`maximumPrice` in the selected credits. Local accounting for concurrent
invocations must not allow the same available balance to authorize several
maximum prices that could not all be paid. When a completion record is
returned, only `finalPrice` is settled and the unused authorization ceases to
be reserved. The internal reservation mechanism is implementation-dependent.

After execution, the provider returns `billedMilliseconds` and `finalPrice` in
the completion record. Both peers recalculate the final price from the returned
billed duration and the accepted offering. A record whose price does not match
the formula or exceeds `maximumPrice` is invalid.

The provider may not bill queueing, result conversion, result transmission,
sandbox cleanup, delayed termination beyond the requested limit, or other work
outside the execution interval defined in section 3.

The measured duration originates at the provider and is therefore not proof of
actual resource use. A requester that considers it implausible may lower its
local trust in the provider. CR2SE defines no automatic refund or adjudication.

---

## 8. Invocation input

The logical input is:

```text
language:                 string
languageVersion:          string
source:                   string
maxExecutionMilliseconds: uint64
```

The provider validates all of the following before acceptance:

```text
language has the syntax defined in section 2;
the runtime pair appears in the selected offering;
the UTF-8 encoding of source is no larger than maximumSourceBytes;
maxExecutionMilliseconds is within the offering's minimum and maximum;
maximumPrice is representable as uint64;
the requester accepts the credit issuer and maximumPrice;
the requester satisfies the offering's preconditions and provider policy.
```

The source may be empty only if the selected language accepts empty source and
defines a result for it. A provider must reject invalid UTF-8 rather than
silently replacing bytes or interpreting another character encoding.

Source transmission occurs before execution and is not part of billed time.
The provider must enforce `maximumSourceBytes` while receiving it and must not
allocate memory based only on an unvalidated declared size.

---

## 9. Acceptance and execution

An invocation becomes **accepted** only after:

```text
the complete input has been received and validated;
the selected offering is still current and available;
both peers agree on the credit issuer and maximumPrice;
the provider commits to attempt this one execution.
```

Before acceptance the provider may reject the request without charge. After
acceptance the provider must start the selected runtime or return an uncharged
service failure.

The provider executes the source once. It must not silently retry an execution
after a runtime crash, because a second execution could repeat external side
effects or produce a different value. A requester may submit a new invocation,
but that is a new computation with its own acceptance and possible charge.

When an evaluation value is produced before the limit, the provider converts it
to result text and returns `result`. When the limit is reached first, the
provider stops or abandons the execution and returns `timeLimitReached`. When
the runtime reports a language-level error first, the provider returns
`executionError`.

The provider must prevent a stopped or abandoned execution from later changing
the completion record or adding charges. Whether the implementation can also
prevent that code from continuing to affect the host is an implementation
security responsibility, not a guarantee made by CR2SE.

---

## 10. Completion record

The logical completion record contains:

```text
outcome:            string
billedMilliseconds: uint64
price:              uint64 credits
result:             string, only for result
diagnostic:         string, optional and only for executionError
```

`outcome` is exactly `result`, `timeLimitReached`, or `executionError`.

For `result`, `result` is required and `diagnostic` is forbidden. An empty
result string is a valid computation result.

For `timeLimitReached`, both `result` and `diagnostic` are forbidden, and:

```text
billedMilliseconds = maxExecutionMilliseconds
price = maximumPrice
```

For `executionError`, `result` is forbidden. `diagnostic`, when present, is
untrusted UTF-8 text intended for a human or developer. Its wording and content
are not standardized and must not be parsed to determine the outcome.

For every outcome, `billedMilliseconds` must be in:

```text
1 .. maxExecutionMilliseconds
```

and `price` must equal the calculation in section 7.

Returning the completion record successfully authorizes both peers to apply the
final price to their local ledgers. A check is not required before charging.

---

## 11. Computation check

The version 1 check is independent re-execution by the requester or by a third
implementation chosen by the requester. It does not ask the original provider
to execute the code again and has no additional CR2SE charge from that
provider.

The check uses the original:

```text
language;
languageVersion;
source;
maxExecutionMilliseconds;
completion record.
```

The checker executes the same source using the same runtime pair and time limit.
It then produces one of the common check outcomes:

```text
pass
    Both executions have outcome result and their result texts are byte-for-byte
    equal.

fail
    The requester established before checking that the source should be
    deterministic, both executions have outcome result, and their result texts
    are not byte-for-byte equal.

inconclusive
    Either execution has timeLimitReached or executionError, the selected
    runtime is unavailable to the checker, the check cannot be completed, or
    the result texts differ but the requester did not establish that the source
    should be deterministic.
```

A `pass` establishes only that two executions produced the same result text. It
does not prove that the source was safe, that either runtime was correct, that
the provider reported time honestly, or that the result satisfies the
requester's larger purpose.

Computations may read time, randomness, files, networks, mutable state, or other
implementation-defined inputs. They may also contain undefined or
implementation-dependent language behavior. Re-execution of such a computation
can legitimately produce a different result. The local trust decision always
belongs to the requester.

The original provider is not required to retain source or results after the
completion record has been delivered. A requester that may perform a check must
retain the original input and output itself.

---

## 12. Required service definition

Every version 1 Computation offering must expose a service definition through
`service.get`. Its `id` and `description` match the selected Board offering. Its
logical schema is equivalent to:

```json
{
  "id": "computation-standard",
  "service": "cr2se.computation",
  "serviceVersion": 1,
  "description": "Evaluate requester-supplied source code for a bounded time.",
  "input": {
    "type": "object",
    "fields": {
      "language": {
        "type": "string",
        "description": "Lowercase identifier of the programming language to execute."
      },
      "languageVersion": {
        "type": "string",
        "description": "Exact advertised version of the selected programming language."
      },
      "source": {
        "type": "string",
        "description": "UTF-8 source code evaluated by the selected runtime."
      },
      "maxExecutionMilliseconds": {
        "type": "uint64",
        "description": "Requester-selected maximum execution time in whole milliseconds."
      }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "outcome": {
        "type": "string",
        "description": "Completion outcome: result, timeLimitReached, or executionError."
      },
      "billedMilliseconds": {
        "type": "uint64",
        "description": "Whole execution milliseconds used to calculate the final price."
      },
      "price": {
        "type": "uint64",
        "description": "Final credits charged for this completed computation."
      },
      "result": {
        "type": "string",
        "description": "Runtime-defined UTF-8 result text; present only when outcome is result.",
        "optional": true
      },
      "diagnostic": {
        "type": "string",
        "description": "Unstandardized runtime diagnostic; permitted only when outcome is executionError.",
        "optional": true
      }
    }
  },
  "check": {
    "description": "Independently execute the original source with the same runtime pair and time limit, then compare result text when both executions return a result.",
    "input": {
      "type": "object",
      "fields": {
        "language": {
          "type": "string",
          "description": "Language from the checked invocation."
        },
        "languageVersion": {
          "type": "string",
          "description": "Exact language version from the checked invocation."
        },
        "source": {
          "type": "string",
          "description": "Source from the checked invocation."
        },
        "maxExecutionMilliseconds": {
          "type": "uint64",
          "description": "Maximum execution time from the checked invocation."
        },
        "originalOutcome": {
          "type": "string",
          "description": "Outcome in the original completion record."
        },
        "originalResult": {
          "type": "string",
          "description": "Original result text; present only when originalOutcome is result.",
          "optional": true
        }
      }
    },
    "output": {
      "type": "object",
      "fields": {
        "outcome": {
          "type": "string",
          "description": "Verification outcome: pass, fail, or inconclusive."
        },
        "checkedOutcome": {
          "type": "string",
          "description": "Completion outcome produced by the independent execution.",
          "optional": true
        },
        "checkedResult": {
          "type": "string",
          "description": "Result text produced by the independent execution, when it produced one.",
          "optional": true
        }
      }
    }
  }
}
```

An implementation may expose language-appropriate functions, processes, or
streaming APIs instead of this JSON shape. It must preserve the same logical
fields, exact integer ranges, UTF-8 values, validation rules, pricing, outcome
rules, and observable behavior.

---

## 13. Example interaction

Assume the offering in section 6. A requester asks:

```json
{
  "language": "javascript",
  "languageVersion": "ECMAScript 2024",
  "source": "1+1",
  "maxExecutionMilliseconds": 60000
}
```

Both peers calculate and accept a maximum price of 60 credits. If execution
takes one billed millisecond, the provider returns:

```json
{
  "outcome": "result",
  "billedMilliseconds": 1,
  "price": 1,
  "result": "2"
}
```

If it does not finish within one minute, the provider instead returns:

```json
{
  "outcome": "timeLimitReached",
  "billedMilliseconds": 60000,
  "price": 60
}
```

The second response is a valid, billable completion and contains no computation
result.

---

## 14. Concurrency, retries, and side effects

Different invocations are independent and may run concurrently. Providers must
limit concurrency according to their own capacity and security policy.

An invocation is not idempotent. Repeating the same input may repeat filesystem,
network, ledger-external, or other side effects and may produce a different
result. Neither a requester nor a provider may automatically retry an accepted
invocation unless the requester has separately established that doing so is
safe.

If the requester loses the completion record, CR2SE version 1 provides no
operation for recovering it and no global mechanism for deciding whether the
execution occurred. The peers' local ledgers may disagree. The requester may
submit a new invocation, but it is a separate execution and may be charged
separately.

---

## 15. Failure behavior

No valid completion record is returned, and no charge is permitted, for
conditions including:

```text
unsupported service or pricing version;
malformed fields;
invalid UTF-8;
unsupported or unadvertised runtime pair;
source larger than maximumSourceBytes;
time limit outside the offering's advertised range;
maximum-price overflow or disagreement;
insufficient accepted credits;
failed requester authentication or preconditions;
rejection by provider trust, capacity, or security policy;
provider inability to start the selected runtime;
provider failure before a complete completion record is returned.
```

A syntax error or language-level runtime error encountered after acceptance is
`executionError`, not a service failure. It returns a valid completion record
and is charged for its billed milliseconds.

A reached execution limit after acceptance is `timeLimitReached`, not a service
failure. It returns a valid completion record and is charged the maximum price.

CR2SE has no global adjudicator. A false result, implausible duration, incorrect
runtime, fabricated completion record, or disagreement about delivery may
inform local trust but does not automatically refund or reverse credits.

---

## 16. Security and implementation responsibility

### Provider responsibility

The provider decides whether and how to execute code. It may execute only code
from identities it trusts, reject all unknown identities, support only selected
runtimes, or refuse every request that exceeds a local risk threshold.

This specification does not require or certify:

```text
a container, virtual machine, process, interpreter, or hardware sandbox;
filesystem, network, memory, CPU, thread, or process isolation;
limits on memory, output size, subprocesses, or network traffic;
protection against denial of service, data theft, privilege escalation,
side channels, persistence, or compromise of the host;
safe interruption when the time limit is reached;
reproducible builds or trustworthy language runtimes.
```

These omissions do not make direct execution safe. A provider implementation is
responsible for every security decision and for damage caused by its choices.
Merely receiving a Board, retrieving a service definition, or receiving source
metadata must never execute the source.

An implementation should validate sizes before allocation, bound queues and
concurrency, avoid passing source through a command shell, use an explicit
runtime selection table, keep secrets out of the execution environment, and
assume that source and diagnostics are malicious. These are safety guidance,
not interoperable guarantees supplied by CR2SE.

### Requester responsibility

The requester must treat the result text and diagnostic text as untrusted. It
must not automatically execute a result, interpolate it into a command, render
it as trusted markup, deserialize it into unsafe native objects, or grant it
authority merely because it came from a trusted provider.

A computation result is not guaranteed. Code may be rejected, fail, time out,
depend on unavailable facilities, produce nondeterministic output, exploit an
implementation difference, or be executed dishonestly. Requesters choose
providers and decide how each observation affects local trust.

### Confidentiality

The provider receives the source in plaintext at the Computation service layer
and may inspect, log, copy, or retain it. CR2SE transport encryption protects
data in transit but does not hide source from the provider that executes it.

The source may also disclose data through its result, diagnostics, timing,
network activity, or other side effects. Computation version 1 provides no
confidential-computing guarantee and no proof that source or intermediate state
was deleted after execution.

---

## 17. Interoperability checklist

A version 1 implementation is interoperable only if it:

```text
uses service cr2se.computation at serviceVersion 1;
uses pricing model cr2se.computation.v1;
advertises exact supported runtime pairs and matches them byte for byte;
accepts source as UTF-8 and enforces maximumSourceBytes;
measures the defined execution interval with a monotonic clock;
rounds measured time upward to whole milliseconds;
never bills more than maxExecutionMilliseconds;
uses exact, overflow-safe ceiling arithmetic for both prices;
agrees the credit issuer and maximum price before execution;
returns exactly one defined completion outcome after accepted execution;
omits result text for timeLimitReached and executionError;
charges the maximum price for timeLimitReached;
does not charge a pre-acceptance rejection or service failure;
does not silently retry an accepted execution;
exposes the required service definition and check;
treats all source, results, and diagnostics as untrusted input;
leaves sandboxing and other execution-security policy to the implementation.
```
