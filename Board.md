# CR2SE Board

The CR2SE Board describes the services an identity is willing to provide and the services it wants other identities to provide.

Common domain terms such as **Board publisher**, **offering**, **provided service**, and **wanted service** are defined in the [CR2SE Glossary](./Glossary.md).

The Board is the service-discovery layer of CR2SE.

It answers questions such as:

```text
What provided services does this Board publisher advertise?

What wanted services does this Board publisher advertise?

What does a particular service cost?

Which credit is used for payment?

What conditions must be satisfied before the service may be invoked?
```

The Board does not define the behavior of every possible service.

For example, the Board may advertise a storage service, but the rules governing storage belong to the CR2SE Storage specification.

Likewise, an implementation may advertise custom services that are not defined by CR2SE.

The Board provides a compact, machine-readable summary of those services. Detailed service definitions are retrieved separately using the service's Board `id`.

The common service model, input and output schemas, type system, service checks, and standard-versus-custom service rules are defined by the [CR2SE Services specification](./Services.md).

---

## 1. Board Publisher

A Board is published by a CR2SE identity.

The identity publishing the Board is called the **Board publisher**.

For example:

```text
Alice publishes a Board.
```

Alice is the Board publisher.

The Board belongs to the identity, not to:

```text
a TCP connection;
an IP address;
a machine;
a process;
a particular application.
```

Several nodes operating with the same CR2SE identity may therefore publish the same logical Board.

How multiple nodes belonging to the same identity coordinate their Boards is implementation-dependent.

---

## 2. Board Representation

A CR2SE Board is represented as JSON.

A minimal Board is:

```json
{
  "version": 1,
  "providedServices": [],
  "wantedServices": []
}
```

A version 1 Board must contain:

```text
version
providedServices
wantedServices
```

Additional fields may be present.

Implementations must ignore Board fields they do not understand unless a future CR2SE specification explicitly defines a field as requiring different behavior.

This allows Boards to be extended without making older implementations unable to read them.

---

## 3. Board Version

The `version` field identifies the Board schema version.

This document defines:

```json
"version": 1
```

The version is an unsigned integer.

A version 1 implementation must not interpret a Board with an unsupported version as if it were a version 1 Board.

How a node exposes an unsupported Board version to applications is implementation-dependent.

---

## 4. Services

A **service** is an operation one CR2SE identity may perform for another identity.

Examples include:

```text
store data;
recover stored data;
perform a computation;
search for information;
return sensor information;
relay a message;
look up some resource.
```

CR2SE does not require all possible services to be defined by the core protocol.

Applications and future CR2SE specifications may define additional services.

The Board therefore treats service descriptions generically.

The normative definition of a service belongs to the CR2SE Services specification. The Board advertises offerings of those services.

---

## 5. Provided Services

`providedServices` contains services that the Board publisher is willing to provide to other identities.

The following partial example focuses only on service direction and identity; a complete offering also contains the payment fields defined later in this document:

```json
{
  "version": 1,
  "providedServices": [
    {
      "id": "temperature-default",
      "service": "example.weather.current",
      "serviceVersion": 1,
      "description": "Returns the current temperature for a location."
    }
  ],
  "wantedServices": []
}
```

Conceptually:

```text
Board publisher
      |
      | provides
      v
other identities
```

If Alice publishes this Board, the provided service means:

```text
Alice provides example.weather.current.
```

It does not mean that every invocation must succeed.

Whether an invocation is accepted depends on the service, its requirements, the identities involved, the local ledger, trust, available resources, and local policy.

---

## 6. Wanted Services

`wantedServices` contains services that the Board publisher wants other identities to provide.

The following partial example focuses only on service direction and identity; a complete offering also contains the payment fields defined later in this document:

```json
{
  "version": 1,
  "providedServices": [],
  "wantedServices": [
    {
      "id": "storage-flexible",
      "service": "cr2se.storage",
      "serviceVersion": 1,
      "description": "Store requester-selected data for a requester-selected period."
    }
  ]
}
```

Conceptually:

```text
other identities
      |
      | provide
      v
Board publisher
```

If Alice publishes this Board, the wanted service means:

```text
Alice wants another identity to provide this service to Alice.
```

The distinction between provided and wanted services concerns the direction of the service.

It does not describe the direction of credits.

Payment is described separately.  

---

## 7. Offerings

Each element of `providedServices` or `wantedServices` is called an **offering**.

An offering describes one particular way in which a service may be exchanged.

For example, a fixed-package storage service might advertise separate offerings:

```text
store up to 1 GB for 10 days for 5 credits;

store up to 1 GB for 30 days for 12 credits;

store up to 10 GB for 10 days for 40 credits.
```

Even though all three perform storage, they represent different advertised terms.

Such fixed packages must therefore be represented as separate offerings. The standard `cr2se.storage` service instead defines one bounded, deterministic variable-price offering so a requester can choose its byte count and retention time.

For example:

```json
{
  "providedServices": [
    {
      "id": "store-1g-10d",
      "service": "example.storage.fixed",
      "serviceVersion": 1
    },
    {
      "id": "store-1g-30d",
      "service": "example.storage.fixed",
      "serviceVersion": 1
    },
    {
      "id": "store-10g-10d",
      "service": "example.storage.fixed",
      "serviceVersion": 1
    }
  ]
}
```

The service defines the operation.

The offering defines one advertised variant of that operation.

Examples that focus on one Board field may omit other required offering fields for brevity. Such excerpts are not complete offerings unless explicitly described as complete.

---

## 8. Offering Identifier

Every offering must contain an `id`.

For example:

```json
"id": "store-1g-10d"
```

The offering ID is an opaque UTF-8 string.

It must not be empty.

Offering IDs must be unique within one Board.

For example, this is invalid:

```json
{
  "providedServices": [
    {
      "id": "storage",
      "service": "cr2se.storage",
      "serviceVersion": 1
    },
    {
      "id": "storage",
      "service": "cr2se.storage",
      "serviceVersion": 1
    }
  ]
}
```

because the two offerings have the same ID.

Offering IDs do not need to be globally unique.

For example:

```text
Alice may have offering "storage".
Bob may also have offering "storage".
```

Those IDs refer to different Boards and therefore do not conflict.

An implementation should keep an offering ID stable while the same logical offering continues to exist.

If the meaning of an offering changes substantially, publishing it under a new ID is recommended.

Applications must treat offering IDs as opaque strings and must not derive service semantics from their contents.

---

## 9. Service Identifier and Version

Every offering must contain `service` and `serviceVersion` fields.

For example:

```json
{
  "service": "cr2se.storage",
  "serviceVersion": 1
}
```

The service identifier describes the operation implemented by the offering.

A service identifier is a non-empty UTF-8 string.

The service version is an unsigned integer greater than zero. It selects an exact version of that service's contract.

The service identifier and version together identify the service:

```text
(service, serviceVersion)
```

An implementation must not silently substitute another version when it does not support the advertised version.

The same service identifier may appear in several offerings.

For example:

```json
[
  {
    "id": "store-small-short",
    "service": "cr2se.storage",
    "serviceVersion": 1
  },
  {
    "id": "store-small-long",
    "service": "cr2se.storage",
    "serviceVersion": 1
  }
]
```

These are two offerings of the same service.

A service identifier therefore must not be treated as an offering identifier.

The `id` identifies the particular offering.

The `service` and `serviceVersion` identify the exact operation contract the offering performs.

---

## 10. Service Namespaces

Service names beginning with:

```text
cr2se.
```

are reserved for services defined by CR2SE specifications.

For example:

```text
cr2se.storage
```

may be defined by the CR2SE Storage specification.

Custom applications should use namespaced service identifiers that are unlikely to conflict with services created by unrelated implementations.

For example:

```text
example.weather.current

talksphere.message.send

org.example.compute.hash
```

CR2SE does not maintain a global registry for custom service names.

A node may advertise a service unknown to the receiving implementation.

Unknown services do not make the Board invalid.

---

## 11. Description

Every offering must contain a human-readable `description`.

For example:

```json
"description": "Store requester-selected data for a requester-selected period."
```

The description is a non-empty UTF-8 string.

It exists for:

```text
users;
developers;
debugging;
service discovery interfaces;
human-readable documentation.
```

Programs must not parse the description to redefine the behavior of a standard CR2SE service. Machine-readable rules belong in fields defined by the service specification.

For a custom service, the description helps users and automated agents decide whether to retrieve its full definition. It does not replace the separately retrievable `input`, `output`, and `check` definitions or service-specific information.

For example, the Storage specification defines machine-readable size and retention limits plus a deterministic pricing model.

The description may explain those terms in more detail for humans.

This Board-level `description` is a discovery summary. The full service definition returned for the offering repeats that description and contains the descriptions of individual input, output, and check fields. Those field descriptions are defined by the [CR2SE Services specification](./Services.md).

---

## 12. Offering Information

An offering may contain an `info` object.

`info` contains service-specific information.

For example:

```json
{
  "info": {
    "maximumBytes": 1000000000,
    "minimumRetentionSeconds": 3600,
    "maximumRetentionSeconds": 2592000
  }
}
```

The meaning of `info` is defined by the service.

The Board specification does not assign universal meaning to arbitrary fields inside `info`.

For example:

```text
maximumBytes
minimumRetentionSeconds
algorithm
resolution
region
compression
cpuArchitecture
```

may be meaningful to particular services without being concepts understood by the Board layer.

This allows CR2SE to describe services that do not yet exist when this document is written.

Unknown `info` fields must not make the Board itself invalid.

An implementation that does not understand the service-specific information may expose the offering to applications without being able to invoke it automatically.

---

## 13. Different Terms and Pricing Models

A single offering should describe one coherent set of service terms.

Substantially different service conditions or pricing models should normally be represented as different offerings. A service whose specification defines deterministic variable pricing may use one offering for a bounded range of requester-selected inputs.

For example:

```json
{
  "providedServices": [
    {
      "id": "storage-1g-10d",
      "service": "example.storage.fixed",
      "serviceVersion": 1,
      "description": "Store up to 1 GB for 10 days.",
      "info": {
        "maximumBytes": 1000000000,
        "periodDays": 10
      }
    },
    {
      "id": "storage-1g-30d",
      "service": "example.storage.fixed",
      "serviceVersion": 1,
      "description": "Store up to 1 GB for 30 days.",
      "info": {
        "maximumBytes": 1000000000,
        "periodDays": 30
      }
    }
  ]
}
```

Separate offerings are preferred over an ad hoc price table when the alternatives can naturally be described independently. A standard service-defined pricing model is not an ad hoc price table: its specification defines the exact fields, arithmetic, limits, and rounding shared by all implementations.

The service specification determines which differences are significant enough to require separate offerings.

---

## 14. Credits Used for Payment

Every offering must contain `creditIssuer` to identify the issuer of the credits used for that offering.

For example:

```json
"creditIssuer": "CR2SE_ID"
```

`creditIssuer` must contain a valid CR2SE identity ID as defined by the Identity specification.

The value is explicit.

There is no special value such as:

```text
own
self
remote
peer
```

The actual issuer identity must be included.

This avoids making the meaning depend on where the field appears or which peer is currently reading it.

---

## 15. Credit Meaning for Provided Services

For a provided service:

```text
creditIssuer
```

identifies the issuer of the credits that the Board publisher expects to receive as payment.

Suppose Alice publishes:

```json
{
  "id": "weather",
  "service": "example.weather.current",
  "serviceVersion": 1,
  "creditIssuer": "ALICE_ID",
  "price": 2
}
```

This means:

```text
Alice provides the service.

The advertised price is 2 Alice credits.
```

Alice could instead advertise:

```json
{
  "creditIssuer": "BOB_ID",
  "price": 2
}
```

This would mean:

```text
Alice provides the service.

The advertised price is 2 Bob credits.
```

CR2SE does not require a provider to accept only its own credits.

---

## 16. Credit Meaning for Wanted Services

For a wanted service:

```text
creditIssuer
```

identifies the issuer of the credits the Board publisher is willing to use to pay for the service.

Suppose Alice publishes:

```json
{
  "id": "storage",
  "service": "example.storage.fixed",
  "serviceVersion": 1,
  "creditIssuer": "ALICE_ID",
  "price": 5
}
```

inside `wantedServices`.

This means:

```text
Alice wants the service.

Alice is willing to compensate the provider with 5 Alice credits.
```

If Alice instead advertises:

```json
"creditIssuer": "BOB_ID"
```

then Alice is advertising payment using Bob credits.

How Alice obtained those Bob credits is a Ledger concern and does not affect the Board representation.

---

## 17. Price

Every offering must contain exactly one of:

```text
price
pricing
```

`price` is a fixed advertised credit price.

For example:

```json
"price": 5
```

The price is expressed in credits issued by `creditIssuer`.

Therefore:

```json
{
  "creditIssuer": "ALICE_ID",
  "price": 5
}
```

means:

```text
5 Alice credits
```

The `price` value is an unsigned 64-bit integer.

Its valid range is:

```text
1 .. 18446744073709551615
```

This uses the same credit amount representation defined by the Ledger specification.

Fractional credits do not exist.

Therefore values such as:

```json
"price": 0.01
```

are invalid CR2SE credit prices.

`pricing` is a JSON object describing a deterministic variable-price model. It must contain:

```text
model
    a non-empty string identifying the exact pricing model and version
```

The remaining fields and calculation are defined by the selected service specification. For example, the Storage specification defines `cr2se.storage.v1`, whose exact rational factors calculate a price from requested bytes and time.

An implementation that does not understand the named pricing model may display the offering, but must not calculate, accept, or invoke it. Unknown pricing models do not make unrelated Board offerings invalid.

---

## 18. Minimum Price

The minimum CR2SE service price is:

```text
1 credit
```

A price of zero is invalid.

This remains true when the identities have maximum trust in each other or are controlled by the same operator. Requiring a nonzero price is an anti-abuse property of CR2SE.

Identities that want effectively unrestricted cooperation may issue each other sufficiently large credit balances. They must still use service operations whose fixed or calculated final price is one credit or more.

---

## 19. Fixed and Calculated Prices

The `price` field is the price of the offering described by that Board entry.

For example:

```json
{
  "id": "storage-1g-10d",
  "service": "example.storage.fixed",
  "serviceVersion": 1,
  "creditIssuer": "ALICE_ID",
  "price": 5,
  "description": "Store up to 1 GB for 10 days."
}
```

means that the advertised service variant costs:

```text
5 Alice credits
```

For a fixed-price offering, the Board does not interpret this as:

```text
5 credits per byte
```

or:

```text
5 credits per day
```

or any other implicit pricing formula.

A variable-price offering instead names an explicit service-defined model. The
following Storage example uses the factor representation defined in
[Storage](./Storage.md): `numerator` is a number of credits and `denominator` is
the number of applicable bytes or byte-seconds covered by that rate. Thus
`1 / 1000000` means one credit per one million applicable units.

```json
{
  "id": "storage-flexible",
  "service": "cr2se.storage",
  "serviceVersion": 1,
  "creditIssuer": "ALICE_ID",
  "pricing": {
    "model": "cr2se.storage.v1",
    "minimumPrice": 1,
    "byteUsageFactor": { "numerator": 1, "denominator": 1000000 },
    "byteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
    "retrievalByteUsageFactor": { "numerator": 1, "denominator": 1000000 },
    "renewalByteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
    "removePrice": 1
  },
  "checkPrice": 1,
  "preconditions": [
    "cr2se.identity"
  ],
  "info": {
    "maximumBytes": 1000000000,
    "minimumRetentionSeconds": 3600,
    "maximumRetentionSeconds": 2592000,
    "maximumTotalRetentionSeconds": 31536000,
    "maximumRetrieveBytes": 1000000000,
    "checkResponseSeconds": 30
  }
}
```

The named model, rather than the Board layer, gives these fields their normative meaning. The requester chooses valid input within the advertised limits, and both peers calculate the same integer price before accepting the operation.

If a service has multiple useful combinations of terms and prices, they may be advertised as several offerings.

For example:

```json
[
  {
    "id": "storage-1g-10d",
    "service": "example.storage.fixed",
    "serviceVersion": 1,
    "creditIssuer": "ALICE_ID",
    "price": 5,
    "info": {
      "maximumBytes": 1000000000,
      "periodDays": 10
    }
  },
  {
    "id": "storage-1g-30d",
    "service": "example.storage.fixed",
    "serviceVersion": 1,
    "creditIssuer": "ALICE_ID",
    "price": 12,
    "info": {
      "maximumBytes": 1000000000,
      "periodDays": 30
    }
  }
]
```

The custom service definition determines the exact meaning of these illustrative fixed-package fields. The standard Storage service instead uses the explicit variable model shown above.

The Board only provides the common mechanism for advertising the variants.

---

## 20. Price Must Be Determinable Before Execution

For a fixed-price offering, the Board price is fixed for the complete offering. For a variable-price offering, the Board and the service specification together must contain everything required to calculate one exact final price from the validated invocation input.

An offering must not leave its price discretionary, depend on undisclosed provider state, or determine an unbounded final cost after execution. Variable pricing must advertise bounded inputs and a deterministic model. The calculated price must fit the CR2SE `uint64` credit range.

The exact fixed or calculated price and credit issuer must be known and accepted before execution begins. Metadata needed to calculate a streamed operation's price may be exchanged first, but the provider must not begin the chargeable work or accept a large body until price agreement. If a cached Board is stale and the provider no longer accepts its advertised terms, the provider must reject the invocation rather than execute it at an undisclosed price.

---

## 21. Service Definitions Are Separate

The Board is an index of advertised offerings, not a container for their type definitions. An offering must not contain `input`, `output`, or `check` schemas.

Every advertised offering must have a separately retrievable service definition. A client uses the offering's Board `id` with the `service.get` Node API operation defined in [NodeApi.md](./NodeApi.md). The returned definition contains:

```text
the offering ID;
the service identifier and version;
the full service description;
the input schema;
the output schema;
the check definition.
```

The definition's `id`, `service`, `serviceVersion`, and `description` must match the corresponding Board offering. Repeating these fields lets a client detect a stale or inconsistent response.

Every named field in the input, output, and check schemas must contain a non-empty `description`, including fields in nested objects. A wanted custom service definition must be clear enough that an unfamiliar implementation, including an AI-assisted implementation, can implement it after retrieving the definition.

Two offerings with the same `service` and `serviceVersion` must use the same logical input, output, success, failure, and check definitions. Offering-specific terms such as capacity, duration, fixed price or pricing model, and preconditions remain on the Board and may differ.

A Board remains valid when a definition uses a schema type that the client does not understand. The client may still display the Board summary, but it must not claim to understand or invoke that service definition.

---

## 22. Checks and Check Price

Every service has a check, as defined by the [CR2SE Services specification](./Services.md) and by the specification of that service.

Performing a check is optional. Providing the defined check mechanism is mandatory.

A check may be included in the main offering price or separately priced. An offering may contain:

```json
"checkPrice": 1
```

`checkPrice` uses the same credits identified by the offering's `creditIssuer`.

If `checkPrice` is absent, the required check is included in the main service price and has no additional charge. It is part of the already purchased service, not a free offering. The service contract defines how many included checks may be requested and any time or frequency limit.

If `checkPrice` is present, it is the fixed price of one check invocation and must be an unsigned 64-bit integer in the range:

```text
1 .. 18446744073709551615
```

The requester must know and accept a separate check price before initiating that check.

---

## 23. Implementation Suggestions

A custom offering may contain `implementationSuggestions`.

This is an array of objects containing non-normative information that may help a provider implement the service. For example:

```json
{
  "implementationSuggestions": [
    {
      "name": "Example Processor",
      "version": "2.1",
      "uri": "https://example.invalid/processor",
      "description": "One implementation known to produce the required output."
    }
  ]
}
```

Each suggestion must contain a non-empty `name`. `version`, `uri`, and `description` are optional UTF-8 strings.

Suggestions do not change the service contract. A provider may use another implementation that produces the required behavior.

Implementations must treat these values as untrusted metadata. Reading a Board must not automatically download, install, or execute suggested software.

This field is particularly useful for wanted custom services, but it may appear in either wanted or provided offerings.

---

## 24. Preconditions

An offering may contain a `preconditions` array.

A precondition identifies something that must be satisfied before the service may proceed.

For example:

```json
{
  "preconditions": [
    "cr2se.identity"
  ]
}
```

Preconditions are UTF-8 strings.

Names beginning with:

```text
cr2se.
```

are reserved for preconditions defined by CR2SE.

Custom specifications should use namespaced identifiers.

For example:

```text
example.membership
talksphere.roomAccess
```

The meaning and verification procedure of a precondition must be defined by the specification that introduces it.

---

## 25. Identity Preconditions

A service that requires the remote participant to prove control of a CR2SE identity may advertise the standard identity precondition:

```json
"cr2se.identity"
```

The identity proof uses the identity and cryptographic mechanisms defined by the CR2SE Identity and Encryption specifications.

The Board does not redefine those cryptographic operations.

It only declares that successful identity proof is required by the offering.

---

## 26. Multiple Preconditions

An offering may require several preconditions.

For example:

```json
{
  "preconditions": [
    "cr2se.identity",
    "example.membership"
  ]
}
```

All listed preconditions must be satisfied unless the specification defining a particular precondition explicitly states otherwise.

An implementation that cannot understand or satisfy a required precondition must not assume that the precondition can be ignored when invoking the offering.

Unknown preconditions do not make the complete Board invalid.

They may, however, make that particular offering unusable by an implementation that does not understand them.

---

## 27. Offering Example

A complete offering could look like:

```json
{
  "id": "weather-current",
  "service": "example.weather.current",
  "serviceVersion": 1,
  "description": "Returns the current temperature for a location.",
  "creditIssuer": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567ABCDEFGHIJKLMNOP",
  "price": 1,
  "preconditions": [
    "cr2se.identity"
  ]
}
```

The Board layer can determine:

```text
the offering identifier;

the service identifier;

the service version;

the human-readable description;

which credits are used;

the fixed advertised price;

the required preconditions;
```

The logical input, output, and check are obtained separately with `service.get` using `weather-current`. The Board does not need to know those schemas or how the weather service obtains temperature information.

---

## 28. Storage Example

The following is illustrative.

The exact storage fields and semantics belong to `Storage.md`.

```json
{
  "id": "storage-flexible",
  "service": "cr2se.storage",
  "serviceVersion": 1,
  "description": "Store requester-selected data for a requester-selected period.",
  "creditIssuer": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567ABCDEFGHIJKLMNOP",
  "pricing": {
    "model": "cr2se.storage.v1",
    "minimumPrice": 1,
    "byteUsageFactor": { "numerator": 1, "denominator": 1000000 },
    "byteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
    "retrievalByteUsageFactor": { "numerator": 1, "denominator": 1000000 },
    "renewalByteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
    "removePrice": 1
  },
  "checkPrice": 1,
  "preconditions": [
    "cr2se.identity"
  ],
  "info": {
    "maximumBytes": 1000000000,
    "minimumRetentionSeconds": 3600,
    "maximumRetentionSeconds": 2592000,
    "maximumTotalRetentionSeconds": 31536000,
    "maximumRetrieveBytes": 1000000000,
    "checkResponseSeconds": 30
  }
}
```

The requester supplies an exact size and retention period within these limits.
The Storage specification defines the price calculation, including exact
rational arithmetic and rounding. Retrieval and renewal are paid separately
using a compatible Storage offering current when each later operation begins.

---

## 29. Complete Board Example

A Board may contain both wanted and provided services.

For example:

```json
{
  "version": 1,

  "providedServices": [
    {
      "id": "temperature-current",
      "service": "example.weather.current",
      "serviceVersion": 1,
      "description": "Returns the current temperature.",
      "creditIssuer": "ALICE_ID",
      "price": 1
    }
  ],

  "wantedServices": [
    {
      "id": "storage-flexible",
      "service": "cr2se.storage",
      "serviceVersion": 1,
      "description": "Store requester-selected data for a requester-selected period.",
      "creditIssuer": "ALICE_ID",
      "pricing": {
        "model": "cr2se.storage.v1",
        "minimumPrice": 1,
        "byteUsageFactor": { "numerator": 1, "denominator": 1000000 },
        "byteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
        "retrievalByteUsageFactor": { "numerator": 1, "denominator": 1000000 },
        "renewalByteStorageDurationFactor": { "numerator": 1, "denominator": 86400000000 },
        "removePrice": 1
      },
      "checkPrice": 1,
      "preconditions": [
        "cr2se.identity"
      ],
      "info": {
        "maximumBytes": 1000000000,
        "minimumRetentionSeconds": 3600,
        "maximumRetentionSeconds": 2592000,
        "maximumTotalRetentionSeconds": 31536000,
        "maximumRetrieveBytes": 1000000000,
        "checkResponseSeconds": 30
      }
    }
  ]
}
```

Conceptually:

```text
Alice's Board

Provided:
    example.weather.current
        Alice provides temperature information.
        Price: 1 Alice credit.

Wanted:
    cr2se.storage
        Alice wants storage.
        Alice offers Alice credits calculated by the advertised Storage model.
```

---

## 30. Board State

A Board describes the services and terms currently advertised by its publisher.

A Board may change.

For example, an identity may:

```text
add an offering;
remove an offering;
change a fixed price or pricing model;
change service-specific information;
change a description;
change preconditions.
```

A peer must not assume that a previously retrieved Board remains permanently valid.

How often Boards are refreshed or cached is implementation-dependent.

---

## 31. Offering Removal

If an offering previously existed and no longer appears on a newly retrieved Board, it is no longer advertised by that Board.

For example:

```text
Board A:

providedServices:
    storage-1g-10d
    storage-1g-30d
```

and later:

```text
Board B:

providedServices:
    storage-1g-30d
```

means that:

```text
storage-1g-10d
```

is no longer advertised.

Removing an offering stops new selections of that offering. It does not by
itself cancel an accepted ongoing service or shorten an active Storage lease.
Later Storage operations use another compatible current offering, if one is
available; their prices are not inherited from the removed offering.

CR2SE does not require a separate deletion record.

The current Board is the current advertised set.

---

## 32. Offering Changes

Because offering IDs identify advertised variants, an implementation should avoid silently changing the fundamental meaning of an offering while retaining the same ID.

For example, changing:

```text
store up to 1 GB for 10 days
```

into:

```text
store up to 100 MB for 1 day
```

while retaining the same offering ID may confuse software that has cached information about the previous offering.

A new offering ID is recommended when the service variant changes substantially.

Minor descriptive changes do not require a new ID.

---

## 33. Unknown Fields

A version 1 implementation must tolerate fields it does not understand.

For example:

```json
{
  "id": "example",
  "service": "example.operation",
  "serviceVersion": 1,
  "futureField": {
    "something": true
  }
}
```

must not make the entire Board invalid merely because `futureField` is unknown.

This rule applies to:

```text
the Board object;
offerings;
service-specific info.
```

An implementation may preserve unknown fields when passing Board JSON to applications.

---

## 34. Unknown Services

A Board may contain a service identifier unknown to the receiving node.

For example:

```json
{
  "service": "someone.newService",
  "serviceVersion": 1
}
```

The Board remains valid.

The node may:

```text
display the offering;
return it through the Node API;
store it temporarily;
allow an application that understands it to use it.
```

The core CR2SE implementation does not need built-in knowledge of every advertised service.

---

## 35. Definitions With Unknown Types

Service schemas are not part of the Board. If a separately retrieved service definition uses an input, output, or check type an implementation does not understand, the Board remains readable and the offering remains discoverable.

However, the implementation must not pretend that it understands how to construct or validate values of that type. Applications that understand the extension may still use it.

---

## 36. Unknown Preconditions

Unknown preconditions behave similarly.

The Board remains valid.

The particular offering must not be treated as automatically satisfying a precondition that the implementation does not understand.

This prevents extension compatibility from accidentally removing access requirements.

---

## 37. Board and Ledger

The Board and Ledger solve different problems.

The Board describes:

```text
what services are wanted;

what services are provided;

what credits an offering uses;

what an offering costs;
```

The Ledger records:

```text
credits owned;

credits issued;

trust.
```

For example, a Board may advertise:

```text
Service price:
    10 Alice credits
```

while Bob's Ledger may contain:

```text
Owned Alice credits:
    25
```

The Board describes the offer.

The Ledger determines Bob's local economic state relative to the credit issuer.

---

## 38. Board and Identity

The Board uses CR2SE identities where identities are required.

For example:

```text
creditIssuer
```

contains a CR2SE identity ID.

The Board does not define identity generation, signing keys, identity encoding, or identity proof.

Those concepts are defined by the CR2SE Identity and Encryption specifications.

---

## 39. Board and Network

The Board is independent of TCP connection identity.

A Board describes an identity's services.

The CR2SE Network layer provides communication between nodes.

The Board does not redefine:

```text
TCP;
frames;
streams;
frame boundaries;
stream IDs;
large-data framing.
```

Those concepts belong to the Network specification.

A Board service may use CR2SE streams to carry its invocation and result.

---

## 40. Board and Node API

The Node API provides local applications with operations for interacting with a CR2SE node.

In particular, the Node API defines an operation logically equivalent to:

```text
board.get
```

which retrieves a remote peer's Board.

The Board value returned by `board.get` follows the schema defined by this document.

After discovery, the Node API operation:

```text
service.get
```

retrieves the complete definition for one offering using its Board `id`.

Service definition retrieval and invocation through the Node API use offerings discovered through Boards.

The Node API defines the application-to-local-node interface.

The Board defines the compact service information being discovered. The Services specification defines the detailed definition returned separately.

These are separate layers.

---

## 41. Selecting an Offering

An application may select an offering using information from the Board.

For example:

```text
Alice provides:

storage-economy
    lower byte-usage and byte-storage-duration factors

storage-fast-retrieval
    higher storage factors, lower retrieval factor

storage-long-term
    larger maximum total retention
```

A remote application may choose whichever offering satisfies its needs.

Selection policy is not defined by the Board.

An implementation may consider:

```text
fixed price or understood pricing model;
trust;
available credits;
service terms;
local application preferences;
service-specific metadata.
```

CR2SE does not require one universal algorithm for choosing between offerings.

---

## 42. Matching Wanted and Provided Services

Wanted and provided services may be used for discovery.

For example:

```text
Alice wants:
    cr2se.storage

Bob provides:
    cr2se.storage
```

This indicates that Alice and Bob may be able to exchange a storage service.

Matching the service identifier alone does not necessarily mean the offerings are compatible.

Applications may also need to compare:

```text
service version;
input and output schemas from the retrieved service definitions;
check definitions from the retrieved service definitions;
check price from the Board;
service-specific info;
fixed price or understood pricing model;
credit issuer;
preconditions;
service-defined constraints.
```

The algorithm used to search for compatible offerings is implementation-dependent unless a specific CR2SE service defines stricter matching rules.

---

## 43. Board Validation

A version 1 Board is structurally valid when:

```text
version exists and equals 1;

providedServices exists and is an array;

wantedServices exists and is an array;

every offering has a non-empty id;

offering IDs are unique within the Board;

every offering has a non-empty service identifier;

every offering has a positive serviceVersion;

every offering has a valid creditIssuer;

every offering has exactly one of `price` or `pricing`;

every fixed `price` is at least one credit;

every `pricing` object has a non-empty model identifier;

an offering using a known pricing model satisfies that model's required fields, types, limits, and relations;

checkPrice, when present, is at least one credit;

every offering has a non-empty description;

no offering contains input, output, or check schemas;

standard fields use the types required by this specification.
```

An offering containing malformed standard fields must not be interpreted as a valid offering.

An implementation may reject only the malformed offering rather than discarding the entire Board when doing so is safe.

This is recommended because Boards are extensible and one malformed offering should not unnecessarily hide unrelated valid offerings.

---

## 44. Untrusted Input

Boards received from peers are untrusted input.

Implementations must not assume that a Board is well formed merely because it came from a CR2SE peer.

Implementations should protect themselves against unreasonable values such as:

```text
extremely large JSON documents;

extremely large arrays;

extreme object nesting;

very long strings;

duplicate identifiers;

invalid identity IDs.
```

Exact resource limits are implementation-dependent.

A malformed Board must not cause memory corruption, integer overflow, uncontrolled allocation, or other unsafe behavior.

---

## 45. Board Size

CR2SE does not require implementations to accept arbitrarily large Boards.

Implementations must enforce a configurable maximum Board size.

The exact maximum is implementation-dependent unless a future CR2SE version defines a minimum interoperability limit.

Nodes should keep Boards reasonably compact.

Large resources and service schemas must not be embedded in the Board.

The Board describes service summaries and offering terms, not service type definitions or the data exchanged through services.

---

## 46. Ordering

The order of offerings inside:

```text
providedServices
```

and:

```text
wantedServices
```

does not assign priority unless a future specification explicitly defines such behavior.

For example:

```json
[
  {
    "id": "A"
  },
  {
    "id": "B"
  }
]
```

does not inherently mean:

```text
A is preferred over B.
```

Applications must not derive economic or semantic priority solely from array position.

---

## 47. Duplicate Services

Several offerings may use the same service identifier.

This is valid and expected.

For example:

```json
[
  {
    "id": "small",
    "service": "example.compute",
    "serviceVersion": 1
  },
  {
    "id": "large",
    "service": "example.compute",
    "serviceVersion": 1
  }
]
```

The offering ID selects the particular advertised variant.

A service invocation mechanism should therefore identify the offering being invoked rather than assuming that the service identifier alone uniquely selects one entry.

---

## 48. Empty Boards

A Board may contain no offerings.

For example:

```json
{
  "version": 1,
  "providedServices": [],
  "wantedServices": []
}
```

This is a valid Board.

It represents an identity that currently advertises no provided or wanted services.

---

## 49. Example Interaction

Suppose Alice publishes:

```json
{
  "version": 1,
  "providedServices": [
    {
      "id": "temperature",
      "service": "example.weather.current",
      "serviceVersion": 1,
      "description": "Returns the current temperature in whole degrees Celsius using the provider's configured observation source.",
      "creditIssuer": "ALICE_ID",
      "price": 1
    }
  ],
  "wantedServices": []
}
```

Bob retrieves Alice's Board.

Bob discovers:

```text
Offering ID:
    temperature

Service:
    example.weather.current

Service version:
    1

Price:
    1 Alice credit
```

The Board is enough for discovery and economic selection. Before invocation, Bob retrieves the definition of offering `temperature` with `service.get`. The definition tells Bob that the input has a described `location` string field, the output has a described `temperatureCelsius` `int32` field, and how the check works.

Bob's application may then decide to invoke:

```text
offering "temperature"
```

with:

```text
location = "Berlin"
```

The service invocation layer transports the request.

Alice processes the service according to the service's rules.

The Ledger handles the corresponding credit relationship.

The service returns the result.

The Board's role was to make the offering discoverable. The separately retrieved service definition made its typed contract interpretable before invocation.

---

# Summary

A CR2SE Board is a versioned JSON description of an identity's advertised service relationships.

A Board contains:

```text
providedServices
    services the publisher is willing to provide;

wantedServices
    services the publisher wants other identities to provide.
```

Each offering has:

```text
id
    identifies the particular advertised offering;

service
    identifies the logical operation;

serviceVersion
    identifies the exact contract version;

creditIssuer
    identifies the credits used for payment;

price or pricing
    defines either a fixed integer price or a deterministic service-defined pricing model; every final price is at least one credit.
```

Every offering also has a non-empty `description` that summarizes the service for discovery.

An offering may additionally describe:

```text
description;
service-specific information;
preconditions;
separate check price;
implementation suggestions.
```

Boards never contain service input, output, or check schemas. Every advertised offering instead has a definition retrievable by its Board `id` through `service.get`. The definition repeats the service identity and description and contains the typed input, output, and check contracts.

Different service terms or pricing models should normally be represented as different offerings. One deterministic model may cover a bounded range of requester-selected inputs.

Credits use the unsigned 64-bit integer model defined by the Ledger.

Input, output, and check schemas in the separate service definition use the language-independent logical type system defined by the [CR2SE Services specification](./Services.md).

The Board describes service summaries and offering-specific terms. It does not describe the typed interface.

It does not define the internal implementation of the service, the transport of large data, identity cryptography, ledger storage, or service-specific behavior.

Those concerns belong to their respective CR2SE layers and service specifications.
