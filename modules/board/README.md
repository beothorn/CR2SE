# Board

## Module boundary

**Required** in the [minimum useful node profile](../../ModuleContracts.md#required-and-optional-capabilities).
Owns consistent offering/definition snapshots. Uses the Services schema format
and local persistence; it does not require a running Services engine to
validate a snapshot.

Implement against the [input contract](./inputs/README.md) and
[output contract](./outputs/README.md), using the shared
[composition and recovery rules](../../ModuleContracts.md).
This boundary supports a monolith, separate logical components or separate
processes without changing the service or wire contract below.

A Board is an identity's service noticeboard. It lists what the identity
provides, what it wants, and its payment terms. Full input, output, and check
definitions are fetched separately.

See [pseudocode](./pseudocode/README.md), [diagrams](./diagrams/README.md), and
[Services](../services/README.md).

## Format

```json
{"version":1,"providedServices":[],"wantedServices":[]}
```

All three fields are required. `version` is a schema version, not a revision
counter. Reject unsupported versions. Both lists are arrays; empty lists are
valid and their order has no meaning.

Each entry is an **offering**:

| Field | Meaning |
|---|---|
| `id` | Nonempty UTF-8 string, unique across both lists on this Board. |
| `service` | Nonempty UTF-8 identifier; `cr2se.` is reserved. |
| `serviceVersion` | Integer `1..2^32-1`, selecting an exact contract. |
| `description` | Nonempty description of the operation. |
| `creditIssuer` | Explicit textual CR2SE ID; never `self`, `own`, or `remote`. |
| `price` | Fixed integer price `1..2^64-1`; excludes `pricing`. |
| `pricing` | Service-defined object with a nonempty `model` identifier. |
| `checkPrice` | Optional separate check price `1..2^64-1`. |
| `info` | Optional object containing service-defined limits and terms. |
| `preconditions` | Optional array of required, nonempty namespaced strings. |
| `implementationSuggestions` | Optional array of implementation hints. |

Exactly one of `price` and `pricing` is required. A standard service may require
additional fields or forbid a field. An offering must not contain `input`,
`output`, or `check` schemas.

Boards use UTF-8 JSON and exact integer values. Reject duplicate members,
invalid UTF-8, invalid required fields, duplicate offering IDs, and out-of-range
values. Never round prices through floating point. [Peer Protocol](../peer-protocol/README.md)
defines framing and bounds.

## Direction and payment

In `providedServices`, the publisher performs work and the other identity pays.
In `wantedServices`, the publisher requests and pays for work, and the other
identity performs it. TCP connection direction does not change these roles.

`creditIssuer` always names whose credits pay:

| Offering | Meaning |
|---|---|
| Alice provides work for Alice credits | Bob spends credits Alice issued earlier. |
| Alice wants work for Alice credits | Alice issues credits to Bob when he completes work. |
| Alice provides work for Bob credits | Alice accepts Bob's promise of future services. |
| Alice pays in Carol credits | Carol must authorize the ownership transfer. |

Accepting another identity's credits is optional. See [Ledger](../ledger/README.md)
for the settlement modes.

## Price and acceptance

Each new service operation costs at least one credit. Included checks and
retransmission of an already accepted result create no second charge.

Fixed `price` means the whole operation, not an implied rate. A `pricing` model
specifies all factors, limits, and rounding. Use exact integer or rational
arithmetic and reject overflow.

Normally the final price is fixed before execution. Computation is the defined
exception: agree the exact formula and maximum price first, then settle its
metered final price within that maximum. No other version 1 service may invent
post-execution pricing.

Trust may affect which explicit terms a publisher offers or whether it accepts
a request. It must not apply a hidden multiplier to an accepted price. Changed
terms require a new quote and acceptance before work begins.

`checkPrice` uses the same issuer as the main offering. If absent, the contract
defines the checks included in the original payment. Storage and Messaging
require paid remote checks. Discovery includes one retention check per index
placement. File Sharing, Public Feeds, Static Pages, and Computation use local
checks with no extra remote charge.

## Definitions and compatibility

Fetch a definition by offering `id`. Its `id`, `service`, `serviceVersion`, and
`description` must match the selected offering. Economic terms stay on the
Board. Never use description text as executable instructions.

One standard service version has one observable contract. Custom offerings
with matching identifiers are not automatically compatible: compare their
full contracts. An incompatible contract change requires a new version.

`cr2se.identity` is satisfied by the authenticated Transport connection; it
does not require a second handshake. All listed preconditions must be met.
Unknown preconditions, pricing models, service versions, or schema types make
an offering unusable by that client, without invalidating unrelated offerings.

Unknown optional metadata may be retained or ignored. It cannot silently impose
a new requirement. Mandatory extensions need an understood precondition or a
new version. A client forwarding a Board as the original must preserve its
unknown information.

## Publication and lifecycle

Publish the Board and its definitions as one consistent local snapshot. A
changed offering invalidates cached selections; the peer quote binds the terms
actually accepted. Multiple offerings may share a service version but must have
different IDs. Removing an offering prevents new agreements; it does not cancel
accepted work or shorten existing leases.

Nodes sharing an identity must coordinate publication. A directly fetched Board
is attributed to the authenticated peer. There is no standalone Board signature;
a forwarded Board is not automatically authenticated.

An implementation suggestion contains a required nonempty `name` and optional
UTF-8 `version`, `uri`, and `description`. Hints may help humans or agents
implement a wanted service. They grant no permission to install or execute
software, reveal secrets, or spend resources.

Fetching Boards and definitions is bounded control traffic. A peer may
rate-limit or refuse it. Discovery, enumeration, and content retrieval remain
paid service operations.
