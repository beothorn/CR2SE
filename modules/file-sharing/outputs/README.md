# Public File Sharing outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Results returned through Services

Outputs carry matching `operation`, exact `price:uint64` and these fields:

| Operation | Output | Guarantee |
|---|---|---|
| `manifest` | `shareId:bytes[32]`, `manifest:bytes` | Exact quoted length; canonical format, SHA-256 equals requested share ID. |
| `download` | `shareId`, `fileIndex`, `firstPiece`, `pieceCount`, `data` | Exact requested metadata and quoted byte count; concatenated pieces in order, no added separators. |
| `catalog` | `catalogAt:uint64`, `shareRecords:array<bytes>`, `more:bool` | Current positive signed records from authenticated host, ordered by share ID, respecting exclusive cursor, time limits and result count. Empty catalog is a paid success. |
| Local publication | Share ID and validated availability/manifest reference | Only complete hosted shares become available; no paid lease or promise of permanent retention is created. |
| Local check/download progress | Pass/fail/inconclusive and verified piece/file state | Piece hashes must match before marking pieces valid; whole-file hash must match before reporting a complete file. |

Consumers are [Services](../../services/inputs/README.md), requester applications
and optional [Discovery indexing clients](../../discovery/inputs/README.md).
Services supplies Ledger settlement and Peer Control delivery; File Sharing
does not directly debit accounts. Internal completion references survive any
required local settlement recovery, but the peer service does not add replay
guarantees for repeated reads.

Catalog output uses Discovery codecs without requiring an indexer. Host claims
do not establish continuous availability. A manifest may be cached by hash;
catalog pages may change between calls. Interrupted download pieces can be
kept only after hash verification; any new invocation has a new accepted price.
Local extraction enforces safe paths rather than trusting manifest names as
filesystem authority.

## Independent acceptance examples

- Reproduce the canonical manifest vector and independently verify share, piece
  and whole-file hashes using local content and crypto substitutes.
- Exercise manifest/download/catalog with the Discovery runtime absent; catalog
  bytes still validate against the shared share-record format.
- Corrupt one piece or use a traversal path: verification/extraction fails.
  A partial response never becomes a successful paid result.
