# Cryptography

## Module boundary

**Required** in the [minimum useful node profile](../../ModuleContracts.md#required-and-optional-capabilities).
Owns cryptographic operations and transient secrets. Consumes platform
randomness and protected key handles; no running CR2SE module is required.

Implement against the [input contract](./inputs/README.md) and
[output contract](./outputs/README.md), using the shared
[composition and recovery rules](../../ModuleContracts.md).
This boundary supports a monolith, separate logical components or separate
processes without changing the service or wire contract below.

Use the [acceptance test pseudocode](./acceptanceTests/README.md) to guide
implementation and check its observable results.

Cryptography supplies signatures, key agreement, authenticated encryption, and
hashing. It proves specific facts about keys and bytes. It does not establish
trust, authorize resource use, or prove that returned content is true or safe.

See [pseudocode and fixed vector](./pseudocode/README.md),
[diagrams](./diagrams/README.md), [Identity](../identity/README.md), and
[Transport](../transport/README.md).

## Algorithms and key separation

| Algorithm | Purpose | Sizes |
|---|---|---|
| Ed25519 | Identity signatures and encryption-key binding | Public key 32 bytes; signature 64 bytes. |
| X25519 | Key agreement | Public key and shared result 32 bytes. |
| HKDF-SHA-256 | Derive purpose-specific keys | Encryption key output 32 bytes. |
| XChaCha20-Poly1305 | Authenticated encryption | Key 32 bytes; nonce 24 bytes; tag 16 bytes. |
| SHA-256 | IDs and content hashes | Digest 32 bytes. |

Generate independent signing and encryption pairs using a cryptographically
secure random generator. Keep both private keys secret. Do not convert or
interchange Ed25519 and X25519 keys. Use established algorithm implementations;
the protocol defines their inputs, not a replacement crypto implementation.

Sign exactly the bytes defined by the operation. Native object serialization,
textual IDs, or JSON with different formatting are not substitutes for canonical
binary signing bytes. Ed25519 uses the ordinary Ed25519 operation, not Ed25519ph.

Reject an invalid X25519 operation and reject an all-zero shared result even if
the underlying library does not report it. Do not use the raw shared result as
an encryption key. Derive a key with the operation's exact HKDF salt and info.

## Persistent encryption credential

An identity publishes its Ed25519 public key, persistent X25519 public key, and
binding signature. The signature input is exactly:

```text
ASCII("CR2SE-ENCRYPTION-KEY-V1") || x25519PublicKey
```

The prefix has no terminating zero or length field; the key is 32 bytes.
Verify that the Ed25519 key derives the expected identity, then verify this
64-byte signature. Only after both checks may the encryption key be used.
Messaging defines the Board credential fields used for publication.

## Generic encryption for one identity

Use the same operation for another recipient or for a backup encrypted to
yourself. Validate the recipient's credential, then generate a fresh ephemeral
X25519 pair and a fresh 24-byte nonce for each object. Calculate:

```text
shared = X25519(ephemeralPrivateKey, recipientPersistentPublicKey)

kdfContext =
    0x01 || 0x01 || 0x01 || 0x01
    || recipientId
    || recipientPersistentPublicKey
    || ephemeralPublicKey
    || nonce

salt = SHA-256(
    ASCII("CR2SE-IDENTITY-ENCRYPTION-SALT-V1") || 0x00 || kdfContext)

prk = HKDF-Extract-SHA-256(salt, shared)

key = HKDF-Expand-SHA-256(prk,
    ASCII("CR2SE-IDENTITY-ENCRYPTION-KEY-V1") || 0x00 || kdfContext,
    32)
```

The four bytes select format version 1, X25519, HKDF-SHA-256, and
XChaCha20-Poly1305. IDs and public keys are 32 bytes each. The context is exactly
124 bytes. The explicit `0x00` bytes above are part of the derivation.

The encrypted object starts with this 132-byte header:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 1 | Format version `0x01` |
| 1 | 1 | Key agreement `0x01` |
| 2 | 1 | Key derivation `0x01` |
| 3 | 1 | Authenticated encryption `0x01` |
| 4 | 32 | Recipient ID |
| 36 | 32 | Recipient persistent X25519 public key |
| 68 | 32 | Ephemeral X25519 public key |
| 100 | 24 | Nonce |
| 124 | 8 | Sealed length, unsigned big-endian |

Sealed length is plaintext length plus 16, at least 16. Check length arithmetic
before allocation. Use the complete header as authenticated data:

```text
sealed = XChaCha20-Poly1305(key, nonce, plaintext, header)
object = header || ciphertext || 16-byte tag
```

Exactly `sealed length` bytes follow the header, with no trailing bytes inside
this object. There is no additional external authenticated-data argument. A
service needing to bind extra metadata includes it in the plaintext or defines
a separate exact construction. Messaging has such a service-specific envelope;
its `cr2se.identity-encrypted.v1` payload is not this generic 132-byte envelope.

## Decryption and validation

1. Validate format, algorithms, lengths, and local resource limits.
2. Compare the recipient ID and persistent key with the intended local identity.
3. Compute X25519 using the local persistent private key and the ephemeral
   public key; reject an all-zero result.
4. Derive the same key using the exact context above.
5. Authenticate and decrypt with the complete header as authenticated data.
6. Release plaintext only after authentication succeeds.

On any failure, reject the complete object. Do not release provisional plaintext,
partially accept malformed metadata, or log secret material. Erase ephemeral
private keys, intermediate secrets, PRKs, and derived keys when no longer needed.
Never reuse a nonce with the same encryption key. Nonces are public, not passwords.

This envelope authenticates ciphertext and recipient binding, not the sender.
Sender authentication requires a separate signature or authenticated protocol.
Persistent recipient-key compromise can expose previously captured encrypted
objects; generic identity encryption does not promise forward secrecy.

## Large objects and independent protection

A library may encrypt incrementally, but it must not release a unit's plaintext
before validating that unit's tag. The service or application defines chunk
boundaries, ordering, and the manifest when using several encrypted objects.
Independent valid chunks alone do not detect deletion or reordering. An
authenticated manifest must bind their positions, lengths, and hashes.

For the first PoC, use a single generic encrypted object per bounded storage
object and retain its format in the recovery catalog. Larger application-level
chunking can be added without changing Storage's opaque-byte contract.

Transport authenticates connections and protects frame integrity. Its headers
and payloads remain visible. Content encryption hides selected content, not
identity, length, timing, or access patterns. Plaintext storage and public content
are conforming, but must not be described as confidential.

Encrypting bytes on a connection does not automatically encrypt stored data.
Choose protection at each boundary. Never send private identity keys to a peer
to request storage or computation. A confidential interactive session above
Transport requires its own explicit service protocol; this module does not
define a second generic session handshake.
