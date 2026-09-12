# Public File Sharing pseudocode

This document translates [`PublicFileSharing.md`](../PublicFileSharing.md) into
implementation-neutral algorithms. The specification remains authoritative.
Manifests, paths, lengths, catalog records, and downloaded bytes are untrusted.

## 1. Constants, terms, and exact prices

```text
SERVICE_ID = "cr2se.public-file-sharing"
SERVICE_VERSION = 1
PRICING_MODEL = "cr2se.public-file-sharing.v1"
SHARE_ID_SIZE = 32

Terms:
    minimumPrice; manifestByteFactor; downloadByteFactor; catalogPrice
    maximumManifestBytes; maximumDownloadBytes; maximumFiles
    maximumCatalogResults; maximumCatalogRecordLifetimeSeconds
    maximumCatalogClockSkewSeconds

function ceilFraction(n, d): require d > 0; return (n + d - 1) div d
function manifestPrice(N, t):
    return uint64Fit(max(t.minimumPrice,
        ceilFraction(BigInt(N)*t.manifestByteFactor.n,
                     t.manifestByteFactor.d)))
function downloadPrice(D, t):
    return uint64Fit(max(t.minimumPrice,
        ceilFraction(BigInt(D)*t.downloadByteFactor.n,
                     t.downloadByteFactor.d)))
```

Offering validation requires the exact service/version/model, identity
precondition, no fixed `price`, all pricing and `info` fields, positive
nonzero denominators, `minimumPrice` and `catalogPrice` of at least one, and the
specified bounds (including manifest >= 70 and download >= 16384). Calculate
prices at advertised maxima using arbitrary precision and reject overflow.

## 2. Canonical manifests

```text
function buildManifest(pieceSize, inputFiles):
    require pieceSize satisfies the specification bounds
    files = []
    for source in inputFiles:
        path = validateCanonicalComponentPath(source.path)
        stream source exactly once into consecutive pieces of at most pieceSize
        record piece hashes = SHA256(each exact piece)
        record fileSize and fileHash = SHA256(all exact file bytes)
        files.append(record)
    sort files by canonical component-by-component byte ordering
    reject duplicate paths and file count overflow
    encoded = encodeManifestV1Exactly(files, pieceSize) // fixed tags/BE widths
    require parseManifestV1(encoded) reproduces the same records
    return {manifest: encoded, shareId: SHA256(encoded)}

function parseAndValidateManifest(bytes, terms):
    require length(bytes) <= terms.maximumManifestBytes
    parse version, pieceSize, fileCount, records with checked arithmetic
    require fileCount in 1 .. terms.maximumFiles
    validate UTF-8 components, component lengths, hashes, piece counts,
            file-size/piece-size consistency, canonical ordering, and EOF
    require encodeManifestV1Exactly(parsed) == bytes
    return parsed
```

The canonical field layout and tags are exactly those in the normative
specification; implementations must not substitute JSON, platform paths,
locale sorting, hex hashes, or native-endian integers.

## 3. Hosting and manifest retrieval

```text
function hostShare(manifestBytes, fileSource, terms):
    manifest = parseAndValidateManifest(manifestBytes, terms)
    verify every file size, file hash, piece boundary, and piece hash
    snapshot = durableImmutableSnapshot(manifestBytes, fileSource)
    shareStore.publishAtomically(SHA256(manifestBytes), snapshot)

function manifestOperation(requester, offering, input):
    require input.operation == "manifest"
    require length(input.shareId) == 32
    require input.maximumManifestBytes <= offering.maximumManifestBytes
    snapshot = shareStore.open(input.shareId) or fail shareUnavailable
    require SHA256(snapshot.manifest) == input.shareId
    require length(snapshot.manifest) <= input.maximumManifestBytes
    price = manifestPrice(length(snapshot.manifest), offering)
    agreeAndReserve(requester, offering.creditIssuer, price)
    returnAndCommitExactly({operation:"manifest", shareId:input.shareId,
        manifest:snapshot.manifest, price:price})
```

Share existence is checked before acceptance. Failure or an incomplete output
releases the reservation and is not charged.

## 4. Piece download

```text
function downloadOperation(requester, offering, verifiedManifest, input):
    require input.operation == "download"
    require input.shareId == SHA256(canonicalBytes(verifiedManifest))
    file = verifiedManifest.files[input.fileIndex] or fail InvalidRange
    require input.pieceCount > 0
    range = checkedConsecutivePieceRange(
        file, input.firstPiece, input.pieceCount)
    D = exactLogicalByteLength(range) // final piece may be shorter
    require 1 <= D <= offering.maximumDownloadBytes
    price = downloadPrice(D, offering)
    agreeAndReserve(requester, offering.creditIssuer, price)
    snapshot = shareStore.open(input.shareId) or fail shareUnavailable
    bytes = snapshot.readExactFileRange(input.fileIndex, range)
    require length(bytes) == D
    returnAndCommitExactly({operation:"download", shareId:input.shareId,
        fileIndex:input.fileIndex, firstPiece:input.firstPiece,
        pieceCount:input.pieceCount, data:bytes, price:price})

function verifyDownload(manifest, output):
    split output.data at manifest-defined piece boundaries
    require every SHA256(piece) equals its manifest piece hash
    if complete file assembled:
        require its length and SHA256 equal file record
    return PASS; on mismatch return FAIL; unavailable data returns INCONCLUSIVE
```

Downloaders write only beneath a selected root, reject traversal and path
collisions, use temporary files, verify before atomic publication, and do not
follow unsafe links.

## 5. Catalog and checks

```text
function catalogOperation(requester, offering, afterShareId, limit, now):
    require 1 <= limit <= offering.maximumCatalogResults
    records = catalog.positiveShareRecordsOrderedByShareId(
        exclusiveAfter = afterShareId, limit = limit)
    for record in records:
        Discovery.validateShareRecord(record)
        require record.providerId == localIdentityId
        require record.issuedAt <= now + maximumCatalogClockSkewSeconds
        require record.expiresAt - record.issuedAt
                <= maximumCatalogRecordLifetimeSeconds
        require shareStore currently hosts record.shareId
    agreeAndReserve(..., offering.catalogPrice)
    returnAndCommitExactly({operation:"catalog", catalogAt:now,
                            shareRecords:records,
                            price:offering.catalogPrice})
```

Manifest check validates canonical encoding and `SHA256(manifest)==shareId`.
Download check validates the selected piece hashes. Catalog check validates
canonical signed positive Discovery records, ordering, bounds, provider, time,
and returned price. Complete contradictory evidence is `FAIL`; missing data or
a local limit is `INCONCLUSIVE`. Checks are local and add no charge.
