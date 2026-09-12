# Page pseudocode

This document translates [`Page.md`](../Page.md) into implementation-neutral
algorithms. The specification remains authoritative. All paths, metadata, and
content are untrusted; JSON below denotes logical values, not a required wire
encoding.

## 1. Constants and state

```text
SERVICE_ID = "cr2se.page"
SERVICE_VERSION = 1
IDENTITY_PRECONDITION = "cr2se.identity"
SHA256_SIZE = 32
UINT64_MAX = 18_446_744_073_709_551_615

PageTerms:
    fixedPrice                 uint64 in 1 .. UINT64_MAX
    maximumPathBytes           integer in 1 .. 65535
    maximumResourceBytes       uint64 in 1 .. UINT64_MAX

ResourceSnapshot:
    path                       canonical UTF-8 string
    mediaType                  valid lowercase type/subtype
    content                    immutable byte snapshot
```

## 2. Offering and input validation

```text
function validatePageOffering(offering):
    require offering.service == SERVICE_ID
    require offering.serviceVersion == SERVICE_VERSION
    require offering.price is exact integer in 1 .. UINT64_MAX
    require offering has no pricing member
    require offering has no checkPrice member
    require IDENTITY_PRECONDITION in offering.preconditions
    require offering.info has exactly the required Page members

    return PageTerms {
        fixedPrice: offering.price,
        maximumPathBytes: requireExactInteger(
            offering.info.maximumPathBytes, 1, 65535),
        maximumResourceBytes: requireExactInteger(
            offering.info.maximumResourceBytes, 1, UINT64_MAX)
    }

function validateCanonicalPath(path, maximumPathBytes):
    require path is valid shortest-form UTF-8
    bytes = UTF8.encode(path)
    require 1 <= length(bytes) <= maximumPathBytes
    if path == "/": return path
    require bytes begins with ASCII('/') and not ends with ASCII('/')
    components = split path at '/'; require components[0] == ""
    for component in components[1..]:
        require 1 <= byteLengthUtf8(component) <= 255
        require component not in {".", ".."}
        require component contains no '/', '\\', U+0000..U+001F, or U+007F
    return path

function validateMediaType(value):
    require value is valid UTF-8 and contains exactly one '/'
    (type, subtype) = split value at '/'
    require 1 <= length(type) <= 63 and 1 <= length(subtype) <= 63
    require every byte in both is one of lowercase ASCII letters, digits,
            or ASCII("!#$&^_.+-")
    return value
```

Percent signs, `?`, and `#` are ordinary path characters. No percent decoding
or Unicode normalization occurs.

## 3. Provider retrieval

```text
function getPageResource(requesterId, offeringSnapshot, input):
    terms = validatePageOffering(offeringSnapshot)
    path = validateCanonicalPath(input.path, terms.maximumPathBytes)
    maximumBytes = requireExactInteger(input.maximumBytes, 0, UINT64_MAX)
    require maximumBytes <= terms.maximumResourceBytes

    // Validate before accepting payment or starting a body stream.
    snapshot = resourceStore.openImmutableSnapshot(path)
    if snapshot is NONE: raise ServiceFailure("resource unavailable")
    mediaType = validateMediaType(snapshot.mediaType)
    size = snapshot.exactByteLength
    require size <= maximumBytes and size <= terms.maximumResourceBytes

    reservation = ledger.reserveCharge(
        requesterId, offeringSnapshot.creditIssuer, terms.fixedPrice)
    try:
        bytes = streamExactly(snapshot.content, size)
        hash = SHA256(bytes)
        output = {
            path: path, mediaType: mediaType, contentSize: size,
            contentHash: hash, content: bytes, price: terms.fixedPrice
        }
        ledger.commitReservation(reservation)
        return output
    catch failure:
        ledger.releaseReservation(reservation)
        raise ServiceFailure(failure)
    finally:
        snapshot.close()
```

The logical `content` may be streamed, but success requires exactly the
advertised bytes. Metadata and bytes come from one immutable snapshot. A
missing or oversized resource is a failure, never an HTML success response.

## 4. Visitor verification

```text
function checkPageGet(requestedPath, agreedPrice, output, limits):
    if any required value is unavailable: return INCONCLUSIVE
    if output.contentSize > limits.maximumCheckBytes: return INCONCLUSIVE

    if not isCanonicalPath(output.path): return FAIL
    if output.path != requestedPath: return FAIL
    if not isValidMediaType(output.mediaType): return FAIL
    if output.price != agreedPrice: return FAIL
    if output.contentSize != length(output.content): return FAIL
    if length(output.contentHash) != SHA256_SIZE: return FAIL
    if not constantTimeEqual(SHA256(output.content), output.contentHash):
        return FAIL
    return PASS
```

The check is local and included in the successful invocation; it creates no
second invocation or charge. Cache keys should include publisher identity,
path, and content hash. Version 1 provides no freshness promise.

## 5. Publication and safety

```text
function publishResource(path, mediaType, bytes, activeTerms):
    validateCanonicalPath(path, maximum(activeTerms.maximumPathBytes))
    validateMediaType(mediaType)
    require length(bytes) <= maximum(activeTerms.maximumResourceBytes)
    resourceStore.replaceAtomically(path, mediaType, bytes)

function validateAdvertisedPage(resourceStore, offering):
    terms = validatePageOffering(offering)
    root = resourceStore.openImmutableSnapshot("/")
    require root exists and root.mediaType == "text/html"
    require root.exactByteLength <= terms.maximumResourceBytes
```

Publication is local and unpaid. Providers must map protocol paths without
traversal or unintended symlink access. Visitors must sandbox active content,
enforce limits before allocation or rendering, and treat media types and
content as publisher assertions rather than safety guarantees.
