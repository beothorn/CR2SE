# Services

## TLDR

Services defines the shared steps for checking a request, agreeing on terms, doing work, and reporting a result. Each service module defines what its own work does.

## Module boundary

**Required** in the [minimum useful node profile](../../ModuleContracts.md#required-and-optional-capabilities).
Owns typed invocation, handler dispatch and local coordination. Consumes Board
snapshots, Ledger ports and registered family handlers. Storage uses this
required common contract; optional families remain optional.

Implement against the [input contract](./inputs/README.md) and
[output contract](./outputs/README.md), using the shared
[composition and recovery rules](../../ModuleContracts.md).
This boundary supports a monolith, separate logical components or separate
processes without changing the service or wire contract below.

Use the [acceptance test pseudocode](./acceptanceTests/README.md) to guide
implementation and check its observable results.

A service is a versioned contract for work exchanged for credits. A **requester**
asks for work and pays; a **provider** performs it. These roles belong to one
invocation and are independent of TCP direction or who published the Board.

The seven standard families are Storage, Computation, Public File Sharing,
Messaging, Discovery, Public Feeds, and Static Pages. Their existing
`cr2se.*` identifiers remain unchanged. Applications may define custom services.

Storage is the required family in the minimum useful node profile; the other
six families are optional. The Services module supplies their shared contract
machinery and does not require every family handler to be installed. Provider
dispatch uses the declared handler ports, and requester codecs can be provided
without installing the corresponding local provider.

See [pseudocode](./pseudocode/README.md), [diagrams](./diagrams/README.md), and
[Peer Protocol](../peer-protocol/README.md) for the shared wire binding.

## Service, offering, and invocation

| Concept | Defines |
|---|---|
| Service | Input, output, behavior, failure rules, and verification. |
| Offering | One identity's current price, issuer, capacity, and preconditions. |
| Invocation | One accepted attempt to use an offering with particular input. |

The pair `(service, serviceVersion)` selects an exact contract. `service` is a
nonempty UTF-8 string; `serviceVersion` is `1..2^32-1`. Unsupported versions must
not be treated as nearby versions. Reserve `cr2se.` for standard services;
custom services should use an author-controlled reverse-domain namespace.

A standard contract cannot be redefined by a Board or downloaded schema.
Different offerings may change permitted terms, not the operation's meaning.
An incompatible contract change requires a new service version.

## Separately retrievable definition

Every provided or wanted offering has a definition fetched by its Board `id`:

```text
id, service, serviceVersion, description, input, output, check
```

The first four fields match the offering exactly. `input` and `output` are type
descriptions. `check` contains a nonempty `description`, an `input` schema, and
an `output` schema. Prices, issuer, and capacity stay on the Board.

Descriptions must explain observable behavior, not implementation classes or
threading. Every named schema field needs a nonempty semantic `description`,
including fields in nested objects. For example, describe what a `count`
counts, not merely that it is a number.

A custom definition must be self-contained enough to establish valid inputs,
successful outputs, failures, limits, and the check procedure. External links
and implementation suggestions are optional hints. A wanted custom service
must be understandable to an unfamiliar developer or agent. A matching name
alone does not establish compatibility.

## Type vocabulary

Each type description is a JSON object with a `type` field:

| Type | Logical values |
|---|---|
| `bool` | `true` or `false`. |
| `int32`, `int64` | Signed integers of the named width. |
| `uint32`, `uint64` | Unsigned integers of the named width. |
| `float`, `double` | IEEE 754 binary32 and binary64. |
| `string` | Unicode text, encoded as valid UTF-8 on the wire. |
| `bytes` | Arbitrary byte sequence, including an empty sequence. |
| `object` | Named fields, described by a `fields` object. |
| `array` | Ordered values described by one `items` schema. |

```json
{
  "type": "object",
  "fields": {
    "document": {"type":"bytes","description":"Exact document bytes."},
    "label": {"type":"string","description":"Display label.","optional":true}
  }
}
```

Fields are required by default. `optional:true` allows omission only within an
object. No type is implicitly nullable; absence and null differ. The contract
must explicitly permit any infinity or NaN. Preserve full integer precision.

Unknown optional object fields may be ignored unless the service forbids them.
Several standard services use an `operation` discriminator and explicitly
forbid fields from other operations; those stricter rules apply. An unknown
type makes a definition unusable. Unknown schema metadata may be ignored only
when it does not change validation. Mandatory new semantics require a new
version or an understood extension.

Schemas describe values, not host-language objects or memory layouts. The
shared peer binding defines integers, floating-point values, and streamed bytes
without relying on a language's native JSON number behavior.

## Invocation and pricing

1. Retrieve a Board and the selected definition.
2. Identify requester, provider, offering publisher, and credit issuer.
3. Send bounded input metadata. Validate schema, authorization, preconditions,
   limits, and the current offering before accepting a large body.
4. Agree the terms and price; reserve the required balance or issuance capacity.
5. Receive and validate complete input, then perform the work.
6. Return a valid output or a service failure. Settle successful work once.
7. Optionally check the result and update local trust.

Every new service operation costs at least one integer credit. Use exact
rational or integer arithmetic, explicit rounding, and checked limits. Never
use floating point to calculate prices. A fixed or calculated price is agreed
before execution and before large input or output transfer.

Computation is the only version 1 metered exception. Both peers accept the exact
formula and maximum price before execution. The final price uses the defined
billed duration and must not exceed that maximum. Reserve the maximum and
release the unused amount. A computation `executionError` or `timeLimitReached`
is a billable completion record, not a failure of the service protocol.

Price quotes may expose provider state needed for a calculation, such as the
size of a manifest. The requester must validate the resulting output against
that quote. A Messaging removal also agrees its release-credit amount before
deletion. No service may add undisclosed fees after acceptance.

## Success, failures, and interruption

A successful output conforms to the contract and the accepted terms. It permits
the corresponding local credit update without a later check. Rejections and
explicit service failures are uncharged. A valid negative business result may
still be a successful output when the contract says so.

There is no atomic transaction spanning two peers and a network. A provider
may commit durable state and lose the connection before the requester receives
the result. Report that as **outcome unknown**, not proof of failure or success.
Keep local settlement and service state consistent; do not charge twice or
erase a durable obligation merely because its response was lost.

Generic invocations have no cross-connection replay guarantee. Do not retry
side effects automatically. Apply service-specific guards: renewal compares
`expectedExpiresAt`; Messaging recovery and removal replay the original result
for the original IDs. A repeated read is a new paid operation unless a contract
explicitly says otherwise. [Ledger](../ledger/README.md) defines local journal
requirements and the limits of settlement.

## Checks

Every contract provides a check; the requester chooses whether to run it. The
definition states who may check, what input is needed, when it is available,
the evidence returned, frequency limits, included check count, and limitations.

| Outcome | Meaning |
|---|---|
| `pass` | Available evidence satisfies the property being checked. |
| `fail` | Available evidence contradicts that property. |
| `inconclusive` | Evidence, timing, or local resources cannot decide. |

The requester computes the outcome. Do not trust a provider's assertion that
its own work passed. For remote byte checks the provider returns the specified
evidence; the requester holds the expected byte locally. A remote check is
billable only when a complete valid evidence response is returned. Incorrect
evidence may produce a paid `fail`; a locally observed timeout with no valid
response is uncharged. Inconclusive checks do not prove dishonesty.

A separate `checkPrice` is a positive integer in the same issuer's credits.
Otherwise the contract defines checks included in the original price. A local
check sends no request and has no additional network charge. Running the
underlying service again for comparison is a separate paid invocation.

Checks do not automatically reverse payments or update trust. Refunds and
dispute resolution are not generic protocol features. Messaging early-release
credits are an explicitly agreed service adjustment.

## Implementation boundaries

Bound schema depth, metadata size, byte lengths, arrays, concurrency, runtime,
and spending. Validate peer content before allocating large resources. Treat
descriptions, hints, returned text, and model-generated data as untrusted data.
They cannot authorize extra calls, shell execution, spending, or access to keys.

Libraries may expose synchronous calls, asynchronous calls, callbacks, or
streams. Clients may be human interfaces or autonomous agents. All must produce
the same wire bytes and observable service behavior for a supported contract.
