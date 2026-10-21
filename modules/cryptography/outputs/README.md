# Cryptography outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Result | Consumer / guarantee |
|---|---|
| Public key and opaque private-key capability | [Identity](../../identity/inputs/README.md) or [Transport](../../transport/inputs/README.md); exact algorithm and ownership, with private material confined to the authorized key-store boundary. |
| SHA-256 digest | Identity, Ledger and all content codecs; exactly 32 bytes over the supplied bytes in order. |
| Signature / verification decision | Identity, Transport, Ledger, Messaging, Discovery, Files and Feeds; exactly 64-byte Ed25519 signature, or valid/invalid for the exact bytes. Verification does not assign trust. |
| Shared/derived secret or protected handle, authentication tag | Transport and envelope codecs; operation-specific sizes and context. Secrets are not application diagnostics or public events. |
| Generic encrypted object | [Identity](../../identity/inputs/README.md), Ledger claim client or application; exact header, ciphertext and tag, with complete length and recipient binding. |
| Authenticated plaintext | Authorized decrypting caller only; released only after all header, length, recipient and tag checks pass. |
| Structured failure | Caller; invalid key/format/length/tag or unavailable primitive/key store. No partial plaintext, synthetic success or secret-bearing diagnostics. |

Cryptography owns transient secret cleanup, not trust, spending or service state.
Stateless hash/verification can be repeated. Encryption must use fresh ephemeral
keys and nonce per new object; do not retry by reusing an uncontrolled nonce.
Keep primitive private handles scoped to their purpose and authorized caller.

## Independent acceptance examples

- Use the existing fixed envelope and Transport vectors with a deterministic
  test adapter; compare canonical bytes, digests, derived keys and signatures.
- Change one header byte or tag: decryption fails and emits no plaintext.
- Reject wrong key lengths, unsupported algorithms, all-zero X25519 results and
  overflowing lengths before allocation; no other module needs to be running.

All public-key validation and signature verification follows the
[Ed25519 verification profile](../README.md#ed25519-verification-profile),
including canonical point encoding, small-order rejection, scalar bounds and
identical acceptance for single and batch verification.
