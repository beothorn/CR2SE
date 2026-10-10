# Identity

## Module boundary

**Required** in the [minimum useful node profile](../../ModuleContracts.md#required-and-optional-capabilities).
Owns persistent identity credentials and contacts. Consumes Cryptography and a
protected platform key store; Discovery lookup is optional.

Implement against the [input contract](./inputs/README.md) and
[output contract](./outputs/README.md), using the shared
[composition and recovery rules](../../ModuleContracts.md).
This boundary supports a monolith, separate logical components or separate
processes without changing the service or wire contract below.

An identity has an Ed25519 key for signing and a separate persistent X25519
key for decryption. Its ID comes from the Ed25519 public key. A person,
organization, device, program, or network of agents may control an identity;
the protocol does not require a human owner.

A **node** is one running implementation acting as one identity. Several nodes
may share an identity. Addresses, machines, and connections are not identities.

See [pseudocode](./pseudocode/README.md), [diagrams](./diagrams/README.md), and
the [glossary](../../Glossary.md).

## Creation

Creation is local and needs no registration or network access:

1. Generate independent Ed25519 and X25519 key pairs with cryptographically
   secure randomness.
2. Derive the ID from the Ed25519 public key.
3. Sign the X25519 public key using the [key-binding format](../cryptography/README.md).
4. Protect and back up both private keys.

Do not convert an Ed25519 key into an X25519 key. Private-key storage and backup
formats are implementation choices.

## Binary and textual IDs

The version 1 ID is exactly:

```text
SHA-256(0x01 || 0x01 || ed25519PublicKey)
```

The first byte is the identity version; the second selects Ed25519. The public
key is exactly 32 bytes, the hash input is 34 bytes, and the ID is 32 bytes.
Reject unsupported versions, algorithms, and key lengths. Compare identities
using these 32 bytes, not their address or display spelling.

The textual form is `cr2se:` followed by RFC 4648 Base32:

- Exactly 52 Base32 characters, without `=` padding.
- Alphabet `ABCDEFGHIJKLMNOPQRSTUVWXYZ234567`; accept lowercase letters too.
- Emit uppercase Base32 and the exact lowercase prefix `cr2se:`.
- Reject whitespace, wrong lengths, invalid characters, and nonzero unused
  bits in the last Base32 character. Do not silently trim an ID.

Example from the [transport vectors](../transport/pseudocode/TestVectors.md):

```text
cr2se:3FEKTKCHTGJQLPTATWZZ3HFFBN6JGGCOYNV56CAPN5DECXQZSJOQ
```

To validate a key for a claimed ID, derive the ID and compare it with the claim.
This proves the key-to-ID relationship, not possession of the private key.
Possession requires a signature over the operation's exact bytes.
[Transport](../transport/README.md) defines the fresh connection proof. Do not
substitute a reusable signature over only the public ID.

## Contact information and QR codes

A QR code may contain the textual ID alone, or one bootstrap endpoint:

```text
cr2se:<base32-id>?address=<address>&port=<port>
```

For this format, `address` is an IPv4 or IPv6 literal without brackets or a zone
identifier. Percent-encode UTF-8 bytes other than ASCII letters, digits, `-`,
`.`, `_`, and `~`; IPv6 colons therefore appear as `%3A`. Decode once. `port` is
decimal `1..65535`, without a sign or leading zeros. Require one `address` and
one `port`, in either order. Reject duplicate or unknown parameters and
fragments. DNS endpoints use Discovery records instead.

Contact data is a hint. After connecting, require the authenticated remote ID
to match the contact ID. A mismatch fails resolution. An old address can stop
working without changing the identity.

[Discovery](../discovery/README.md) can find current signed endpoints once the
requester has a usable bootstrap relationship. An ID alone cannot locate an
unknown network with no initial contact.

## Trust, multiple nodes, and recovery

Creating a key grants no trust, credits, or service access. Unknown identities
start with zero local trust. [Ledger](../ledger/README.md) explains how a
relationship begins and how credits are earned.

Nodes sharing an identity share its authority and obligations. They must
coordinate balances, replay records, Boards, and accepted service state before
presenting themselves as one coherent participant. Copying keys alone does
not copy that state. The first PoC should use one active writer per identity;
other devices may be offline backups. Internal replication is not standardized.

Losing the signing private key loses control of the identity. Changing it
creates a new ID. Version 1 has no central recovery, identity-preserving signing
key rotation, or way to distinguish two holders of the same private key.

Losing the persistent X25519 private key prevents decryption of objects
encrypted for that key. Replacing it does not change the ID, but version 1
defines no encryption-key rotation or selection procedure. Preserve the
persistent pair across nodes and backups.

Portable recovery needs keys **and** a recovery catalog: provider IDs,
bootstrap endpoints, lease IDs, expirations, content hashes, encryption formats,
and application metadata needed to reconstruct data. Storage does not enumerate
a user's leases. Back up this catalog independently; do not put its only
location inside data that cannot be found without it.
