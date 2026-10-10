# Public File Sharing inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

Optional. The host owns complete immutable shares and their catalog. It consumes
[Services context](../../services/outputs/README.md), [Identity signing](../../identity/outputs/README.md),
[Cryptography hashing](../../cryptography/outputs/README.md), local content/clock
ports and the [Discovery share-record format](../../discovery/README.md#6-share-records).
That format is mandatory for catalogs; a Discovery indexer is optional. Paid
Storage is not required for hosting or downloading a share.

## Accepted operations

Invocation inputs carry `operation`. Share IDs/cursor IDs are 32 bytes, counts
and indices uint32; byte limits uint64.

| Input / source | Fields and expectations |
|---|---|
| Local host/import / authorized administrator | Complete file tree or canonical manifest plus complete bytes; validate paths, ordering, lengths, pieces and file hashes before advertising. No remote upload operation is implied. |
| `manifest` / Services | `shareId`, `maximumManifestBytes`; bound at least 70 and no greater than offering limit. Assessment locates exact immutable manifest and quotes `manifestBytes`. |
| `download` / Services | `shareId`, `fileIndex`, `firstPiece`, `pieceCount`; positive count, subtraction-safe range within validated manifest and bytes within download limit. Assessment quotes `downloadBytes`. |
| `catalog` / Services | Optional `afterShareId`, `limit`; exclusive unsigned-byte cursor and positive current catalog limit. |
| Local check / requester | Original request and accepted terms; manifest and requested ID, or verified manifest plus range/data, or provider ID plus catalog/cursor/time limits. |
| Optional host lookup / requester application | Known share ID, candidate contacts and explicit Discovery budget. A known provider can be contacted directly without lookup. |

Catalog signing uses this host identity and canonical current positive Discovery
share records. Do not require the Discovery server to be online to construct
them. Shared format validation is available as a codec port or locally linked
implementation.

Manifest and download requests pin a consistent immutable share. Host storage
layout, deduplication and upstream retrieval are private; the host must be able
to provide the complete advertised share. A downloader validates the manifest
before selecting piece ranges, then retains independently verified pieces.
