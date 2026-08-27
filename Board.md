# CR2SE Board

The CR2SE Board describes the services an identity is willing to provide and the services it wants other identities to provide.

The Board is the service-discovery layer of CR2SE.

It answers questions such as:

```text
What services does this peer provide?

What services does this peer want?

What does a particular service cost?

Which credit is used for payment?

What input does the service accept?

What output does the service produce?

What conditions must be satisfied before the service may be invoked?
```

The Board does not define the behavior of every possible service.

For example, the Board may advertise a storage service, but the rules governing storage belong to the CR2SE Storage specification.

Likewise, an implementation may advertise custom services that are not defined by CR2SE.

The Board defines how those services are described in a common, machine-readable form.

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

---

## 5. Provided Services

`providedServices` contains services that the Board publisher is willing to provide to other identities.

For example:

```json
{
  "version": 1,
  "providedServices": [
    {
      "id": "temperature-default",
      "service": "example.weather.current",
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

If Alice publishes this Board, the entry means:

```text
Alice provides example.weather.current.
```

It does not mean that every invocation must succeed.

Whether an invocation is accepted depends on the service, its requirements, the identities involved, the local ledger, trust, available resources, and local policy.

---

## 6. Wanted Services

`wantedServices` contains services that the Board publisher wants other identities to provide.

For example:

```json
{
  "version": 1,
  "providedServices": [],
  "wantedServices": [
    {
      "id": "storage-1g-10d",
      "service": "cr2se.storage.store",
      "description": "Store up to 1 GB for 10 days."
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

If Alice publishes this Board, the entry means:

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

For example, these may be separate offerings:

```text
store up to 1 GB for 10 days for 5 credits;

store up to 1 GB for 30 days for 12 credits;

store up to 10 GB for 10 days for 40 credits.
```

Even though all three perform storage, they represent different advertised terms.

They must therefore be represented as separate offerings.

For example:

```json
{
  "providedServices": [
    {
      "id": "store-1g-10d",
      "service": "cr2se.storage.store"
    },
    {
      "id": "store-1g-30d",
      "service": "cr2se.storage.store"
    },
    {
      "id": "store-10g-10d",
      "service": "cr2se.storage.store"
    }
  ]
}
```

The service defines the operation.

The offering defines one advertised variant of that operation.

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
      "service": "cr2se.storage.store"
    },
    {
      "id": "storage",
      "service": "cr2se.storage.store"
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

## 9. Service Identifier

Every offering must contain a `service` field.

For example:

```json
"service": "cr2se.storage.store"
```

The service identifier describes the operation implemented by the offering.

A service identifier is a non-empty UTF-8 string.

The same service identifier may appear in several offerings.

For example:

```json
[
  {
    "id": "store-small-short",
    "service": "cr2se.storage.store"
  },
  {
    "id": "store-small-long",
    "service": "cr2se.storage.store"
  }
]
```

These are two offerings of the same service.

A service identifier therefore must not be treated as an offering identifier.

The `id` identifies the particular offering.

The `service` identifies what kind of operation the offering performs.

---

## 10. Service Namespaces

Service names beginning with:

```text
cr2se.
```

are reserved for services defined by CR2SE specifications.

For example:

```text
cr2se.storage.store
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

An offering may contain a human-readable `description`.

For example:

```json
"description": "Store up to 1 GB of data for 10 days."
```

The description is a UTF-8 string.

It exists for:

```text
users;
developers;
debugging;
service discovery interfaces;
human-readable documentation.
```

Programs must not depend on parsing the description to determine service behavior.

Machine-readable service rules belong in fields defined by the service specification.

For example, a Storage specification may define machine-readable fields describing storage size and retention period.

The description may explain those terms in more detail for humans.

---

## 12. Offering Information

An offering may contain an `info` object.

`info` contains service-specific information.

For example:

```json
{
  "info": {
    "maximumBytes": 1000000000,
    "periodDays": 10
  }
}
```

The meaning of `info` is defined by the service.

The Board specification does not assign universal meaning to arbitrary fields inside `info`.

For example:

```text
maximumBytes
periodDays
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

## 13. Different Terms Are Different Offerings

A single offering should describe one coherent set of service terms.

Different pricing or substantially different service conditions should normally be represented as different offerings.

For example:

```json
{
  "providedServices": [
    {
      "id": "storage-1g-10d",
      "service": "cr2se.storage.store",
      "description": "Store up to 1 GB for 10 days.",
      "info": {
        "maximumBytes": 1000000000,
        "periodDays": 10
      }
    },
    {
      "id": "storage-1g-30d",
      "service": "cr2se.storage.store",
      "description": "Store up to 1 GB for 30 days.",
      "info": {
        "maximumBytes": 1000000000,
        "periodDays": 30
      }
    }
  ]
}
```

This is preferred over creating one offering containing a complex price table when the alternatives can naturally be described as independent offerings.

The service specification determines which differences are significant enough to require separate offerings.

---

## 14. Credits Used for Payment

An offering that requires credit payment uses `creditIssuer` to identify the issuer of the credits used for that offering.

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
  "service": "cr2se.storage.store",
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

An offering that has a fixed advertised credit price contains a `price`.

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
0 .. 18446744073709551615
```

This uses the same credit amount representation defined by the Ledger specification.

Fractional credits do not exist.

Therefore values such as:

```json
"price": 0.01
```

are invalid CR2SE credit prices.

---

## 18. Zero Price

A price of zero is valid.

For example:

```json
{
  "creditIssuer": "ALICE_ID",
  "price": 0
}
```

describes a service that currently requires no credit payment.

A service may therefore be exposed through the same Board mechanism whether it is paid or free.

A service specification or implementation may still impose non-credit requirements.

---

## 19. Fixed Offering Price

The `price` field is the price of the offering described by that Board entry.

For example:

```json
{
  "id": "storage-1g-10d",
  "service": "cr2se.storage.store",
  "creditIssuer": "ALICE_ID",
  "price": 5,
  "description": "Store up to 1 GB for 10 days."
}
```

means that the advertised service variant costs:

```text
5 Alice credits
```

The Board does not interpret this as:

```text
5 credits per byte
```

or:

```text
5 credits per day
```

or any other implicit pricing formula.

If a service has multiple useful combinations of terms and prices, they may be advertised as several offerings.

For example:

```json
[
  {
    "id": "storage-1g-10d",
    "service": "cr2se.storage.store",
    "creditIssuer": "ALICE_ID",
    "price": 5,
    "info": {
      "maximumBytes": 1000000000,
      "periodDays": 10
    }
  },
  {
    "id": "storage-1g-30d",
    "service": "cr2se.storage.store",
    "creditIssuer": "ALICE_ID",
    "price": 12,
    "info": {
      "maximumBytes": 1000000000,
      "periodDays": 30
    }
  }
]
```

The Storage specification determines the exact meaning of fields such as `maximumBytes` and `periodDays`.

The Board only provides the common mechanism for advertising the variants.

---

## 20. Services Without a Board Price

Some future services may require pricing behavior that cannot reasonably be represented by one fixed Board price.

For example, a service could determine its final cost from work performed during the operation.

Such behavior must be defined by the specification of that service.

The Board must not invent implicit pricing formulas from arbitrary service metadata.

If `price` is absent, the service specification must define how the cost becomes known before credits are committed.

This is consistent with the Ledger requirement that a cost must be known before a credit-charging operation is committed.

Implementations should prefer fixed-price offerings where practical because they are simpler to discover, compare, and reason about.

---

## 21. Input Schema

An offering may contain an `input` field.

The `input` field describes the logical input accepted by the service.

It does not contain the input of a particular invocation.

For example:

```json
{
  "input": {
    "type": "object",
    "fields": {
      "location": {
        "type": "string"
      }
    }
  }
}
```

means conceptually:

```text
input:
    location: string
```

An actual invocation might later contain:

```text
location = "Berlin"
```

The Board describes the interface.

The invocation carries the value.

---

## 22. Output Schema

An offering may contain an `output` field.

The `output` field describes the logical result produced by the service.

For example:

```json
{
  "output": {
    "type": "object",
    "fields": {
      "temperature": {
        "type": "int32"
      }
    }
  }
}
```

means conceptually:

```text
output:
    temperature: int32
```

The Board does not contain the actual result.

---

## 23. Type Descriptions

CR2SE version 1 defines a small language-independent type vocabulary for Board input and output schemas.

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

These types describe logical values.

They do not define how those values must be represented internally by an implementation.

For example:

```text
uint64
```

may map to different native language types in C, Rust, Java, Python, or another implementation language.

---

## 24. `bool`

`bool` represents a boolean value.

Its logical values are:

```text
true
false
```

Example:

```json
{
  "type": "bool"
}
```

---

## 25. `int32`

`int32` represents a signed 32-bit integer.

Its range is:

```text
-2147483648 .. 2147483647
```

Example:

```json
{
  "type": "int32"
}
```

---

## 26. `int64`

`int64` represents a signed 64-bit integer.

Its range is:

```text
-9223372036854775808 .. 9223372036854775807
```

Example:

```json
{
  "type": "int64"
}
```

---

## 27. `uint32`

`uint32` represents an unsigned 32-bit integer.

Its range is:

```text
0 .. 4294967295
```

Example:

```json
{
  "type": "uint32"
}
```

---

## 28. `uint64`

`uint64` represents an unsigned 64-bit integer.

Its range is:

```text
0 .. 18446744073709551615
```

Example:

```json
{
  "type": "uint64"
}
```

---

## 29. `float`

`float` represents an IEEE 754 binary32 floating-point value.

Example:

```json
{
  "type": "float"
}
```

The service specification must define whether special values such as infinity or NaN are meaningful if they may occur.

---

## 30. `double`

`double` represents an IEEE 754 binary64 floating-point value.

Example:

```json
{
  "type": "double"
}
```

The service specification must define whether special values such as infinity or NaN are meaningful if they may occur.

---

## 31. `string`

`string` represents Unicode text.

Example:

```json
{
  "type": "string"
}
```

When represented as JSON, the value follows the JSON string rules.

---

## 32. `bytes`

`bytes` represents an arbitrary sequence of bytes.

Example:

```json
{
  "type": "bytes"
}
```

The type does not imply that the actual bytes must be embedded directly in JSON.

For example, a storage service could logically accept:

```text
data: bytes
```

where the data is several gigabytes in size.

The Board describes the logical service interface.

The protocol used to invoke the service determines how the actual byte sequence is transported.

Large binary values may therefore be streamed through CR2SE network frames rather than encoded as one large JSON value.

The Board schema must not be interpreted as requiring large resources to fit in memory or to be Base64-encoded into a JSON document.

---

## 33. Object Type

An object contains named fields.

Example:

```json
{
  "type": "object",
  "fields": {
    "chunkId": {
      "type": "string"
    },
    "data": {
      "type": "bytes"
    }
  }
}
```

This describes:

```text
object
    chunkId: string
    data: bytes
```

`fields` must be a JSON object.

Each property name is a field name.

Each property value is another CR2SE type description.

Objects may therefore be nested.

For example:

```json
{
  "type": "object",
  "fields": {
    "location": {
      "type": "object",
      "fields": {
        "latitude": {
          "type": "double"
        },
        "longitude": {
          "type": "double"
        }
      }
    }
  }
}
```

---

## 34. Array Type

An array contains zero or more values described by one item schema.

Example:

```json
{
  "type": "array",
  "items": {
    "type": "string"
  }
}
```

This describes:

```text
array of string
```

Arrays may contain objects.

For example:

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "fields": {
      "id": {
        "type": "string"
      },
      "size": {
        "type": "uint64"
      }
    }
  }
}
```

Composite types may be nested to arbitrary practical depth.

Implementations should enforce reasonable nesting limits when parsing untrusted Boards.

The exact limit is implementation-dependent.

---

## 35. Optional Fields

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
      "type": "string"
    },
    "limit": {
      "type": "uint32",
      "optional": true
    }
  }
}
```

means:

```text
query is required.

limit is optional.
```

The value:

```json
"optional": false
```

has the same meaning as omitting `optional`.

`optional` applies to a field within an object.

---

## 36. Schema and Wire Encoding

Board schemas describe logical service values.

They do not define the peer-to-peer wire encoding used to transport every service input or result.

For example:

```text
input:
    document: bytes
```

describes what the service consumes.

It does not require:

```text
JSON;
Protocol Buffers;
CBOR;
one CR2SE frame;
one in-memory byte array.
```

The service invocation mechanism and the service specification determine how actual values are transmitted.

This separation is important because the same Board schema must be usable for both small values and very large streamed resources.

---

## 37. Preconditions

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

## 38. Identity Preconditions

A service that requires the remote participant to prove control of a CR2SE identity may advertise the standard identity precondition:

```json
"cr2se.identity"
```

The identity proof uses the identity and cryptographic mechanisms defined by the CR2SE Identity and Encryption specifications.

The Board does not redefine those cryptographic operations.

It only declares that successful identity proof is required by the offering.

---

## 39. Multiple Preconditions

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

## 40. Offering Example

A complete offering could look like:

```json
{
  "id": "weather-current",
  "service": "example.weather.current",
  "description": "Returns the current temperature for a location.",
  "creditIssuer": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567ABCDEFGHIJKLMNOP",
  "price": 1,
  "preconditions": [
    "cr2se.identity"
  ],
  "input": {
    "type": "object",
    "fields": {
      "location": {
        "type": "string"
      }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "temperatureCelsius": {
        "type": "int32"
      }
    }
  }
}
```

The Board layer can determine:

```text
the offering identifier;

the service identifier;

the human-readable description;

which credits are used;

the fixed advertised price;

the required preconditions;

the logical input;

the logical output.
```

The Board does not need to know how the weather service obtains temperature information.

---

## 41. Storage Example

The following is illustrative.

The exact storage fields and semantics belong to `Storage.md`.

```json
{
  "id": "store-1g-10d",
  "service": "cr2se.storage.store",
  "description": "Store up to 1 GB for 10 days.",
  "creditIssuer": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567ABCDEFGHIJKLMNOP",
  "price": 5,
  "preconditions": [
    "cr2se.identity"
  ],
  "info": {
    "maximumBytes": 1000000000,
    "periodDays": 10
  },
  "input": {
    "type": "object",
    "fields": {
      "chunkId": {
        "type": "string"
      },
      "data": {
        "type": "bytes"
      }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "success": {
        "type": "bool"
      }
    }
  }
}
```

Another storage variant may be:

```json
{
  "id": "store-1g-30d",
  "service": "cr2se.storage.store",
  "description": "Store up to 1 GB for 30 days.",
  "creditIssuer": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567ABCDEFGHIJKLMNOP",
  "price": 12,
  "info": {
    "maximumBytes": 1000000000,
    "periodDays": 30
  }
}
```

These are separate offerings.

There is no Board-level concept such as:

```text
pricePerByte
```

or:

```text
pricePerDay
```

unless a particular service specification explicitly introduces such information for that service.

---

## 42. Complete Board Example

A Board may contain both wanted and provided services.

For example:

```json
{
  "version": 1,

  "providedServices": [
    {
      "id": "temperature-current",
      "service": "example.weather.current",
      "description": "Returns the current temperature.",
      "creditIssuer": "ALICE_ID",
      "price": 1,
      "input": {
        "type": "object",
        "fields": {
          "location": {
            "type": "string"
          }
        }
      },
      "output": {
        "type": "object",
        "fields": {
          "temperatureCelsius": {
            "type": "int32"
          }
        }
      }
    }
  ],

  "wantedServices": [
    {
      "id": "storage-1g-10d",
      "service": "cr2se.storage.store",
      "description": "Store up to 1 GB for 10 days.",
      "creditIssuer": "ALICE_ID",
      "price": 5,
      "info": {
        "maximumBytes": 1000000000,
        "periodDays": 10
      },
      "input": {
        "type": "object",
        "fields": {
          "chunkId": {
            "type": "string"
          },
          "data": {
            "type": "bytes"
          }
        }
      },
      "output": {
        "type": "object",
        "fields": {
          "success": {
            "type": "bool"
          }
        }
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
    cr2se.storage.store
        Alice wants storage.
        Alice offers 5 Alice credits.
```

---

## 43. Board State

A Board describes the services and terms currently advertised by its publisher.

A Board may change.

For example, an identity may:

```text
add an offering;
remove an offering;
change a price;
change service-specific information;
change a description;
change preconditions.
```

A peer must not assume that a previously retrieved Board remains permanently valid.

How often Boards are refreshed or cached is implementation-dependent.

---

## 44. Offering Removal

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

CR2SE does not require a separate deletion record.

The current Board is the current advertised set.

---

## 45. Offering Changes

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

## 46. Unknown Fields

A version 1 implementation must tolerate fields it does not understand.

For example:

```json
{
  "id": "example",
  "service": "example.operation",
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
type descriptions;
service-specific info.
```

An implementation may preserve unknown fields when passing Board JSON to applications.

---

## 47. Unknown Services

A Board may contain a service identifier unknown to the receiving node.

For example:

```json
{
  "service": "someone.newService"
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

## 48. Unknown Types

If an offering uses an input or output type an implementation does not understand, the complete Board remains readable.

However, the implementation must not pretend that it understands how to construct or validate values of that type.

Applications that understand an extension may still use it.

Standard CR2SE services should use the standard type vocabulary unless their specification explicitly defines an extension.

---

## 49. Unknown Preconditions

Unknown preconditions behave similarly.

The Board remains valid.

The particular offering must not be treated as automatically satisfying a precondition that the implementation does not understand.

This prevents extension compatibility from accidentally removing access requirements.

---

## 50. Board and Ledger

The Board and Ledger solve different problems.

The Board describes:

```text
what services are wanted;

what services are provided;

what credits an offering uses;

what an offering costs;

what data the service consumes and produces.
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

## 51. Board and Identity

The Board uses CR2SE identities where identities are required.

For example:

```text
creditIssuer
```

contains a CR2SE identity ID.

The Board does not define identity generation, signing keys, identity encoding, or identity proof.

Those concepts are defined by the CR2SE Identity and Encryption specifications.

---

## 52. Board and Network

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

## 53. Board and Node API

The Node API provides local applications with operations for interacting with a CR2SE node.

In particular, the Node API defines an operation logically equivalent to:

```text
board.get
```

which retrieves a remote peer's Board.

The value returned by that operation follows the schema defined by this document.

Likewise, service invocation through the Node API uses offerings discovered through Boards.

The Node API defines the application-to-local-node interface.

The Board defines the service information being discovered.

These are separate layers.

---

## 54. Selecting an Offering

An application may select an offering using information from the Board.

For example:

```text
Alice provides:

storage-1g-10d
    5 credits

storage-1g-30d
    12 credits

storage-10g-10d
    40 credits
```

A remote application may choose whichever offering satisfies its needs.

Selection policy is not defined by the Board.

An implementation may consider:

```text
price;
trust;
available credits;
service terms;
local application preferences;
service-specific metadata.
```

CR2SE does not require one universal algorithm for choosing between offerings.

---

## 55. Matching Wanted and Provided Services

Wanted and provided services may be used for discovery.

For example:

```text
Alice wants:
    cr2se.storage.store

Bob provides:
    cr2se.storage.store
```

This indicates that Alice and Bob may be able to exchange a storage service.

Matching the service identifier alone does not necessarily mean the offerings are compatible.

Applications may also need to compare:

```text
input and output schemas;
service-specific info;
price;
credit issuer;
preconditions;
service-defined constraints.
```

The algorithm used to search for compatible offerings is implementation-dependent unless a specific CR2SE service defines stricter matching rules.

---

## 56. Board Validation

A version 1 Board is structurally valid when:

```text
version exists and equals 1;

providedServices exists and is an array;

wantedServices exists and is an array;

every offering has a non-empty id;

offering IDs are unique within the Board;

every offering has a non-empty service identifier;

standard fields use the types required by this specification.
```

An offering containing malformed standard fields must not be interpreted as a valid offering.

An implementation may reject only the malformed offering rather than discarding the entire Board when doing so is safe.

This is recommended because Boards are extensible and one malformed custom offering should not unnecessarily hide unrelated valid offerings.

---

## 57. Untrusted Input

Boards received from peers are untrusted input.

Implementations must not assume that a Board is well formed merely because it came from a CR2SE peer.

Implementations should protect themselves against unreasonable values such as:

```text
extremely large JSON documents;

extremely large arrays;

extreme object nesting;

very long strings;

very large schemas;

duplicate identifiers;

invalid identity IDs.
```

Exact resource limits are implementation-dependent.

A malformed Board must not cause memory corruption, integer overflow, uncontrolled allocation, or other unsafe behavior.

---

## 58. Board Size

CR2SE does not require implementations to accept arbitrarily large Boards.

Implementations must enforce a configurable maximum Board size.

The exact maximum is implementation-dependent unless a future CR2SE version defines a minimum interoperability limit.

Nodes should keep Boards reasonably compact.

Large resources themselves must not be embedded in the Board.

The Board describes services and schemas, not the data exchanged through those services.

---

## 59. Ordering

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

## 60. Duplicate Services

Several offerings may use the same service identifier.

This is valid and expected.

For example:

```json
[
  {
    "id": "small",
    "service": "example.compute"
  },
  {
    "id": "large",
    "service": "example.compute"
  }
]
```

The offering ID selects the particular advertised variant.

A service invocation mechanism should therefore identify the offering being invoked rather than assuming that the service identifier alone uniquely selects one entry.

---

## 61. Empty Boards

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

## 62. Example Interaction

Suppose Alice publishes:

```json
{
  "version": 1,
  "providedServices": [
    {
      "id": "temperature",
      "service": "example.weather.current",
      "creditIssuer": "ALICE_ID",
      "price": 1,
      "input": {
        "type": "object",
        "fields": {
          "location": {
            "type": "string"
          }
        }
      },
      "output": {
        "type": "object",
        "fields": {
          "temperatureCelsius": {
            "type": "int32"
          }
        }
      }
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

Price:
    1 Alice credit

Input:
    location: string

Output:
    temperatureCelsius: int32
```

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

The Board's role was to make the offering discoverable and interpretable before the invocation occurred.

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
    identifies the logical operation.
```

An offering may additionally describe:

```text
description;
credit issuer;
fixed integer credit price;
service-specific information;
preconditions;
input schema;
output schema.
```

Different service terms or prices should normally be represented as different offerings.

Credits use the unsigned 64-bit integer model defined by the Ledger.

Input and output schemas use a language-independent logical type system inspired by RPC interface descriptions.

The Board describes the logical interface of a service.

It does not define the internal implementation of the service, the transport of large data, identity cryptography, ledger storage, or service-specific behavior.

Those concerns belong to their respective CR2SE layers and service specifications.
