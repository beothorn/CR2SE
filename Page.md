# CR2SE Page

CR2SE Page is a standard, paid service for retrieving static resources
published by a CR2SE identity. A **publisher** is the identity providing the
service. A **visitor** is the identity requesting and paying for a resource. A
**path** is the textual name of one published item. A **media type** is a label
describing a byte representation. **Content** is one finite byte sequence. A
**resource** associates one path, one media type, and content. A **page** is the
publisher's collection of resources.

The page can represent a personal profile, an organization page, a blog, a
recipe, a document, or another collection whose returned bytes do not depend on
the visitor or on server-side application execution. The simplest page has one
HTML resource. A larger page can add images, style sheets, scripts,
downloadable files, and more HTML resources.

Common terms such as **CR2SE identity**, **service**, **offering**,
**invocation**, **service requester**, **service provider**, **credit issuer**,
and **check** are defined in the [CR2SE Glossary](./Glossary.md). The visitor is
the service requester and the publisher is the service provider. Common
invocation, charging, and service-definition rules are defined in
[Services](./Services.md). Board advertisements are defined in
[Board](./Board.md), identity authentication in [Identity](./Identity.md), and
transport-independent invocation in [NodeApi](./NodeApi.md).

This document defines the complete observable Page version 1 contract. An
implementation may be a library, a standalone peer, or part of another
application and may use any programming language.

---

## 1. Version 1 service

The version 1 Page service is identified by:

```text
service:        cr2se.page
serviceVersion: 1
pricing:        fixed Board price
```

It has one operation:

```text
get
    Return one current static resource selected by its path.
```

Every successful `get` costs the fixed `price` in the selected Board offering.
Missing resources and other failed invocations are not charged. Version 1 has
no network operation for publishing, editing, deleting, or listing resources.
Those actions are local to the publisher.

All sizes are measured in bytes. All protocol integers use the ranges of their
declared types. Fixed-width integer arithmetic must never wrap.

---

## 2. Bytes, text, and hashes

A **byte string** is an ordered sequence of bytes. Its length is the number of
bytes, not characters.

A **UTF-8 string** is a byte string containing one valid, shortest-form UTF-8
encoding. Surrogate code points, overlong encodings, and invalid byte sequences
are forbidden. Unicode normalization is not performed. Two UTF-8 strings are
equal only when their encoded bytes are equal.

`uint64` means an unsigned 64-bit integer in the range `0 .. 2^64-1`.

`SHA-256(data)` means the 32-byte SHA-256 result for the exact bytes in `data`,
as defined by FIPS 180-4. Protocol fields contain the raw 32 bytes, not
hexadecimal text. A user interface may display a hash as 64 lowercase
hexadecimal digits.

The SHA-256 value of an empty byte string is:

```text
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

---

## 3. Canonical paths

A **path component** is one UTF-8 string naming one level within a page. Its
UTF-8 encoding contains between 1 and 255 bytes. A component must not:

```text
equal "." or "..";
contain U+0000 through U+001F or U+007F;
contain slash U+002F;
contain reverse solidus U+005C.
```

A **canonical path** is either the one-byte string `/`, called the **root
path**, or a slash followed by one or more path components separated by single
slashes. A non-root canonical path has no trailing slash.

Examples are:

```text
/
/about
/posts/first-post.html
/images/photo.jpg
```

These are not canonical paths:

```text
about              no initial slash
/about/            trailing slash
//about             empty component
/a/./b              dot component
/a/../b             parent component
/images\photo.jpg   reverse solidus
```

The path is a protocol string, not a filesystem path or URI. Percent signs are
ordinary characters and are not decoded. Question marks and number signs are
ordinary characters and do not introduce a query or fragment. A viewer that
maps browser URLs to Page paths must perform that mapping before invoking this
service and must supply the resulting canonical path exactly once; it must not
apply repeated percent decoding.

Canonical paths are case-sensitive and normalization-sensitive. For example,
`/About` and `/about` are different. Visually identical Unicode strings with
different UTF-8 encodings are also different. A publisher should normally use
simple lowercase ASCII paths for portable human use.

The **path size** is the number of bytes in the path's UTF-8 encoding. It must
not exceed the selected offering's `maximumPathBytes`.

The protocol path need not equal a local storage path. A provider must validate
the complete path before using it and must not permit a path to escape the
configured page root. It may store resources in files, a database, memory, an
archive, or any other representation that preserves the behavior defined here.

---

## 4. Media types

A **media type** is a UTF-8 string labeling the representation of a resource's
content. In Page version 1 it has the exact form:

```text
type/subtype
```

`type` and `subtype` each contain between 1 and 63 lowercase ASCII characters.
Every character must be one of:

```text
a through z
0 through 9
! # $ & ^ _ . + -
```

There is exactly one slash, with no whitespace or parameters. Valid examples
include:

```text
text/html
text/css
text/plain
application/javascript
application/json
image/jpeg
image/png
image/svg+xml
application/octet-stream
```

The media type describes the content; it does not transform it. Page performs
no content negotiation, transfer compression, character-set conversion, or
automatic decompression. Textual resources should use UTF-8. A visitor that
does not recognize or trust a media type may save the bytes or treat them as
`application/octet-stream` instead of interpreting them.

---

## 5. Resources and pages

A **resource** consists of:

```text
path
media type
content
```

Its **content size** is the exact number of content bytes. Empty content is
permitted. Its **content hash** is:

```text
SHA-256(content)
```

Within one page, at most one current resource exists at a canonical path. A
**page address** is the pair:

```text
(publisher identity, canonical path)
```

The publisher identity selects the page. The path selects one resource in that
page. An offering ID selects economic terms for retrieving the resource; it is
not part of the page address.

While a publisher advertises a Page offering, its root path must exist, fit the
offering's limits, and have media type `text/html`. Other paths are optional.
No listing operation is required. A visitor learns additional paths from the
root HTML, other retrieved resources, a Board description, or an external
source.

All Page offerings published concurrently by one identity expose the same
logical page. They may have different prices or size limits. If a resource is
larger than a selected offering permits, that invocation fails even when a
different offering from the same publisher would permit it.

A publisher may replace or remove a resource between invocations. Each
successful invocation returns one self-consistent snapshot: its metadata and
content all describe the same byte sequence. Changing a resource during a
transfer must not produce mixed old and new bytes. Page version 1 promises
neither immutability nor a retention period.

The word static describes how an output is produced, not how long it remains
published. For a given accepted invocation, the returned content is selected
only by the publisher identity and canonical path. It must not vary according
to the visitor identity, cookies, request history, time, random values, credit
balance beyond payment authorization, or other visitor-specific input.

A publisher may generate files before making them available, but `get` must
retrieve the already published resource. It must not execute server-side page
logic, templates, database queries, or visitor-supplied code to create the
response. Client-side code contained in a retrieved resource is content and
does not make the Page service itself dynamic.

---

## 6. Discovery and links

A publisher announces Page through a provided-service offering on its Board.
The Board identifies the publisher because the Board belongs to that identity.
Page version 1 does not define a global directory, name system, search engine,
or mapping from human names to identities.

To visit a known identity's page, an application:

1. obtains and authenticates the publisher identity;
2. retrieves a current Board for that identity;
3. selects a compatible `cr2se.page` version 1 offering;
4. invokes `get` for `/`;
5. verifies the result before interpreting it.

HTML links, images, style sheets, and scripts can refer to other paths. Page
version 1 does not define a URI scheme or require a general-purpose web browser.
A Page viewer may resolve a relative reference against the retrieved canonical
path and then request the resulting path from the same publisher. It may also
support application-defined links to other CR2SE identities or ordinary
Internet URLs. Such link handling is outside the Page service contract.

An HTML resource cannot cause another resource to be returned as part of the
same invocation. Every additional Page resource requires a separate successful
`get` invocation and therefore costs the selected offering's fixed price.
Viewers should not fetch referenced resources without considering cost and
local safety policy.

---

## 7. Board offering and price

A version 1 Page offering uses the Board's fixed `price` field. It must not use
a `pricing` object. The price is an integer in `1 .. 2^64-1` expressed in the
credits identified by `creditIssuer`.

The offering's `info` object contains:

```text
maximumPathBytes
    Largest canonical-path UTF-8 byte length accepted by this offering.
    Range: 1 .. 65535.

maximumResourceBytes
    Largest content byte length returned by this offering.
    Range: 1 .. 2^64-1.
```

An empty resource fits every valid `maximumResourceBytes` value because its
content size is zero.

A complete offering has this shape:

```json
{
  "id": "page",
  "service": "cr2se.page",
  "serviceVersion": 1,
  "description": "Return static resources published as this identity's page.",
  "creditIssuer": "PUBLISHER_OR_ACCEPTED_ISSUER_ID",
  "price": 1,
  "info": {
    "maximumPathBytes": 4096,
    "maximumResourceBytes": 16777216
  },
  "preconditions": [
    "cr2se.identity"
  ]
}
```

The numbers are illustrative. Every version 1 offering must contain both shown
`info` fields and the `cr2se.identity` precondition. It must not contain
`checkPrice`, because the Page check is local and included in each successful
invocation.

The credit issuer need not be the publisher. The common Board and Ledger rules
determine whether the visitor and publisher accept the named issuer's credits.
The exact issuer and fixed price are agreed before the provider begins
returning content.

The price covers one complete `get` result, regardless of content size. A
publisher that needs different economics may advertise several offerings with
different fixed prices and limits. Version 1 has no per-byte pricing model.

---

## 8. Get operation

The visitor supplies:

```text
path:         string
maximumBytes: uint64
```

`path` must be a canonical path whose path size does not exceed
`maximumPathBytes` in the selected offering. `maximumBytes` is the largest
content size the visitor is willing to receive in this invocation. It must not
exceed the offering's `maximumResourceBytes`.

The provider validates the path and bounds before accepting the invocation. It
then locates one snapshot of the current resource. The invocation fails without
charge when:

```text
the input is invalid;
the path has no current resource;
the resource exceeds maximumBytes;
the resource exceeds the offering's maximumResourceBytes;
the resource metadata is invalid;
the provider cannot return a complete self-consistent snapshot.
```

A failure must not substitute an HTML error document or another resource as a
successful output. In particular, `/missing` must not silently return `/`.

A successful output contains:

```text
path:        string
mediaType:   string
contentSize: uint64
contentHash: bytes, exactly 32 bytes
content:     bytes, exactly contentSize bytes
price:       uint64 credits
```

The output path must equal the requested path byte for byte. `contentSize` and
`contentHash` describe the exact returned content. `price` must equal the fixed
price agreed from the selected offering.

The provider may stream `content` in bounded transport frames. Frame boundaries
are not part of the content and do not affect its hash. The provider must not
report success until it has returned the complete logical output. If the stream
ends early, the invocation fails and is not charged under the common service
rules.

The provider must authenticate as the publisher identity through the CR2SE
identity and connection mechanisms. Page adds no resource signature. A saved
result therefore proves no more to a third party than any other data copied
from an authenticated connection.

Each accepted `get` is an independent invocation. Repeating the same path can
return newer content and incurs a new price. Transport-level retransmission
that remains part of the same invocation is not a second invocation.

---

## 9. Verification check

The Page check is local verification of one successful `get` result. It sends
no additional request to the publisher. Exactly one logical check is included
in each successful invocation; an implementation may cache or recompute its
result without creating another service invocation or credit charge.

The check input contains:

```text
requestedPath
returned path
mediaType
contentSize
contentHash
content
agreed price
returned price
```

The visitor computes one outcome:

```text
pass
    The returned path equals requestedPath; the media type is valid;
    contentSize equals the number of content bytes; contentHash equals
    SHA-256(content); and the returned price equals the agreed price.

fail
    All values needed for the check are available, but at least one pass
    condition is false.

inconclusive
    A needed input is unavailable, or a local resource limit prevents the
    complete check.
```

The visitor calculates the outcome. It must not trust a publisher-supplied
claim that the result passed.

A pass establishes that the complete returned bytes and metadata are
self-consistent with the request and the agreed price, subject to SHA-256
collision resistance. Authentication of the CR2SE connection establishes
which identity returned them. A pass does not establish truth, safety,
authorship, legality, originality, continued availability, or endorsement of
linked resources.

The check does not reverse a charge or settle a dispute. The visitor may use
its outcome in a local trust decision under the common Services rules.

---

## 10. Required service definition

Every version 1 Page offering must expose a definition through `service.get`.
Its `id` and `description` match the selected Board offering. Its logical
schema is equivalent to:

```json
{
  "id": "page",
  "service": "cr2se.page",
  "serviceVersion": 1,
  "description": "Return static resources published as this identity's page.",
  "input": {
    "type": "object",
    "fields": {
      "path": {
        "type": "string",
        "description": "Canonical path of the requested resource within the publisher's page."
      },
      "maximumBytes": {
        "type": "uint64",
        "description": "Largest resource content size in bytes that the visitor accepts."
      }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "path": {
        "type": "string",
        "description": "Canonical path returned, exactly equal to the requested path."
      },
      "mediaType": {
        "type": "string",
        "description": "Lowercase type/subtype label for the returned content."
      },
      "contentSize": {
        "type": "uint64",
        "description": "Exact number of returned content bytes."
      },
      "contentHash": {
        "type": "bytes",
        "description": "Exact 32-byte SHA-256 hash of the returned content."
      },
      "content": {
        "type": "bytes",
        "description": "Complete static content bytes for the requested path."
      },
      "price": {
        "type": "uint64",
        "description": "Exact credits charged for the successful get invocation."
      }
    }
  },
  "check": {
    "description": "Locally verify that one complete get output matches its requested path, agreed price, declared size, media type, and SHA-256 content hash.",
    "input": {
      "type": "object",
      "fields": {
        "requestedPath": {
          "type": "string",
          "description": "Canonical path supplied in the checked get invocation."
        },
        "path": {
          "type": "string",
          "description": "Canonical path contained in the checked output."
        },
        "mediaType": {
          "type": "string",
          "description": "Media type contained in the checked output."
        },
        "contentSize": {
          "type": "uint64",
          "description": "Declared byte length contained in the checked output."
        },
        "contentHash": {
          "type": "bytes",
          "description": "Declared 32-byte SHA-256 content hash contained in the checked output."
        },
        "content": {
          "type": "bytes",
          "description": "Complete content bytes contained in the checked output."
        },
        "agreedPrice": {
          "type": "uint64",
          "description": "Fixed offering price accepted before the checked invocation."
        },
        "price": {
          "type": "uint64",
          "description": "Price contained in the checked output."
        }
      }
    },
    "output": {
      "type": "object",
      "fields": {
        "outcome": {
          "type": "string",
          "description": "Visitor-computed verification result: pass, fail, or inconclusive."
        }
      }
    }
  }
}
```

The schema describes logical values. JSON is not required on the peer-to-peer
wire. A language binding may expose a function, method, stream, iterator,
process interface, or language-native record. It must preserve the same UTF-8
strings, unsigned range, exact bytes, validation, fixed price, failure rules,
hash calculation, and observable behavior. Streaming chunks must concatenate
to exactly the logical `content` byte string.

---

## 11. Example

Alice operates a CR2SE identity and publishes this Page offering:

```json
{
  "id": "page",
  "service": "cr2se.page",
  "serviceVersion": 1,
  "description": "Return static resources published as this identity's page.",
  "creditIssuer": "ALICE_ID",
  "price": 1,
  "info": {
    "maximumPathBytes": 4096,
    "maximumResourceBytes": 16777216
  },
  "preconditions": ["cr2se.identity"]
}
```

Her local configuration maps `/` to an HTML file and `/portrait.png` to an
image file. Publication creates no CR2SE invocation and transfers no credits.

Bob authenticates Alice's identity, retrieves her Board, selects the offering,
and requests:

```text
path = "/"
maximumBytes = 1000000
```

Before content transfer, Bob accepts a price of one Alice credit. Alice returns
the root resource with `mediaType = "text/html"`, its exact size, SHA-256 hash,
and bytes. Bob checks the path, price, size, media type, and hash. The successful
invocation costs one Alice credit.

If Bob's viewer later requests `/portrait.png`, that is a second invocation and
costs one more Alice credit. If Bob requests `/missing`, Alice reports a service
failure and neither peer charges the Page price.

---

## 12. Failure, concurrency, and caching

Invalid input, unavailable content, exceeded limits, incomplete output, and
internal provider errors are service failures. A failure is not charged and
must not be represented as a successful resource.

Concurrent visitors are independent. Concurrent requests for the same path may
return different complete snapshots if publication changes between their
snapshot selections. One response must never combine metadata from one
snapshot with content from another.

A visitor may cache a successful output by publisher identity, path, and
content hash. Page version 1 defines no freshness period, expiry time,
conditional request, or promise that a cached resource is still current. A new
paid `get` is required to learn the publisher's current resource through this
service.

Several nodes may operate as one publisher identity. They are responsible for
serving a coherent page and compatible current Board. CR2SE does not
synchronize their files. If nodes return different resources for the same path,
each complete result can pass its local check, but visitors may treat the
inconsistency as a trust concern.

---

## 13. Security and interoperability requirements

Page content is untrusted input. A viewer must enforce local limits before
allocating storage, parsing, decompressing embedded formats, rendering HTML,
loading fonts, running scripts, following links, or writing files. A media type
is a publisher assertion, not proof that the bytes are safe or correctly
classified.

HTML, SVG, style sheets, scripts, and document formats can execute behavior,
load remote content, identify a visitor, consume resources, or exploit a
renderer. A general implementation should use sandboxing and should disable or
ask permission for active content and external network access. Authentication
identifies the publisher; it does not make the content trustworthy.

A provider must treat canonical paths as protocol values and safely map them to
local storage. It must reject invalid paths before filesystem access, avoid
directory traversal, avoid following unintended symbolic links, and prevent a
resource update from exposing partial content.

A conforming Page version 1 implementation must:

```text
recognize exactly (cr2se.page, 1);
retrieve only with the get operation defined here;
validate canonical UTF-8 paths and advertised bounds;
use the selected offering's fixed nonzero price;
return one complete, self-consistent resource snapshot;
calculate SHA-256 over the exact logical content bytes;
distinguish service failures from successful resources;
provide the included local check;
preserve full uint64 values without rounding or overflow;
authenticate the remote CR2SE identity through the common protocol;
avoid assuming JSON, a filesystem, HTTP, or a particular programming language.
```
