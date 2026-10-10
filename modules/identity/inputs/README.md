# Identity inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Required in the minimum node. Identity owns persistent identity credentials and
configured contacts, not connections, balances or service obligations.

## Accepted calls

| Input / source | Values and expectations |
|---|---|
| Create/load identity / authorized local administration | New identity request or protected handles for the independent signing and persistent encryption pairs. Loading validates public/private consistency and binding. Never create replacement keys silently on a load failure. |
| Parse/format ID / any caller | Exact 32-byte ID or textual ID. Enforce the version 1 Base32 length, alphabet and unused bits; accept case as specified without trimming whitespace. |
| Derive/validate ID / Transport or a signed-record codec | Version, algorithm, 32-byte Ed25519 public key and optional expected ID. Key-to-ID validation alone is not proof of possession. |
| Parse contact / authorized local client | ID or canonical contact QR text. Validate exact address/port fields; returned endpoint is a hint, not authentication. |
| Read local public credential / Transport, Ledger, local publishing client | Local caller authority and identity handle. Persistent encryption public key and binding are available without exporting secrets. |
| Sign canonical bytes / authorized Transport, Ledger or family provider | Purpose-scoped key authority, exact byte sequence and resource bounds. Identity delegates to Cryptography; a peer payload never grants signing authority. |
| Decrypt for local identity / authorized application or Ledger | Complete envelope, expected identity and protected encryption handle. Generic and service-specific formats must be selected explicitly. |

Consumes [Cryptography results](../../cryptography/outputs/README.md), secure
randomness, a protected persistent key store and backup/import facilities.
No Discovery runtime is required: configured contacts suffice. If Discovery is
enabled, its validated address records are hints supplied through an adapter.
Private key export/backup is privileged platform functionality, never a peer
operation or a general module result.
