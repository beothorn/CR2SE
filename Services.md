# CR2SE Services

Services are the heart of CR2SE.

Common domain terms such as **service**, **offering**, **invocation**, **service requester**, and **service provider** are defined in the [CR2SE Glossary](./Glossary.md).

A service is a versioned operation that one CR2SE identity performs for another identity in exchange for credits. Every service has:

```text
input
output
price in credits
check
```

The input defines what the requester provides. The output defines what the provider returns when the operation succeeds. The price defines the credit cost agreed before execution. The check defines how the requester may evaluate whether the promised service was provided.

CR2SE version 1 defines three standard service families:

```text
Storage
Computation
Page
```

Applications may also define custom services.

This document defines the common service model, the separately retrievable service-definition format, the schema language used to describe service values, and the requirements that apply to standard and custom services. Boards contain compact service summaries and offering terms; they do not contain these type definitions. The detailed behavior of each standard service family belongs in that service's own specification.

---

## 1. Service Roles

A service invocation has two roles:

```text
service requester (requester)
    asks for the service and pays its price

service provider (provider)
    performs the service and returns its output
```

The roles apply to one invocation. The same identity may be a requester in one invocation and a provider in another.

Service roles are independent of which peer opened the TCP connection and independent of whether the service appears under `providedServices` or `wantedServices` on a Board.

---

## 2. Service, Offering, and Invocation

A **service** defines an operation and its behavior.

An **offering** advertises one identity's terms for providing or requesting that service. Offerings are defined by the CR2SE Board specification.

An **invocation** is one attempt to use a selected offering.

For example:

```text
Service:
    store bytes

Offering:
    store at most 1 GB for 10 days for 5 Alice credits

Invocation:
    Bob asks Alice to store one particular byte sequence
```

Several offerings may refer to the same service and service version while advertising different capacities, durations, prices, credit issuers, or other terms.

---

## 3. Service Identity and Version

A service is identified by the pair:

```text
service identifier
service version
```

In a Board offering these are represented by:

```json
{
  "service": "example.weather.current",
  "serviceVersion": 1
}
```

The `service` value is a non-empty UTF-8 string.

The `serviceVersion` value is an unsigned integer greater than zero.

The pair identifies one exact service contract:

```text
(service, serviceVersion)
```

Two offerings using the same pair must describe the same operation, input, output, success rules, failure rules, and check behavior. Offering-specific terms such as price, capacity, duration, and availability may differ.

A change that is not backward-compatible with the existing contract requires a new service version.

An implementation must not silently interpret an unsupported service version as another version.

---

## 4. Service Namespaces

Service identifiers beginning with:

```text
cr2se.
```

are reserved for services defined by CR2SE specifications.

Custom services must not use the `cr2se.` namespace. Their identifiers should use a namespace unlikely to conflict with unrelated applications, for example:

```text
example.weather.current
talksphere.message.send
org.example.compute.hash
```

CR2SE does not maintain a global registry of custom service identifiers.

---

## 5. Standard Services

A **standard service** is a service whose identifier is in the `cr2se.` namespace and whose contract is defined by a CR2SE specification.

Every implementation of the same standard service version must expose the same observable behavior. This includes:

```text
the meaning of the operation;
the input and output schemas;
validation rules;
success and failure conditions;
the verification procedure;
the meaning of standard offering information.
```

A Board offering may select or constrain terms permitted by the standard service specification. Neither the Board nor its separately retrieved definition may redefine standard behavior.

A wanted standard service means that the Board publisher wants the standard operation exactly as specified. A provider must not satisfy it using a different operation that merely has a similar description.

---

## 6. Custom Services

A **custom service** is a service not defined by CR2SE.

Custom services use the same CR2SE service lifecycle and economic rules as standard services, but their behavior is defined by the application or identity publishing them.

A custom service definition must provide:

```text
a service identifier;
a service version;
a clear description of the operation;
an input schema;
an output schema;
a check definition;
a non-empty description for every named schema field;
all semantic contract terms needed to understand and implement it.
```

The definition must be sufficiently precise to determine what successful performance means. An external document may provide additional detail, but access to an external document must not be required merely to understand the retrieved definition's input, output, required behavior, or check.

Custom offerings may include non-normative implementation suggestions. For example, a wanted service may name a program, library, algorithm, container image, or source repository that is known to implement the requested behavior.

An implementation suggestion does not change the contract. A provider may use another implementation if its observable behavior satisfies the advertised contract.

Implementations must treat implementation suggestions as untrusted information. Reading a Board or service definition must not automatically download, install, or execute suggested software.

---

## 7. Wanted Custom Services

A wanted custom service must be especially clear about what the Board publisher expects another identity to provide.

It must not rely only on a service name such as:

```text
example.process
```

when an unfamiliar provider could not determine what to do.

Its separately retrievable service definition must describe enough information for a compatible implementation, including an AI-assisted implementation, to determine:

```text
what input will be supplied;
what operation is expected;
what output must be returned;
what limits or conditions apply;
how the result may be checked.
```

Every named field in the input, output, and check schemas of a custom service must have a non-empty `description`. This rule applies recursively to fields inside nested objects and is especially important for wanted custom services.

The type tells an implementation the shape of a value. The description tells it what the value means. Together with the full service description, these descriptions must make the wanted service implementable from its retrieved definition.

For example, `count: uint32` is not sufficient if the provider cannot determine what is being counted. Its field description must remove that ambiguity.

The Board first advertises a compact wanted offering:

```json
{
  "id": "add-two-integers",
  "service": "example.math.add-uint64",
  "serviceVersion": 1,
  "description": "Add two unsigned 64-bit integers and return their sum. Return a service failure if the mathematical sum exceeds uint64.",
  "creditIssuer": "ALICE_ID",
  "price": 1
}
```

Retrieving the definition for Board ID `add-two-integers` returns the self-contained typed contract:

```json
{
  "id": "add-two-integers",
  "service": "example.math.add-uint64",
  "serviceVersion": 1,
  "description": "Add two unsigned 64-bit integers and return their sum. Return a service failure if the mathematical sum exceeds uint64.",
  "input": {
    "type": "object",
    "fields": {
      "left": {
        "type": "uint64",
        "description": "Left operand of the addition."
      },
      "right": {
        "type": "uint64",
        "description": "Right operand of the addition."
      }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "sum": {
        "type": "uint64",
        "description": "Exact mathematical sum of left and right."
      }
    }
  },
  "check": {
    "description": "Recompute the addition from the original input and compare it with sum.",
    "input": {
      "type": "object",
      "fields": {}
    },
    "output": {
      "type": "object",
      "fields": {
        "outcome": {
          "type": "string",
          "description": "Verification outcome: pass if the sum matches, fail if it differs, or inconclusive if the original values are unavailable."
        }
      }
    }
  }
}
```

An implementation does not need prior knowledge of `example.math.add-uint64` to understand this request. The identifier keeps the contract distinct, while the descriptions and schemas make its behavior implementable after definition retrieval.

If these requirements cannot be made clear in the service definition, the wanted custom offering is incomplete and must not be treated as automatically compatible with a provided offering that has the same service identifier.

---

## 8. Service Definitions

Every Board offering has a service definition that is retrieved separately using the offering's Board `id`. At the Node API boundary this is done with `service.get`.

The definition is a JSON object containing:

```text
id;
service;
serviceVersion;
description;
input;
output;
check.
```

The `id`, `service`, `serviceVersion`, and `description` values must exactly match the Board offering used for the lookup. The definition must not contain offering-specific economic terms such as `creditIssuer`, `price`, or `checkPrice`; those remain on the Board.

Separating definitions keeps Boards compact and allows applications to fetch type information only for services they are considering. A publisher must make the definition available for every currently advertised provided or wanted offering.

If an offering is removed or its ID no longer identifies the advertised service, the publisher must reject the lookup. Clients must treat definitions as untrusted and potentially stale data.

### Service Contract

Every service contract defines:

```text
Input
    the logical value supplied for one invocation

Output
    the logical value returned when that invocation succeeds

Failures
    conditions under which no successful output is returned

Check
    the procedure available to evaluate fulfillment
```

The contract defines logical values and observable behavior. It does not prescribe programming-language classes, function signatures, process layout, internal algorithms, or storage structures unless those choices affect interoperability.

The separately retrieved service definition uses `input`, `output`, and `check` to carry these parts of the contract. The Board must not embed them.

---

## 9. Input

The `input` schema describes the logical value accepted by a service invocation.

It does not contain the input of a particular invocation.

For example:

```json
{
  "input": {
    "type": "object",
    "fields": {
      "location": {
        "type": "string",
        "description": "Location whose current temperature is requested."
      }
    }
  }
}
```

describes:

```text
input:
    location: string
```

An invocation later supplies a particular value, such as:

```text
location = "Berlin"
```

The provider must validate the input before treating the invocation as accepted. Invalid input produces a service failure rather than a successful output.

---

## 10. Output

The `output` schema describes the logical value returned when the service succeeds.

For example:

```json
{
  "output": {
    "type": "object",
    "fields": {
      "temperatureCelsius": {
        "type": "int32",
        "description": "Current temperature in whole degrees Celsius."
      }
    }
  }
}
```

describes:

```text
output:
    temperatureCelsius: int32
```

A successful output must conform to the retrieved definition's output schema and the service's semantic rules.

An error message is not a successful output merely because it can be represented by the output schema. Failures must be reported as failures by the service invocation protocol.

---

## 11. Type Descriptions

CR2SE version 1 defines a small language-independent type vocabulary for service input, output, and check schemas.

The primitive types are:

```text
bool
int32
int64
uint32
uint64
float
double
string
bytes
```

The composite types are:

```text
object
array
```

These are logical types. They do not prescribe the native type used by a C, Rust, Java, Python, or other implementation.

Every type description is a JSON object containing a `type` field.

A type description may also contain a `description` field:

```json
{
  "type": "uint64",
  "description": "Maximum number of bytes the provider must accept."
}
```

`description` is a non-empty UTF-8 string explaining the semantic meaning of the value. It does not change the value's type or range.

For custom services, field descriptions are part of the retrieved contract. They must not contradict the containing schema, the matching Board description, or other service-specific information. An implementation must not use a description to accept a value that violates its declared type.

Every named field in a service definition's `input`, `output`, and `check` schemas must include a description. For standard services, those descriptions must reflect the normative field semantics in the standard service specification and must not redefine them.

---

## 12. Primitive Types

### `bool`

`bool` represents `true` or `false`.

```json
{
  "type": "bool"
}
```

### `int32`

`int32` represents an integer in the range:

```text
-2147483648 .. 2147483647
```

### `int64`

`int64` represents an integer in the range:

```text
-9223372036854775808 .. 9223372036854775807
```

### `uint32`

`uint32` represents an integer in the range:

```text
0 .. 4294967295
```

### `uint64`

`uint64` represents an integer in the range:

```text
0 .. 18446744073709551615
```

### `float`

`float` represents an IEEE 754 binary32 floating-point value.

### `double`

`double` represents an IEEE 754 binary64 floating-point value.

For `float` and `double`, the service contract must define whether infinity, negative infinity, and NaN are permitted when they may occur. A transport representation that cannot encode an allowed value must define another unambiguous encoding for it.

### `string`

`string` represents Unicode text.

When carried in JSON, it follows the JSON string rules.

### `bytes`

`bytes` represents an arbitrary sequence of zero or more bytes.

It does not imply that the bytes are embedded in JSON, Base64 encoded, held entirely in memory, or transferred in one CR2SE frame.

The invocation protocol and service specification determine how a particular byte value is transported.

---

## 13. Object Type

An object contains named fields.

```json
{
  "type": "object",
  "fields": {
    "chunkId": {
      "type": "string",
      "description": "Identifier assigned to this chunk by the requester."
    },
    "data": {
      "type": "bytes",
      "description": "Exact bytes contained in this chunk."
    }
  }
}
```

`fields` must be a JSON object. Each property name is a field name and each property value is another CR2SE type description.

Objects may be nested.

Unless its service contract says otherwise, an input object containing an unknown field must not be rejected solely because of that field. This supports compatible extension. A service must not assign required semantics to a new field without introducing a compatible rule or a new service version.

---

## 14. Array Type

An array contains zero or more values described by one item schema.

```json
{
  "type": "array",
  "items": {
    "type": "string"
  }
}
```

Every item must conform to the schema in `items`.

Arrays may contain objects or other arrays. Composite types may be nested to a practical depth.

Implementations must impose reasonable size and nesting limits when processing schemas or values received from an untrusted peer.

---

## 15. Optional Object Fields

Object fields are required by default.

A field may contain:

```json
"optional": true
```

to indicate that it may be omitted.

For example:

```json
{
  "type": "object",
  "fields": {
    "query": {
      "type": "string",
      "description": "Text to search for."
    },
    "limit": {
      "type": "uint32",
      "description": "Maximum number of results to return.",
      "optional": true
    }
  }
}
```

`optional` applies only to a field within an object.

Omitting `optional`, or setting it to `false`, means the field is required.

CR2SE version 1 does not implicitly treat any type as nullable. Omission and a null value are not equivalent.

---

## 16. Schema and Wire Encoding

Service schemas describe logical values. They do not by themselves define the peer-to-peer wire encoding.

For example:

```text
input:
    document: bytes
```

does not require JSON, Base64, one frame, or one in-memory byte array.

Small structured values may have a JSON representation at the Node API boundary. Large values may be streamed using bounded CR2SE frames. The service's invocation protocol must define an unambiguous mapping from transported bytes to the logical schema.

Integer types retain their full specified ranges even when a particular JSON implementation cannot represent every value exactly. A JSON binding must not silently round an integer. The binding must either preserve the value exactly using a defined representation or reject it.

---

## 17. Schema Extensions

Future specifications or custom services may add fields to a type description.

Unknown schema fields do not make the service definition invalid. An implementation may ignore an unknown field only when that field is not required to understand or validate the service value.

An unknown `type` value is different. An implementation that does not understand a type must not pretend that it can construct, validate, invoke, or check that contract.

Standard CR2SE services should use the version 1 type vocabulary unless their specification explicitly defines an extension.

---

## 18. Price and Credit Agreement

Every CR2SE service invocation costs credits.

The offering selected for an invocation identifies:

```text
creditIssuer
price
```

These fields and their meanings are defined by the Board specification using the credit model defined by the Ledger specification.

The minimum service price is:

```text
1 credit
```

A price of zero is invalid. This rule applies even when the requester and provider have maximum trust in each other or are controlled by the same operator.

Requiring a nonzero price is an anti-abuse property of CR2SE. Closely related identities may issue and exchange large credit balances when they want effectively unrestricted cooperation, but they still use priced service invocations.

The price and credit issuer must be known and accepted before execution begins. CR2SE version 1 Board offerings use a fixed price rather than an implicit per-byte, per-second, or other formula.

---

## 19. Invocation Lifecycle

The logical service lifecycle is:

```text
discover offering
        |
        v
select service identifier, version, and offering
        |
        v
agree input, credit issuer, and price
        |
        v
provider validates input and current terms
        |
        v
provider performs service
        |
        +---- failure
        |
        +---- success + output
                    |
                    v
              charge credits
                    |
                    v
             optional check
                    |
                    v
             local trust decision
```

The peer-to-peer invocation protocol defines how these steps are represented on CR2SE streams. The Node API defines how a local application asks its node to initiate them.

An invocation must select a particular offering, not merely a service identifier, because one Board may contain several offerings of the same service version with different terms.

---

## 20. Success, Failure, and Charging

A service succeeds when the provider returns a successful result conforming to the service output contract.

After the service returns successfully, both parties may immediately apply the corresponding credit change to their local ledgers.

A check is not required before charging. The normal path assumes that successfully returned services are accepted without an additional check.

If the provider returns a service failure, the main service price must not be charged.

If communication is interrupted or the parties disagree about whether a successful result was returned, their local ledgers may differ. CR2SE does not define a global adjudicator or dispute-resolution system.

---

## 21. Service Checks

Every service definition must include a check.

The provider must support the check defined by the service contract for an accepted invocation or ongoing service. The requester decides whether to perform it.

A check is a service-specific verification procedure. It may examine the returned output, challenge an ongoing service, retrieve evidence, repeat part of the operation, or use another method appropriate to the service.

A check definition must state:

```text
what service or invocation is being checked;
who may request the check;
when the check is available;
how many checks are included or permitted and any frequency limit;
the check input;
the check output;
how its outcome is determined;
what the check proves;
known limitations that can make it inconclusive.
```

For a custom service, the separately retrieved definition of `check` must contain at least:

```json
{
  "check": {
    "description": "A precise description of the verification procedure.",
    "input": {
      "type": "object",
      "fields": {}
    },
    "output": {
      "type": "object",
      "fields": {
        "outcome": {
          "type": "string",
          "description": "Verification outcome: pass, fail, or inconclusive."
        }
      }
    }
  }
}
```

The check output must communicate one of the standard outcomes defined below. It may also contain service-specific evidence or details.

---

## 22. Check Outcomes

A completed check has one of three logical outcomes:

```text
pass
    the check found the verified property to be satisfied

fail
    the check found the verified property not to be satisfied

inconclusive
    the check could not establish either pass or fail
```

An inconclusive result is not a successful verification, but it is also not proof that the provider failed to provide the service.

The service specification must define the evidence and rules that produce each outcome. It must also state the scope of the claim. For example, one successful random storage challenge does not prove that every byte was continuously available throughout the complete storage period.

The check operation itself may complete successfully while reporting `fail` or `inconclusive`. In that case the provider successfully returned a valid check result; the outcome describes the checked service, not whether the check protocol ran correctly.

---

## 23. Check Cost

A check may be included in the original service price or may have an additional credit price.

The Board may advertise a `checkPrice` for an offering. It is expressed in the same credits identified by the offering's `creditIssuer`.

If `checkPrice` is absent, the service's required check is included in the main service price and produces no additional credit charge. This is not a free service: the check is part of the service invocation that was already purchased for at least one credit. The service contract must define how many included checks may be requested and any time or frequency limit.

If `checkPrice` is present, it must be at least one credit per check invocation. The requester must know and accept that price before initiating the check.

A successfully completed check may be charged regardless of whether its outcome is `pass`, `fail`, or `inconclusive`, because those are valid outputs of the check. A check that fails to execute and returns no valid check result must not be charged.

---

## 24. Checks, Trust, and Disputes

A check does not automatically change credits, reverse a completed payment, or force either party to update trust.

After a check, each identity may use the result as an input to its own trust calculation.

For example:

```text
pass
    may increase or preserve trust

fail
    may reduce trust

inconclusive
    requires a local decision
```

These are possible policies, not mandatory trust calculations.

Disputes, refunds, compensation, arbitration, and reconciliation after a service result are outside CR2SE version 1.

---

## 25. Standard Service Families

CR2SE version 1 reserves three standard service families.

Their individual specifications define their exact operation identifiers, versions, schemas, offering information, invocation rules, and checks.

### Storage

Storage services preserve arbitrary bytes for an agreed period or under other explicitly advertised storage terms.

The Storage specification defines the related operations required to place, retrieve, check, and remove stored data. A typical check challenges the provider for selected stored bytes or cryptographic evidence derived from them.

This document does not define storage chunking, retention measurement, retrieval rules, or proof details. Those belong in `Storage.md`.

### Computation

Computation services execute a defined computation using supplied input and return its result.

The Computation specification must define execution semantics, supported computation descriptions, limits, determinism requirements where applicable, result encoding, and verification behavior. Checks may validate the result, repeat the computation, or use computation-specific evidence.

This document does not select a runtime, instruction set, container format, proof system, or scheduling policy. Those belong in the Computation specification.

### Page

Page services host exclusively static content.

Examples include:

```text
a home page;
a recipe;
an HTML document;
images, stylesheets, or other static assets;
another fixed content resource.
```

A Page service does not execute server-side application logic to generate dynamic responses. Its specification defines publication, addressing, retrieval, lifetime, content metadata, supported collections of static resources, and checks. A typical check retrieves a resource and compares its content and metadata with the expected values.

The detailed rules belong in the Page specification.

---

## 26. Standard and Custom Check Examples

The following examples illustrate the expected verification model. They are not complete definitions of the standard services.

```text
Storage
    Request a randomly selected offset or range.
    Compare the returned bytes or evidence with expected data.

Computation
    Validate the result according to the computation definition.
    Recompute all or part of a deterministic operation when practical.

Page
    Retrieve an advertised path.
    Compare status, media type, and content bytes or hash.

Custom service
    Follow the check procedure included in its retrieved service definition.
    Return pass, fail, or inconclusive.
```

The strength and cost of these checks differ. Service specifications must describe those limitations rather than claiming that all checks provide equivalent assurance.

---

## 27. Board Relationship

The Board describes currently advertised offerings.

For each offering it identifies:

```text
offering ID;
service identifier;
service version;
direction: provided or wanted;
credit issuer;
price;
optional separate check price;
preconditions;
offering-specific information.
```

The Board does not carry input, output, or check schemas. A client retrieves them separately by offering ID before it constructs, validates, implements, or invokes an unfamiliar service.

The Board does not execute services and does not decide whether a check passes.

---

## 28. Ledger Relationship

The Ledger records credits and local trust.

Services use the Ledger's credit units, issuer-specific balances, and local trust values. A service does not create a global balance or make a provider's promise enforceable.

Successful service completion permits the parties to update their corresponding local credit records immediately. Later verification affects trust or other local policy but does not automatically rewrite ledger history.

---

## 29. Network and Node API Relationship

The Network layer transports service invocations, streamed values, outputs, and checks between peers.

The Node API exposes logical service operations to local applications. In particular, `service.get` retrieves a remote service definition by the offering ID discovered on its Board, and `service.invoke` uses the selected offering.

Neither layer changes the service contract. A large `bytes` value remains one logical value even when it is transferred through many bounded frames and exposed to a local application through a streaming mechanism.

Exact peer frame types and the final streaming binding are defined outside this document.

---

## 30. Untrusted Service Definitions and Values

Boards, service definitions, schemas, inputs, outputs, check definitions, and check evidence received from peers are untrusted input.

Implementations must enforce limits on:

```text
schema size and depth;
array and object size;
string and byte lengths;
numeric conversion;
execution time;
storage and memory use;
check frequency;
other service-specific resources.
```

Understanding a custom service description does not make its suggested implementation safe. Implementations must not automatically execute arbitrary code, commands, scripts, containers, or downloads merely because a Board or service definition recommends them.

A valid check result establishes only the service-specific fact defined by that check. It does not establish that the provider, returned content, or suggested software is safe or trustworthy for unrelated purposes.

---

## 31. Version 1 Requirements Summary

A CR2SE version 1 service has:

```text
a non-empty service identifier;
a positive service version;
a defined input;
a defined output;
a non-empty semantic description for every named input, output, and check field;
a price of at least one credit;
a defined check;
defined success and failure behavior.
```

For standard services:

```text
the CR2SE service specification is authoritative;
all implementations of the same version behave the same;
a wanted offering requests that exact standard behavior.
```

For custom services:

```text
the Board contains a compact service summary and offering terms;
the complete definition is retrieved separately by Board ID;
the input, output, and check schemas use the CR2SE type system;
implementation suggestions are optional and non-normative.
```

For completion and verification:

```text
successful service return permits immediate charging;
performing a check is optional;
providing a check mechanism is mandatory;
a check may return pass, fail, or inconclusive;
a check may have an additional advertised price;
checks do not automatically reverse credits;
disputes are outside CR2SE version 1.
```
