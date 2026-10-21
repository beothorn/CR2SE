# Cryptography inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Required in the minimum node. Cryptography can be implemented without any
running CR2SE module. It consumes bytes, algorithm parameters and protected key
handles; Identity's ID derivation is a shared formula, not a runtime dependency.

## Accepted calls

| Input / source | Values and expectations |
|---|---|
| Key generation / Identity or Transport | Explicit Ed25519 or X25519 purpose, cryptographically secure platform randomness and protected key-store adapter. Generate independent key pairs. |
| Hash / Identity, Transport, Ledger or family codecs | Exact bounded bytes or ordered byte stream, hash algorithm SHA-256. No implicit text conversion. |
| Sign or verify / Identity, Transport, Ledger, Messaging, Discovery, Files or Feeds | Exact canonical bytes, Ed25519 private handle for authorized signing or 32-byte public key and 64-byte signature for verification. Caller selects the specified domain; do not sign arbitrary peer requests through an unrestricted key port. |
| Key agreement and derivation / Transport, Identity or Messaging | X25519 key handle/public key, exact salt/info/context and requested output length from the owning construction. Reject invalid/all-zero shared results. Transport's HKDF uses its exact transcript; frame tags use the specified XChaCha20-Poly1305 construction and directional sequence counters. |
| Authenticated encryption/decryption / Identity or family codec | XChaCha20-Poly1305 key handle, 24-byte nonce, exact associated data and bounded plaintext/sealed bytes. Key and nonce sizes are checked before use. |
| Generic identity envelope / local authorized caller | Plaintext plus recipient ID, Ed25519 public key, persistent X25519 public key and binding signature; or complete ciphertext plus local identity/key handle. Validate ID derivation and key binding before encryption. |

Algorithm parameters, signing bytes and envelope fields are fully defined in
the [specification](../README.md); callers must not substitute host serialization.
Messaging's envelope and Transport's session construction are distinct from the
generic 132-byte-header envelope. Their codecs compose the primitives with their
own exact formats.

Platform dependencies are secure randomness, protected transient/private key
access and established algorithm implementations. No network, Board, trust,
Ledger or paid Storage access is required. Bound object sizes and overflow-check
lengths before allocation. Test-only deterministic randomness must be explicitly
injected and isolated from ordinary key generation.

All public-key validation and signature verification follows the
[Ed25519 verification profile](../README.md#ed25519-verification-profile),
including canonical point encoding, small-order rejection, scalar bounds and
identical acceptance for single and batch verification.
