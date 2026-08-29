# CR2SE Identity

CR2SE identities provide a stable way to identify participants independently of their network address, machine, process, or current connection.

Common domain terms such as **CR2SE identity**, **CR2SE ID**, **CR2SE node**, **peer**, and **connection** are defined in the [CR2SE Glossary](./Glossary.md).

An identity is based on a cryptographic key pair.

The public key is used to derive the identity identifier. The private key is used to prove control of that identity.

Conceptually:

```text
Private Key
    |
    | derives
    v
Public Key
    |
    | SHA-256
    v
CR2SE ID
```

An identity can be created locally without contacting another CR2SE node or any central authority.

CR2SE version 1 uses:

* Ed25519 for identity key pairs;
* SHA-256 for deriving identity identifiers;
* Base32 for the textual representation of identifiers.

---

## 1. Identity and Nodes

An identity and a node are different concepts.

A **CR2SE identity** is a cryptographic identity represented by a key pair and its derived identifier.

A **CR2SE node** is a running implementation of CR2SE.

A node operates using exactly one identity.

The same identity may be used by multiple nodes.

For example:

```text
                    Identity A
                 key pair + ID
                       |
          +------------+------------+
          |            |            |
          v            v            v
       Node 1        Node 2        Node 3
```

CR2SE does not assign meaning to why several nodes use the same identity.

They could represent:

* several machines owned by the same person;
* a phone and a computer;
* replicated servers;
* several processes;
* another arrangement chosen by the operator.

Likewise, CR2SE does not define an identity as representing a human, machine, organization, account, or service.

It represents only a cryptographic identity.

If an operator needs several identities on one machine, the operator may run several CR2SE nodes.

Each node still operates using exactly one identity.

---

## 2. Identity Ownership

Control of an identity is established by possession of its private key.

Anyone possessing the private key can act as that identity.

Therefore, copying an identity key pair to another machine allows that machine to operate using the same identity.

This is intentional.

CR2SE does not attempt to distinguish between different machines possessing the same private key.

From the protocol's perspective:

```text
same private key
        |
        v
same identity
```

Consequently, trust, credits, and other relationships associated with an identity are associated with the identity rather than with a particular machine.

The mechanisms used to store and protect private keys are implementation-specific.

---

## 3. Identity Generation

Identity generation is completely local.

Creating an identity does not require:

* registration;
* an Internet connection;
* communication with another CR2SE node;
* a central server;
* a certificate authority;
* permission from another participant.

To create a CR2SE version 1 identity, an implementation:

1. generates an Ed25519 key pair using a cryptographically secure random number generator;
2. obtains the canonical Ed25519 public key bytes;
3. derives the CR2SE ID from the public key as defined below;
4. securely stores the private key.

Conceptually:

```text
secure random data
        |
        v
Ed25519 key generation
        |
        +------> Private Key
        |
        +------> Public Key
                     |
                     v
               CR2SE ID
```

The private key must never be transmitted merely for the purpose of identifying a node.

---

## 4. Version 1 Identity Algorithms

CR2SE identity formats are designed to allow different cryptographic algorithms in future versions.

CR2SE version 1 defines one mandatory identity configuration:

```text
Identity format version: 1
Key algorithm:           Ed25519
ID hash algorithm:       SHA-256
Text encoding:           Base32
```

All CR2SE version 1 implementations must support this configuration.

Future versions may define additional algorithms if existing algorithms become unsuitable or stronger alternatives are required.

An implementation must not silently interpret an unknown identity version or key algorithm as a version 1 identity.

---

## 5. Public Key

CR2SE version 1 uses Ed25519 public keys.

An Ed25519 public key is exactly 32 bytes.

The public key is not secret.

It may be exchanged with other peers and may be stored by other nodes.

The corresponding private key must remain secret.

A peer can use the public key to verify cryptographic signatures produced by the corresponding private key.

The exact nonce, transcript, signature, ephemeral key exchange, and
peer-authentication messages used when establishing a CR2SE connection are
defined by `Network.md`. A service may use the authenticated remote identity
recorded for that connection without repeating the identity handshake for every
stream.

This document defines the identity itself, not the complete authentication handshake.

---

## 6. CR2SE ID

Every identity has a CR2SE ID.

The ID is a fixed-size 256-bit value.

For version 1, it is derived from the identity definition and public key using SHA-256.

The ID is not randomly generated independently of the key pair.

It is deterministically derived from the public key.

This means that the same identity information always produces the same ID.

---

## 7. ID Derivation

CR2SE must define the exact bytes used when deriving an ID so that independent implementations produce identical results.

For version 1, the hash input is:

```text
Identity Version || Key Algorithm || Public Key
```

where:

```text
Identity Version = 0x01
Key Algorithm    = 0x01
Public Key       = 32-byte Ed25519 public key
```

`0x01` is assigned to Ed25519 as the version 1 identity key algorithm identifier.

The complete hash input is therefore exactly 34 bytes:

```text
Offset | Size     | Field
0      | 1 byte   | Identity Version
1      | 1 byte   | Key Algorithm
2      | 32 bytes | Ed25519 Public Key
```

The CR2SE ID is:

```text
SHA-256(
    0x01
    ||
    0x01
    ||
    ed25519_public_key
)
```

The result is exactly 32 bytes.

Conceptually:

```text
┌──────────────────────┐
│ Identity Version     │ 1 byte
├──────────────────────┤
│ Key Algorithm        │ 1 byte
├──────────────────────┤
│ Ed25519 Public Key   │ 32 bytes
└──────────┬───────────┘
           |
           | SHA-256
           v
┌──────────────────────┐
│ CR2SE ID             │ 32 bytes
└──────────────────────┘
```

Including the identity version and key algorithm in the hash input prevents the meaning of the public-key bytes from being ambiguous if CR2SE introduces other identity formats in the future.

---

## 8. ID Properties

A CR2SE version 1 ID is:

```text
256 bits
32 bytes
```

The identifier space therefore contains:

```text
2^256
```

possible values.

CR2SE does not perform a global check to determine whether an ID already exists.

Uniqueness relies on the cryptographic properties of identity generation and SHA-256.

Accidental collisions are considered sufficiently improbable that CR2SE treats IDs as globally unique.

---

## 9. ID and Public Key Verification

Receiving an ID and a public key does not require trusting that they belong together.

A peer can independently calculate:

```text
SHA-256(
    identity_version
    ||
    key_algorithm
    ||
    public_key
)
```

and compare the result with the claimed ID.

If the calculated ID differs from the claimed ID, the public key does not belong to that CR2SE identity.

Conceptually:

```text
Received ID
    |
    | compare
    |
    +---------------------------+
                                |
Received Public Key             |
    |                           |
    v                           |
derive ID                       |
    |                           |
    +---------------------------+
```

Matching the ID proves only that the public key corresponds to the identifier.

It does not by itself prove that the remote peer possesses the corresponding private key.

Proof of possession requires a cryptographic signature or authentication
exchange. For CR2SE network connections, `Network.md` provides this proof and
cryptographically binds every later frame to the authenticated connection.

---

## 10. Identity Proof

A node claiming a CR2SE identity must be able to prove possession of the private key corresponding to that identity.

Conceptually:

```text
Peer A                            Peer B

        claims Identity X
------------------------------------>

        authentication challenge
<------------------------------------

        signature using X private key
------------------------------------>

        verify using X public key
```

The verifier must additionally confirm that the public key derives the claimed CR2SE ID.

Therefore identity verification ultimately establishes both:

```text
ID corresponds to Public Key

and

Peer possesses corresponding Private Key
```

For CR2SE network connections, the exact authentication transcript, fresh
nonce, signature format, replay protection, session-key derivation, and
connection-integrity procedure are defined by `Network.md`.

---

## 11. Identity Is Independent of Address

A CR2SE ID does not contain a network address.

For example, the following are not identities:

```text
192.0.2.10

192.0.2.10:8042

example.org:8042
```

A network address describes where a node may currently be reachable.

An identity describes who the peer cryptographically claims to be.

These properties must remain separate.

For example:

```text
Identity X
    |
    +---- reachable at Address A
    |
    +---- reachable at Address B
    |
    +---- reachable at Address C
```

Addresses may change without changing the identity.

Several nodes using the same identity may also be reachable through different addresses.

---

## 12. Identity and Connections

A network connection is not an identity.

The same identity may appear through different connections over time.

Likewise, local identifiers used by an implementation to refer to connections must not be treated as CR2SE identities.

Conceptually:

```text
connection
    |
    v
remote node
    |
    v
authenticated CR2SE identity
```

A connection may disappear while the identity continues to exist.

---

## 13. Textual Representation

The binary CR2SE ID is the canonical identifier.

For display, configuration, copying, QR codes, and other textual contexts, CR2SE defines a textual representation.

The 32-byte ID is encoded using Base32.

The Base32 representation must use the RFC 4648 Base32 alphabet:

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZ234567
```

Padding characters must not be included.

Therefore:

```text
=
```

must not appear at the end of a CR2SE ID.

The textual ID is prefixed with:

```text
cr2se:
```

Conceptually:

```text
32-byte CR2SE ID
        |
        v
Base32 without padding
        |
        v
cr2se:<base32-id>
```

A complete version 1 textual identity therefore has the form:

```text
cr2se:ABCDEFGHIJKLMNOPQRSTUVWXYZ234567...
```

The prefix is not part of the binary ID.

It exists to make textual identifiers recognizable and self-describing.

---

## 14. Base32 Normalization

CR2SE implementations must accept Base32 identity characters without regard to ASCII letter case.

For example:

```text
cr2se:ABCDEF...
```

and:

```text
cr2se:abcdef...
```

represent the same identity.

Implementations should produce uppercase Base32 when displaying the canonical textual representation.

Whitespace inside an ID is invalid.

The decoded Base32 value must contain exactly 32 bytes.

---

## 15. QR Identity

A CR2SE textual identity can be directly encoded in a QR code.

The QR code may contain:

```text
cr2se:<base32-id>
```

Scanning such a QR code identifies the CR2SE identity.

It does not necessarily provide enough information to locate a currently reachable node using that identity.

CR2SE Discovery allows an implementation with at least one usable bootstrap
relationship to look for current signed addresses using only the wanted ID.

---

## 16. Contact QR

CR2SE also permits QR codes intended for initial peer contact.

A contact QR contains:

* the CR2SE identity;
* a network address;
* a port.

The address is bootstrap information only.

It is not part of the identity.

A version 1 contact QR uses the following URI-style representation:

```text
cr2se:<base32-id>?address=<address>&port=<port>
```

For example:

```text
cr2se:ABCDEFGHIJKLMNOPQRSTUVWXYZ234567...?address=192.0.2.10&port=8042
```

The exact Base32 value above is illustrative.

The meaning of this contact information is:

```text
Try connecting to:

192.0.2.10:8042

and expect the peer to authenticate as:

cr2se:...
```

It must not be interpreted as:

```text
192.0.2.10:8042 is inherently this identity.
```

After establishing the connection, the remote node must cryptographically prove possession of the expected identity.

If the remote node authenticates using another identity, the bootstrap information must not be considered successfully resolved.

---

## 17. Bootstrap Information Is Mutable

An identity is stable while its contact information may change.

For example:

```text
time 1:

Identity X -> 192.0.2.10:8042


time 2:

Identity X -> 198.51.100.20:9000
```

Identity X remains the same.

A QR code containing an old address may therefore eventually contain obsolete bootstrap information.

The ID itself remains valid.

The CR2SE Discovery service allows nodes with another usable bootstrap
relationship to look for current signed addresses without requiring the
original bootstrap address. See [Discovery](./Discovery.md).

---

## 18. Identity and Distributed Discovery

CR2SE IDs are designed to be suitable for distributed lookup mechanisms.

The binary ID is:

* fixed length;
* 256 bits;
* derived using a cryptographic hash;
* expected to be approximately uniformly distributed.

These properties allow the ID to be used by distributed data structures such as DHTs.

The Discovery specification uses an XOR distance between 256-bit IDs for its
Kademlia-inspired candidate ordering.

The identity specification itself does not require any particular distributed
hash table or peer-discovery algorithm.

Discovery is a separate protocol concern.

Identity defines the identifier that such mechanisms may use.

---

## 19. Identity Creation Is Unrestricted

CR2SE intentionally does not prevent participants from generating multiple identities.

A participant may generate a new key pair and therefore a new identity at any time.

There is no central registry that limits identity creation.

CR2SE does not attempt to guarantee that:

* one identity corresponds to one human;
* one identity corresponds to one machine;
* one human has only one identity;
* one organization has only one identity.

Creating an identity is intentionally inexpensive.

---

## 20. New Identities Have No History

Creating a new identity does not transfer the state associated with another identity.

A newly created identity does not inherit:

* credits;
* trust;
* reputation;
* previous relationships;
* resource contributions;
* permissions associated with another identity.

Conceptually:

```text
Identity A
    credits: 100
    trust:   established

generate new key pair

Identity B
    credits: 0
    trust:   none
```

Identity B cannot claim Identity A's history merely because both identities are controlled by the same person or machine.

This property is important to CR2SE.

CR2SE does not make identity creation scarce.

Instead, useful relationships are expected to be established through interaction, resource contribution, trust, and credit exchange.

The exact rules for credits and trust are defined by the ledger and trust layers.

---

## 21. Identity Responsibility Across Nodes

When the same identity is used by several nodes, other peers treat those nodes as the same identity.

For example:

```text
                    Identity X
                       |
              +--------+--------+
              |                 |
           Node A             Node B
```

Suppose Identity X receives credits after Node A agrees to provide a resource.

If Node B later communicates using Identity X, it represents the same identity.

The fact that Node B may not possess the resource previously provided by Node A does not create another identity.

Any resulting effects on service fulfillment, trust, credits, or reputation apply to Identity X according to the relevant CR2SE protocols.

CR2SE does not track which physical machine performed previous actions unless a higher-level protocol explicitly chooses to record such information.

---

## 22. Private Key Loss

If the private key of an identity is lost, control of that identity is lost.

CR2SE version 1 does not provide account recovery.

It does not provide:

* password recovery;
* central identity restoration;
* recovery through another peer;
* automatic key replacement.

Without the private key, a participant can no longer prove control of the identity.

Any credits, trust, reputation, or relationships associated exclusively with that identity may therefore become inaccessible.

Implementations should clearly communicate the importance of protecting and backing up identity private keys.

---

## 23. Private Key Compromise

Anyone obtaining an identity's private key can impersonate that identity.

CR2SE version 1 does not attempt to determine which holder of a duplicated private key is the legitimate owner.

From the protocol's perspective, possession of the private key is the authority to act as the identity.

Implementations must therefore protect private keys appropriately for their environment.

---

## 24. Key Changes

Changing the identity key pair creates a new identity.

Because the CR2SE ID is derived from the public key:

```text
new key pair
    |
    v
new public key
    |
    v
new CR2SE ID
```

CR2SE version 1 does not define transparent key rotation that preserves an identity.

This is intentional.

A new key pair represents a new identity.

Future CR2SE versions may define mechanisms for announcing or proving relationships between old and new identities, but such mechanisms must not change the fundamental version 1 ID derivation rules.

---

## 25. Identity Comparison

Two CR2SE identities are the same identity if their 32-byte binary IDs are equal.

Implementations should perform identity comparison using the binary ID rather than comparing formatted strings.

For example:

```text
cr2se:ABCDEF...
```

and:

```text
cr2se:abcdef...
```

may have different textual representations while identifying the same 32-byte value.

After parsing and Base32 decoding, identity equality is simply:

```text
id_a == id_b
```

---

## 26. Storage Representation

CR2SE does not prescribe how implementations store identity information locally.

An implementation may use:

* files;
* operating-system key stores;
* encrypted databases;
* hardware-backed key storage;
* secure elements;
* another storage mechanism.

The storage mechanism must not change the CR2SE identity visible to other implementations.

For example, a Rust implementation and a Java implementation using the same Ed25519 key pair must derive the same CR2SE ID.

Local private-key serialization formats are implementation-specific unless another CR2SE specification explicitly standardizes an identity export format.

---

## 27. Identity Portability

An identity may be moved or copied between CR2SE implementations by transferring the corresponding key pair.

For example:

```text
Rust CR2SE implementation
          |
          | transfer identity key pair
          v
Android CR2SE implementation
```

If both implementations use the same key pair, both derive the same CR2SE ID.

The mechanism used to export, import, encrypt, or protect private key material is not defined by this document.

A future CR2SE specification may define a portable identity backup format.

---

## 28. Separation of Responsibilities

Identity answers:

```text
Who is this peer?
```

It does not answer:

```text
Where is this peer?

What services does this peer provide?

How much credit does this peer have?

How much do I trust this peer?

What data is this peer storing?

How should I route messages to this peer?
```

Those concerns belong to other CR2SE layers.

Conceptually:

```text
Identity
    |
    +-- cryptographic identity
    +-- public key
    +-- stable ID
    +-- proof of private-key possession


Network
    |
    +-- connections
    +-- mutual identity authentication
    +-- connection frame integrity
    +-- streams
    +-- data transfer


Discovery / Board
    |
    +-- addresses
    +-- services
    +-- resource requests
    +-- peer information


Ledger
    |
    +-- credits
    +-- trust
    +-- relationships
```

Keeping these concepts separate allows an identity to remain stable while addresses, services, connections, and resources change.

---

## 29. Version 1 Summary

A CR2SE version 1 identity has the following properties:

```text
Key algorithm:
    Ed25519

Public key:
    32 bytes

ID hash:
    SHA-256

ID hash input:
    0x01
    ||
    0x01
    ||
    32-byte Ed25519 public key

Binary ID:
    32 bytes / 256 bits

Text encoding:
    RFC 4648 Base32
    without padding

Canonical text:
    uppercase Base32

Text prefix:
    cr2se:

Identity creation:
    local and permissionless

Identity recovery:
    none

Key rotation preserving ID:
    not supported in version 1

Nodes per identity:
    one or more

Identities per node:
    exactly one
```

The essential relationship is:

```text
Private Key
     |
     v
Public Key
     |
     | version + algorithm + public key
     v
SHA-256
     |
     v
CR2SE ID
     |
     +------> Base32 textual ID
     |
     +------> QR identity
     |
     +------> distributed lookup key
     |
     +------> ledger/trust identity
```

The CR2SE ID identifies the cryptographic identity.

Everything else in CR2SE builds relationships around that identifier.
