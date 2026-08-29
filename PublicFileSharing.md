# CR2SE Public File Sharing

CR2SE Public File Sharing is a standard, paid service for retrieving immutable
files from a CR2SE identity that has chosen to make them publicly available.

A **share** is one immutable file or one immutable directory tree. A **host** is
the service provider that makes every byte of a share available. A
**downloader** is the service requester that pays the host for returned bytes.
A **manifest** is a deterministic byte description of every path, size, and
content hash in a share. A **piece** is one bounded, consecutive part of one
file. The downloader identifies the wanted share with the 32-byte SHA-256 hash
of its manifest, called its **share ID**.

Public means that any authenticated identity may request the data under the
host's advertised terms. It does not mean anonymous, free, confidential,
permanent, trusted, legal, or safe.

This specification answers the following question:

```text
Given a connection to a peer and a share ID, can that peer provide the share,
and how are its metadata and bytes downloaded and verified?
```

Finding peers that may have a share is outside this specification. Discovery
may map a share ID to candidate identities or addresses. A downloader may also
ask any already connected peer directly. A peer that does not host the share
rejects the request before accepting a paid invocation.

Common terms such as **identity**, **service requester**, **service provider**,
**offering**, **credit issuer**, **check**, and **trust** are defined in the
[CR2SE Glossary](./Glossary.md). Common service and pricing rules are defined in
[Services](./Services.md), Board advertisements in [Board](./Board.md), and
transport-independent invocation in [NodeApi](./NodeApi.md).

---

## 1. Version 1 service

The version 1 Public File Sharing service is identified by:

```text
service:        cr2se.public-file-sharing
serviceVersion: 1
pricing model:  cr2se.public-file-sharing.v1
```

It has two operations:

```text
manifest
    Return the canonical description of a share.

download
    Return one or more consecutive pieces of one file in that share.
```

The `manifest` operation is normally performed first. It gives the downloader
the paths, file sizes, piece layout, and hashes needed to construct and verify
later `download` operations.

Version 1 defines retrieval from a host that possesses the complete share. It
does not advertise incomplete shares or individual piece availability. Several
complete hosts may have the same share, and a downloader may retrieve different
piece ranges from different hosts.

Placing content at a host is an administrative action outside this service. A
host may import local files, mirror another host, obtain data through CR2SE
Storage, or use another mechanism. A Storage lease is private to its requester
and does not become public merely because its bytes form a valid share.

---

## 2. Bytes, integers, text, and hashes

A **byte string** is an ordered sequence of bytes. Its length is measured in
bytes, not characters.

`uint32` and `uint64` mean unsigned 32-bit and unsigned 64-bit integers. In the
canonical format defined below, integers use network byte order: the most
significant byte is encoded first.

A **UTF-8 string** is a byte string containing one valid, shortest-form UTF-8
encoding. Surrogate code points, overlong encodings, and invalid byte sequences
are forbidden. Unicode normalization is not performed. Two strings compare
equal only when their UTF-8 bytes are equal.

`SHA-256(data)` means the 32-byte output of SHA-256 applied to `data`, as
defined by FIPS 180-4. Protocol fields contain the raw 32 bytes. A user
interface may display those bytes as exactly 64 lowercase hexadecimal digits.
Hexadecimal text is never hashed in place of the raw bytes unless a
specification explicitly says so.

Useful SHA-256 test vectors are:

```text
SHA-256(empty byte string)
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

SHA-256(three ASCII bytes "abc")
ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
```

MD5 is not used. MD5 collisions can be deliberately constructed, so an
attacker can create different bytes with the same MD5 value. Plainly
concatenating file hashes is also insufficient: without type, length, path,
and ordering rules, independent implementations can describe different trees
with the same input bytes. The canonical manifest below removes that ambiguity
and its SHA-256 hash identifies the complete share.

---

## 3. Files and paths

A **file** is an immutable byte string. Its **file size** is the number of
bytes in that string. Empty files, whose file size is zero, are permitted.

A **path component** is one UTF-8 string naming one level of a relative path.
Its UTF-8 encoding must contain between 1 and 255 bytes. A path component must
not:

```text
equal "." or "..";
contain U+0000 through U+001F or U+007F;
contain slash U+002F;
contain reverse solidus U+005C.
```

A **file path** is a sequence of one or more path components. It is relative to
the root of the share. It has no drive letter, scheme, authority, leading
separator, or trailing separator.

These are three distinct file paths:

```text
["photo.jpg"]
["images", "photo.jpg"]
["Images", "photo.jpg"]
```

Joining components with a platform separator is a local presentation or
extraction operation. The separator is not part of the canonical path.

No two files in one share may have equal paths. A file path must not be a
prefix of another file path. Consequently a share cannot simultaneously
contain a file at `["a"]` and a file at `["a", "b"]`.

A directory exists implicitly when it is a proper prefix of at least one file
path. Empty directories, symbolic links, hard links, devices, ownership,
permissions, timestamps, extended attributes, and alternate data streams are
not represented in version 1.

A one-file share contains exactly one file path. A directory-tree share
contains all regular files recursively beneath its root. The same manifest
format is used for both forms. The selected root directory's own name is not a
path component; every file path is relative to that root. Symbolic links found
during traversal are not followed. Two paths that refer to hard-linked bytes
are encoded as two independent file records. A directory tree containing no
regular file cannot form a version 1 share, although a share containing one or
more empty files is valid.

---

## 4. Pieces

A **piece size** is the maximum number of file bytes in one independently
verified unit. It is a `uint32`, must be a power of two, and must be in this
range:

```text
16384 .. 4194304 bytes
```

That is 16 KiB through 4 MiB. One piece size applies to every file in a share.

A non-empty file is divided from offset zero into consecutive pieces of the
declared piece size. Only the final piece may be shorter. An empty file has no
pieces.

For a file of size `S` and piece size `P`, its **piece count** is:

```text
0                         when S = 0
1 + ((S - 1) div P)       when S > 0
```

`div` is integer division that discards the remainder. This form avoids the
overflow possible in `(S + P - 1) div P`.

The calculated piece count must fit in `uint32`. A file whose size and selected
piece size would require more than `2^32-1` pieces cannot appear in a version 1
manifest; its constructor must select a larger valid piece size or reject it.

Pieces are numbered from zero. For piece index `i`:

```text
pieceOffset = i * P
pieceLength = minimum(P, S - pieceOffset)
```

The multiplication and subtraction must be checked before use. A piece index
is valid only when it is less than the file's piece count.

A **piece hash** is `SHA-256(piece bytes)`. A **file hash** is
`SHA-256(complete file bytes)`. The file hash of an empty file is therefore the
SHA-256 empty-string test vector in section 2.

Piece hashes allow a downloader to validate and retain each piece immediately,
resume an interrupted download, and combine pieces obtained from different
hosts. The file hash detects mistakes in piece assembly and verifies the final
file as a whole.

---

## 5. File records and ordering

A **file record** describes one file using:

```text
path
file size
piece count
piece hashes in increasing piece-index order
file hash
```

File records have one canonical order. Compare their paths component by
component. Compare each component by unsigned lexicographic order of its UTF-8
bytes. At the first different component, the component with the smaller byte
sequence sorts first. If every component in one path matches the beginning of
the other, the shorter path sorts first.

Unsigned lexicographic byte order compares the first differing byte as an
integer in `0 .. 255`; if one byte string is a prefix of another, the shorter
byte string sorts first.

Every manifest must store file records in this canonical path order. A parser
must reject a different order, duplicate path, or file-prefix conflict. It must
not silently reorder a received manifest before checking its identity.

The **file index** is a file record's zero-based position in this order. The
index is only shorthand within a manifest. The path, not the index alone,
describes where a file belongs.

---

## 6. Canonical manifest

The manifest introduced above is encoded as one canonical byte string. It
contains metadata and hashes, not file contents.

The following helper encodings are used:

```text
u8(x)
    x as one byte.

u32be(x)
    x as exactly four bytes in network byte order.

u64be(x)
    x as exactly eight bytes in network byte order.

text(s)
    u32be(length of the UTF-8 encoding of s), followed by those UTF-8 bytes.

hash(h)
    exactly the 32 raw bytes of h, with no length prefix.
```

Concatenation is written `||`. The canonical version 1 manifest is:

```text
ASCII("CR2SEPFS")                                      8 bytes
|| u8(1)                                               1 byte
|| u32be(pieceSize)                                    4 bytes
|| u32be(fileCount)                                    4 bytes
|| fileRecord[0]
|| fileRecord[1]
...
|| fileRecord[fileCount - 1]
```

`fileCount` must be in `1 .. 2^32-1`. Each file record is:

```text
u32be(componentCount)
|| text(component[0])
|| text(component[1])
...
|| text(component[componentCount - 1])
|| u64be(fileSize)
|| u32be(pieceCount)
|| hash(pieceHash[0])
|| hash(pieceHash[1])
...
|| hash(pieceHash[pieceCount - 1])
|| hash(fileHash)
```

`componentCount` must be in `1 .. 2^32-1`. Each component, path, file size,
piece count, piece hash, and file hash must satisfy the rules already defined.
No padding, terminator, trailing byte, optional field, or alternate encoding is
permitted.

The fixed magic bytes and version byte prevent these bytes from being confused
with an unrelated format. A later incompatible format uses another version
byte and another service version unless its use is explicitly made compatible.

A parser must validate lengths before allocation, reject arithmetic overflow,
reject a truncated field, and reject bytes after the final file hash. It should
apply an implementation-configured resource limit before parsing nested
records. The selected offering supplies a mandatory upper bound on accepted
manifest length.

### Constructing a manifest

To construct a version 1 manifest:

1. Choose one valid piece size.
2. Enumerate every regular file and convert its relative path to valid path
   components.
3. Sort the file records by canonical path order.
4. Read each file as bytes, calculate each piece hash, and calculate its file
   hash.
5. Encode every value exactly as specified above.

The input directory must not change during construction. An implementation may
detect modification by reopening files, comparing stable metadata, hashing a
snapshot, or another safe local method. It must never publish a manifest whose
hashes describe bytes it cannot serve.

### Canonical manifest test vector

The smallest valid manifest uses a piece size of 16,384 and contains one empty
file at path `["a"]`. Its 70 bytes, written as lowercase hexadecimal, are:

```text
435232534550465301000040000000000100000001000000016100000000000000000000
0000e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

Line breaks above are only for display and are not bytes. SHA-256 of the exact
70-byte value is:

```text
8faf21bb74074d60be59a2b014739ba4fc9bc194bdc40396cf4bdc3c35a1fbd1
```

An implementation should reproduce both values before exchanging manifests.

---

## 7. Share ID

The **share ID** is:

```text
SHA-256(manifest)
```

It is always 32 raw bytes in protocol fields. A share link, command line, QR
code, or user interface may carry the 64-digit lowercase hexadecimal form.

The share ID commits to:

```text
the manifest format version;
the piece size;
every file path and file size;
every piece boundary and piece hash;
every complete-file hash.
```

It therefore acts as the folder hash for a directory-tree share and as the
complete descriptor hash for a one-file share. Renaming a file, changing the
piece size, adding or removing a file, or changing any file byte creates a
different share ID.

The file hash and share ID serve different purposes. A file hash identifies
only one byte string. It does not identify the file's path, piece layout, or
the other files beside it. Download requests use the share ID.

Two independently constructed manifests with the same paths, piece size, and
file bytes have the same share ID. This property does not depend on operating
system directory order, native integer representation, JSON formatting,
locale, or programming language.

SHA-256 collision resistance is a security assumption, not a mathematical
proof that different manifests can never share an ID. Implementations must
still validate all received lengths and hashes.

---

## 8. Hosting and availability

A provider **hosts** a share when it has validated the canonical manifest and
is willing and able to return every piece described by it through a current
compatible offering.

For an offering to be compatible with a hosted share, the manifest length must
not exceed `maximumManifestBytes`, its file count must not exceed
`maximumFiles`, and its piece size must not exceed `maximumDownloadBytes`.

Having some pieces, remembering a share ID, caching an old manifest, or knowing
another host does not count as hosting the share in version 1. A provider may
fetch or reconstruct data internally, but that must not make an accepted
request miss its required result.

Hosting creates no retention period. A host may stop hosting a share at any
time unless another accepted service, such as a Storage lease, separately
requires retention. Removal affects future requests only. A `download`
operation accepted while the share was hosted must still complete or be a
service failure.

Before accepting either operation, the provider looks up the exact 32-byte
share ID. If it does not currently host the complete share, it returns a
`shareUnavailable` rejection. This is a pre-acceptance rejection, reveals no
manifest, and is not charged.

A requester may use that rejection as the answer to “does this peer have the
file?” No paid probe operation is defined. Providers should rate-limit such
lookups because public share IDs can otherwise be used for resource
enumeration or denial of service.

The provider may reject a request despite hosting the share because of trust,
capacity, credit, policy, or another common pre-acceptance rule. Therefore any
rejection other than `shareUnavailable` does not assert that the provider lacks
the share.

---

## 9. Pricing representation

CR2SE credits are unsigned integers, but bandwidth rates commonly cost less
than one credit per byte. Public File Sharing uses exact fractions:

```json
{
  "numerator": 1,
  "denominator": 1000000
}
```

The fields mean:

```text
numerator: uint64
    Number of credits in the rate. Range: 0 .. 2^64-1.

denominator: uint64
    Number of returned bytes covered by the rate.
    Range: 1 .. 2^64-1; zero is invalid.
```

The example represents one credit per one million returned bytes. A fraction
is an exact rate used in an integer calculation. It is not a fractional credit
transfer. Floating-point values must not be used.

`minimumPrice` is a `uint64` in `1 .. 2^64-1`. It is the minimum price of each
accepted `manifest` or `download` operation.

`manifestByteFactor` is the rate per manifest byte returned by `manifest`.
`downloadByteFactor` is the rate per file byte returned by `download`. Either
numerator may be zero; `minimumPrice` still makes every accepted invocation
cost at least one credit.

---

## 10. Offering limits and shape

The `info` object of an offering contains:

```text
maximumManifestBytes
    Largest manifest the offering will return. Range: 70 .. 2^64-1.

maximumDownloadBytes
    Largest total piece-data value returned by one download operation.
    Range: 16384 .. 2^64-1.

maximumFiles
    Largest fileCount accepted in a hosted manifest. Range: 1 .. 2^32-1.
```

Seventy bytes is the smallest possible manifest: the 17-byte header plus one
empty-file record with one one-byte component and its 32-byte file hash.

A complete version 1 provided or wanted offering has this form:

```json
{
  "id": "public-files",
  "service": "cr2se.public-file-sharing",
  "serviceVersion": 1,
  "description": "Return canonical manifests and hash-verified pieces of publicly hosted immutable files.",
  "creditIssuer": "PROVIDER_ID",
  "pricing": {
    "model": "cr2se.public-file-sharing.v1",
    "minimumPrice": 1,
    "manifestByteFactor": {
      "numerator": 1,
      "denominator": 1000000
    },
    "downloadByteFactor": {
      "numerator": 1,
      "denominator": 1000000
    }
  },
  "info": {
    "maximumManifestBytes": 16777216,
    "maximumDownloadBytes": 16777216,
    "maximumFiles": 100000
  },
  "preconditions": [
    "cr2se.identity"
  ]
}
```

The numbers are illustrative. A version 1 offering must use `pricing`; it must
not use the fixed Board `price` field. It must contain every pricing and `info`
field shown above. It must contain the `cr2se.identity` precondition because
the identities must agree which issuer's credits are transferred.

An offering advertises general retrieval terms, not a list of hosted share
IDs. Large catalogs belong in discovery mechanisms rather than Boards. A
provider must not claim to host a particular share merely because it advertises
this service.

---

## 11. Price calculations

Let:

```text
N = exact manifest length for a manifest operation
D = exact number of file bytes for a download operation
M = minimumPrice
A.n / A.d = manifestByteFactor
B.n / B.d = downloadByteFactor
```

`ceil(value)` means the smallest integer greater than or equal to `value`, and
`max(left, right)` selects the greater value.

The prices are:

```text
manifestPrice = max(M, ceil(N * A.n / A.d))
downloadPrice = max(M, ceil(D * B.n / B.d))
```

For positive integers, an implementation may calculate:

```text
ceil(x / y) = (x + y - 1) div y
```

only when its intermediate arithmetic cannot overflow.

All calculations must use arbitrary-precision integers or an equivalent
overflow-safe algorithm. If an exact price exceeds `2^64-1`, the request or
offering is invalid and must be rejected before acceptance. The maximum prices
permitted by an offering's limits must fit in `uint64`.

The price counts logical returned manifest or file bytes. It does not count
frame headers, encryption overhead, retransmission below the service layer,
internal compression, disk reads, or provider-to-provider traffic.

For `manifest`, the provider communicates the exact manifest length and exact
calculated price after locating the share but before acceptance. The requester
accepts or rejects that quotation. After receiving the output, the requester
must verify that its byte length matches the quotation.

For `download`, both peers derive `D` from the already verified manifest and
the requested piece range before acceptance. They must agree on the same exact
price before any piece data is returned.

---

## 12. Manifest operation

The logical input is:

```text
operation:            "manifest"
shareId:              bytes (exactly 32 bytes)
maximumManifestBytes: uint64
```

`maximumManifestBytes` is the greatest manifest length the requester accepts
for this invocation. It must be at least 70 and no greater than the offering's
limit.

After locating the share, the provider rejects before acceptance when the
manifest is larger than either limit. Otherwise it quotes the exact manifest
length and price. On successful completion it returns:

```text
operation: "manifest"
shareId:   bytes (exactly 32 bytes)
manifest:  bytes
price:     uint64 credits
```

The returned `manifest` must have the quoted length, must be canonical, and
must satisfy:

```text
SHA-256(manifest) = shareId
```

The downloader must apply the following checks in order:

1. Enforce its local byte limit while receiving the value.
2. Verify the exact received length.
3. Calculate and compare the share ID.
4. Parse and validate the canonical format and all declared limits.

Checking the hash before deeply parsing attacker-controlled nested records
does not replace size and allocation limits. A parser may perform shallow
length validation while streaming the hash.

A valid manifest output is immutable and may be cached indefinitely by share
ID. Hosts need not retain records of which downloader previously requested it.

---

## 13. Download operation

The logical input is:

```text
operation:  "download"
shareId:    bytes (exactly 32 bytes)
fileIndex:  uint32
firstPiece: uint32
pieceCount: uint32
```

The downloader must already possess and have validated the manifest identified
by `shareId`. `fileIndex` selects one file record. `firstPiece` selects its
first returned piece. `pieceCount` is the number of consecutive pieces to
return and must be at least one.

The range is valid only when:

```text
fileIndex < fileCount
firstPiece < filePieceCount
pieceCount <= filePieceCount - firstPiece
```

The subtraction form is normative because addition could overflow.

Let `D` be the sum of the defined lengths of the selected pieces. `D` must be
in `1 .. maximumDownloadBytes` for the selected offering. Empty files have no
pieces and therefore require no download invocation; the manifest alone fully
verifies their contents.

A successful output is:

```text
operation:  "download"
shareId:    bytes (exactly 32 bytes)
fileIndex:  uint32
firstPiece: uint32
pieceCount: uint32
data:       bytes (exactly D bytes)
price:      uint64 credits
```

`data` is the concatenation of the requested pieces in increasing piece-index
order. It contains no length prefixes or separators. The validated manifest
determines every boundary. All pieces except a selected final file piece have
exactly the manifest's piece size.

The downloader splits `data` at those boundaries and verifies each part
against the corresponding piece hash before storing it as valid. After every
piece of a file is assembled in order, the downloader must also verify the
complete file hash before reporting that file as complete.

The provider must read and return exactly the bytes committed to by the
manifest. Internal compression, deduplication, reconstruction, cache layout,
or upstream retrieval is not observable.

A successful output is charged only after the complete logical `data` and
metadata have been returned. An interruption before complete output is a
service failure and must not be charged, even if some useful bytes arrived.
Those bytes may be retained locally only after their piece hashes pass, but a
retry is a new invocation with a new price.

---

## 14. Verification check

The Public File Sharing check is local verification of one successful
operation. It requires no additional provider message and has no separate
`checkPrice`. Exactly one logical check is included in each successful
invocation; an implementation may cache or recompute its local result without
creating another service invocation.

For a `manifest` output, the check input is the requested share ID and returned
manifest. Its outcome is:

```text
pass
    The returned bytes form a valid canonical manifest and their SHA-256 hash
    equals the requested share ID.

fail
    Complete returned bytes are available, but the format is invalid or their
    hash differs from the requested share ID.

inconclusive
    The complete returned bytes or requested share ID are unavailable to the
    checker, or local resource limits prevent the check.
```

For a `download` output, the check input is the validated manifest, requested
range metadata, and returned data. Its outcome is:

```text
pass
    Metadata and length match the request, and every returned piece has its
    expected piece hash.

fail
    Complete returned data is available, but metadata, length, or at least one
    piece hash differs.

inconclusive
    The validated manifest, request metadata, or complete returned data is
    unavailable, or local resource limits prevent the check.
```

The requester calculates the outcome. It must not trust a provider-supplied
claim that the data passed.

A passing piece check proves only that the returned bytes match the manifest
at the selected positions, subject to SHA-256 collision resistance. It does
not prove authorship, copyright status, safety, accuracy, continued
availability, or that another path on the local filesystem is unchanged.

The check does not automatically reverse a charge or settle a dispute. Its
result may affect the requester's local trust decision under the common service
rules.

---

## 15. Required service definition

Every version 1 Public File Sharing offering must expose a definition through
`service.get`. Its `id` and `description` match the selected Board offering.
Because the version 1 schema language has no union type, operation-specific
fields are optional in the shared schema; the rules below determine which are
required or forbidden.

Its logical schema is equivalent to:

```json
{
  "id": "public-files",
  "service": "cr2se.public-file-sharing",
  "serviceVersion": 1,
  "description": "Return canonical manifests and hash-verified pieces of publicly hosted immutable files.",
  "input": {
    "type": "object",
    "fields": {
      "operation": { "type": "string", "description": "Operation: manifest or download." },
      "shareId": { "type": "bytes", "description": "Exact 32-byte SHA-256 hash of the canonical manifest." },
      "maximumManifestBytes": { "type": "uint64", "description": "Largest manifest byte length accepted by the requester for a manifest operation.", "optional": true },
      "fileIndex": { "type": "uint32", "description": "Zero-based canonical file-record index selected by a download operation.", "optional": true },
      "firstPiece": { "type": "uint32", "description": "Zero-based first piece selected by a download operation.", "optional": true },
      "pieceCount": { "type": "uint32", "description": "Positive number of consecutive pieces selected by a download operation.", "optional": true }
    }
  },
  "output": {
    "type": "object",
    "fields": {
      "operation": { "type": "string", "description": "Completed operation: manifest or download." },
      "shareId": { "type": "bytes", "description": "Exact 32-byte share ID selected by the invocation." },
      "manifest": { "type": "bytes", "description": "Canonical version 1 manifest returned by a manifest operation.", "optional": true },
      "fileIndex": { "type": "uint32", "description": "Zero-based file-record index returned by a download operation.", "optional": true },
      "firstPiece": { "type": "uint32", "description": "Zero-based first returned piece index.", "optional": true },
      "pieceCount": { "type": "uint32", "description": "Number of consecutive pieces represented by data.", "optional": true },
      "data": { "type": "bytes", "description": "Concatenated complete piece bytes returned by a download operation.", "optional": true },
      "price": { "type": "uint64", "description": "Exact credits charged for the successful operation." }
    }
  },
  "check": {
    "description": "For manifest, validate its canonical encoding and SHA-256 share ID; for download, validate returned metadata, lengths, and every SHA-256 piece hash against the manifest.",
    "input": {
      "type": "object",
      "fields": {
        "operation": { "type": "string", "description": "Checked operation: manifest or download." },
        "shareId": { "type": "bytes", "description": "Requested 32-byte share ID." },
        "manifest": { "type": "bytes", "description": "Returned or previously validated canonical manifest.", "optional": true },
        "fileIndex": { "type": "uint32", "description": "Checked zero-based file-record index for download.", "optional": true },
        "firstPiece": { "type": "uint32", "description": "Checked zero-based first piece index for download.", "optional": true },
        "pieceCount": { "type": "uint32", "description": "Checked number of consecutive pieces for download.", "optional": true },
        "data": { "type": "bytes", "description": "Complete returned piece data checked for download.", "optional": true }
      }
    },
    "output": {
      "type": "object",
      "fields": {
        "outcome": { "type": "string", "description": "Requester-computed verification result: pass, fail, or inconclusive." }
      }
    }
  }
}
```

The operation discriminant selects these exact known input fields:

```text
manifest
    requires operation, shareId, maximumManifestBytes

download
    requires operation, shareId, fileIndex, firstPiece, pieceCount
```

A known field listed for the other operation must be rejected. Unknown object
fields follow the compatible-extension rule in `Services.md`.

An implementation may expose functions, processes, streams, iterators, or
language-native records instead of JSON. It must preserve the same logical
values, unsigned integer ranges, byte order, UTF-8 rules, validation, prices,
hash inputs, and observable behavior. A large `bytes` value may be transported
or exposed in bounded chunks; transport chunk boundaries do not alter the
logical value or piece boundaries.

---

## 16. Example download

Suppose a validated manifest describes a file of 40,000 bytes with a piece
size of 16,384 bytes. Its pieces are:

```text
piece 0: offset     0, length 16384
piece 1: offset 16384, length 16384
piece 2: offset 32768, length  7232
```

A request for `firstPiece = 1` and `pieceCount = 2` returns exactly 23,616
bytes. The first 16,384 returned bytes are checked against piece hash 1 and the
remaining 7,232 bytes against piece hash 2.

With `downloadByteFactor = 1/10000` and `minimumPrice = 1`:

```text
downloadPrice = max(1, ceil(23616 / 10000))
              = 3 credits
```

If another host advertises compatible service terms and hosts the same share
ID, the downloader may instead request either piece from that host. The piece
hashes and final file hash are identical because they come from the same
manifest.

---

## 17. Parallelism, resumption, and retries

Distinct `manifest` and `download` operations are read-only and may run
concurrently. A provider may limit concurrent accepted operations according to
advertised limits, capacity, trust, and local policy.

A downloader should record verified pieces by the tuple:

```text
(share ID, file index, piece index)
```

It may skip those pieces after restart. It must not reuse a piece under another
share ID merely because the numeric indexes match. Content-addressed local
deduplication by verified piece hash is permitted, but the implementation must
also confirm the expected piece length.

Requests may overlap. Repeating a completed request is a new invocation and
may be charged again. An implementation must not automatically retry after an
ambiguous accepted invocation unless the downloader's policy permits the
possible duplicate charge.

After interruption, the downloader should request only pieces it has not
already verified. Version 1 does not resume at an arbitrary byte inside a
piece. It retransmits that complete piece so its hash can be independently
checked.

When downloading from several hosts, the downloader applies each host's own
offering, credit issuer, price, and trust policy. Matching share IDs make bytes
technically compatible; they do not make the economic terms or identities the
same.

---

## 18. Discovery and links

Discovery is expected to use the 32-byte share ID as the content lookup key.
The discovery result may identify zero or more candidate hosts. Its format,
ranking, freshness, privacy, and resistance to false claims belong to the
Discovery specification.

A discovery claim that a peer hosts a share is not proof. The peer confirms
availability only by accepting a request and proves returned content only
through the manifest and piece hashes.

This specification does not define a textual share-link URI. Until one is
standardized, applications may exchange the 64-digit lowercase hexadecimal
share ID together with enough CR2SE bootstrap or discovery information to find
a candidate host. An application-specific URI must not be presented as a
standard CR2SE URI.

---

## 19. Failure behavior

No successful output is returned, and no charge is permitted, for conditions
including:

```text
unsupported service or pricing version;
unknown operation;
malformed fields or a share ID of the wrong length;
operation-specific required field missing;
known field present where the selected operation forbids it;
shareUnavailable before acceptance;
manifest or request outside advertised limits;
invalid file index, piece index, piece count, or derived byte length;
price overflow or price disagreement;
insufficient accepted credits;
failed identity precondition;
provider rejection by trust, capacity, or local policy;
provider inability to return the complete accepted output;
connection interruption before complete output.
```

A provider must validate its hosted manifest before advertising the share as
available. If it discovers after acceptance that local data no longer matches
the manifest, the invocation is a service failure. It must not substitute new
bytes, create a new manifest under the requested share ID, or charge for an
invalid result.

A downloader that receives complete but hash-invalid bytes records a failed
check and may reduce trust. CR2SE has no global adjudicator and does not
automatically reverse credits after a result or verification dispute.

Error details should distinguish `shareUnavailable`, invalid input, price
disagreement, and general refusal when doing so does not violate local privacy
policy. Error text is untrusted and is not part of a share's identity.

---

## 20. Security and implementation guidance

### Content is untrusted

A valid hash proves correspondence with the named bytes, not safety. A share
may contain malware, exploit files, misleading documents, illegal material,
decompression bombs, hostile markup, or filenames chosen to deceive a user.

Downloaders must not automatically execute downloaded files. Previewers,
archive readers, media decoders, indexers, and antivirus tools all process
untrusted input and should be isolated and resource-bounded.

### Safe extraction

Before writing a file tree, an implementation must map canonical components to
local paths without permitting escape from the selected destination. It must
reject or safely transform names that the local platform cannot represent.

In particular, it must defend against:

```text
absolute paths and drive-relative paths;
dot and dot-dot traversal;
separator reinterpretation;
case-folding collisions;
Unicode normalization collisions;
reserved device names;
trailing-space or trailing-dot aliases;
pre-existing symbolic links or mount-point escapes;
time-of-check/time-of-use path replacement.
```

The canonical manifest rules remove several dangerous forms but cannot model
every filesystem. A downloader may keep content in a content-addressed store,
choose safe replacement names, or refuse extraction. It must not claim that a
locally transformed tree has the canonical paths without recording the
mapping.

### Privacy and traffic analysis

The host learns the downloader identity, requested share ID, selected file and
piece indexes, timing, and transferred sizes. Transport encryption does not
hide this information from the host. Public File Sharing provides no anonymity
or private-information-retrieval property.

The files are public to identities the host accepts. Encrypting a share before
publication is permitted; all hashes and prices then apply to the ciphertext
bytes. Key distribution, decryption format, and access control remain outside
this service.

### Host safety

Hosts should keep a validated manifest index, verify imported bytes, use
overflow-safe range calculations, cap concurrent reads and outgoing bandwidth,
and avoid constructing native paths directly from request values. A downloader
selects numeric indexes only after a host has selected a fixed validated
manifest, so the downloader never supplies an arbitrary server filesystem path.

Hashing does not establish the identity of an author or publisher. Applications
requiring authorship should distribute a signature over the share ID through a
separate authenticated mechanism.

---

## 21. Interoperability checklist

A version 1 implementation is interoperable only if it:

```text
uses service cr2se.public-file-sharing at serviceVersion 1;
uses pricing model cr2se.public-file-sharing.v1;
uses SHA-256 raw bytes exactly as defined;
does not substitute MD5, hexadecimal text, or native hash serialization;
uses one valid power-of-two piece size for the complete share;
calculates piece boundaries independently within each file;
validates canonical UTF-8 path components and canonical file order;
encodes integers in network byte order in the canonical manifest;
rejects non-canonical, truncated, trailing, overflowing, or over-limit data;
calculates the share ID as SHA-256 of the exact canonical manifest bytes;
rejects an unavailable share before acceptance and without charging;
derives exact returned lengths from the validated manifest;
uses exact overflow-safe ceiling arithmetic for prices;
agrees the exact price and credit issuer before returning paid data;
returns only complete pieces in increasing index order;
verifies each downloaded piece and each completed file;
does not charge a pre-acceptance rejection or incomplete service failure;
exposes the required service definition and local verification check;
treats manifests, paths, files, discovery claims, and error text as untrusted;
leaves discovery, publication, retention, authorship, and textual links outside
version 1 unless another specification defines them.
```
