# Open Social Messaging pseudocode

This document translates [`OpenSocialMessaging.md`](../OpenSocialMessaging.md)
into implementation-neutral algorithms. The specification remains authoritative.
Messages are public and untrusted even when their signatures verify.

## 1. Constants and records

```text
SERVICE_ID = "cr2se.open-social-messaging"
SERVICE_VERSION = 1
IDENTITY_PRECONDITION = "cr2se.identity"
SIGNING_PREFIX = ASCII("CR2SE-OPEN-SOCIAL-MESSAGE-V1")

Message:
    messageId                  32 bytes
    publisherId                32 bytes
    publisherPublicKey         32 bytes
    publishedAt                uint64 Unix seconds
    body                       valid UTF-8
    attachments               ordered list<Attachment>
    publisherSignature         64 bytes
    messageHash                32 bytes
```

Offering validation requires `pricing.model = "cr2se.open-social-messaging.v1"`,
a positive `readPrice`, no fixed Board `price`, the identity precondition, no
separately charged check, and every limit:
`maximumResults`, `maximumAttachmentsPerMessage`, `maximumBodyBytes`,
`maximumAttachmentBytes`, `maximumMessageBytes`, and `maximumResponseBytes`.
Require `maximumMessageBytes <= maximumResponseBytes`.

## 2. Canonicalization and publication

```text
function canonicalAttachmentBytes(a):
    validate attachment media type, name/metadata, sizes, hash, and data
    return exact version-1 tag || specified big-endian lengths || exact fields

function canonicalMessageBytes(m):
    validate IDs, exact integers, UTF-8 body, attachment count, and all limits
    return SIGNING_PREFIX || exact version-1 fields in normative order
        || uint32_be(length(m.attachments))
        || concat(canonicalAttachmentBytes(a) for a in m.attachments)

function validateSignedMessage(m, publisherId, terms):
    require Identity.deriveVersion1Id(m.publisherPublicKey) == m.publisherId
    require m.publisherId == publisherId
    canonical = canonicalMessageBytes(m)
    require length(canonical) <= terms.maximumMessageBytes
    messageHash = SHA256(canonical)
    require m.messageHash == messageHash
    require Ed25519.verify(m.publisherPublicKey,
        ASCII("CR2SE-OPEN-SOCIAL-SIGNATURE-V1") || messageHash,
        m.publisherSignature)
    return m

function publishLocalMessage(fields, identity, feedStore, terms):
    require messageId has never been published with different bytes
    message = fields with publisherId=identity.id and publisherPublicKey=identity.key
    canonical = canonicalMessageBytes(message)
    message.publisherSignature = Identity.sign(identity,
        ASCII("CR2SE-OPEN-SOCIAL-SIGNATURE-V1") || SHA256(canonical))
    message.messageHash = SHA256(canonical)
    feedStore.publishAtomically(message)
    return message.messageHash
```

The exact canonical byte layouts are those in the specification. Publication
is a local procedure, not a version 1 peer operation, and costs no credits.

## 3. Read selection and response

```text
function validateReadInput(input, terms):
    require input.operation == "read"
    require input.selector in {latest, since, interval}
    require 1 <= input.limit <= terms.maximumResults
    if selector == latest: require fromInclusive and toExclusive absent
    if selector == since: require fromInclusive present and toExclusive absent
    if selector == interval:
        require fromInclusive < toExclusive
    require beforePublishedAt and beforeMessageId are both present or both absent
    return input

function read(requester, offering, input):
    terms = validateOffering(offering)
    query = validateReadInput(input, terms)
    snapshotAt = currentUnixSeconds()
    candidates = feedStore.publicMessagesForLocalIdentity(snapshotAt)
    sort by (publishedAt descending, messageId descending)
    apply latest/since/interval selector, then the exclusive before cursor

    selected = []
    totalBytes = 0
    for message in candidates in selector-defined order:
        validateSignedMessage(message, localIdentityId, terms)
        n = length(canonicalMessageBytes(message))
        if length(selected) == query.limit: break
        if BigInt(totalBytes) + n > terms.maximumResponseBytes: break
        append message; totalBytes += n

    reserve fixed advertised read price
    returnAndCommitExactly({operation:"read", selectedAt:snapshotAt,
        messages:selected, more:anotherMatchingMessageExisted,
        price:offering.pricing.readPrice})
```

An empty successful page is charged. Pagination cursors are exclusive. The
provider returns only its own signed feed and one internally consistent
selection snapshot.

## 4. Verification and combined feeds

```text
function checkRead(originalInput, agreedTerms, output):
    if required bytes unavailable or limits prevent checking: return INCONCLUSIVE
    require output.operation == "read" and output.price == agreed price
    require message count <= originalInput.limit and advertised maximum
    require total canonical bytes <= maximumResponseBytes
    for each message:
        validateSignedMessage(message, authenticatedProviderId, agreedTerms)
        require it satisfies selector and strict canonical ordering
    return PASS
catch validation mismatch: return FAIL

function gatherCombinedFeed(subscriptions, localPolicy):
    combined = []
    concurrently for publisher in subscriptions within budget:
        authenticate publisher; fetch current Board; select compatible offering
        page = invoke read with bounded limit and explicit maximum price
        if checkRead(...) == PASS: append page.messages
        else record provider failure without poisoning other feeds
    deduplicate by (publisherId, messageHash)
    sort using application display policy with deterministic tie-breakers
    return combined
```

A pass proves byte consistency, signature, author identity, selection bounds,
and price—not truth, safety, or completeness beyond the provider's response.
Readers sandbox attachments and rendered content, never auto-execute data, and
enforce economic and resource budgets before following or fetching anything.
