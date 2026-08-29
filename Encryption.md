# CR2SE Encryption

CR2SE uses cryptography for identity, signatures, confidentiality, integrity, and secure communication between identities.

The [CR2SE Glossary](./Glossary.md) defines the common meaning of **identity**, **node**, **peer**, and **connection** used by this specification.

Confidentiality encryption is intentionally **not required for ordinary CR2SE
storage or communication**.

A CR2SE node may store or transmit plaintext data. Plaintext transmitted over a
version 1 CR2SE network connection is nevertheless integrity-protected and
bound to the identities authenticated by the mandatory `Network.md` handshake.

This is a deliberate property of the protocol.

CR2SE can be used for resources that are intended to be public, resources already protected by another network layer, resources whose operator does not require confidentiality, and resources where encryption would provide no useful benefit.

For example, a resource intended for public distribution does not need to be encrypted merely because CR2SE is used to transfer it.

Encryption is therefore applied when the data or operation requires it.

Identity is different.

Every CR2SE identity is cryptographic. As defined in `Identity.md`, an identity is based on an Ed25519 key pair and must be able to prove possession of its private identity key.

CR2SE version 1 therefore distinguishes between:

```text
cryptographic identity
    required

connection authentication and integrity
    required

data encryption
    optional

connection confidentiality
    optional
```

This document defines the cryptographic operations available to CR2SE.

It does not require every service to use them.

---

## 1. Cryptographic Capabilities

CR2SE version 1 defines the following cryptographic capabilities:

1. signing and signature verification;
2. identity proof;
3. encryption for a CR2SE identity;
4. key agreement between two peers;
5. authenticated encryption and integrity verification;
6. large-data encryption;
7. cryptographic key generation.

These capabilities are separate even when they are combined in a workflow.

For example, signing data and encrypting data solve different problems.

A signature proves that data was signed by the holder of an identity's private signing key.

Encryption prevents parties without the required secret from reading the data.

Authenticated encryption additionally detects modification of encrypted data.

Key agreement allows two parties to independently derive the same secret without transmitting that secret.

CR2SE defines each operation separately so implementations can combine them where required.

---

## 2. Version 1 Cryptographic Algorithms

CR2SE version 1 uses the following algorithms:

```text
Purpose                         Algorithm
---------------------------------------------------
Identity and signatures         Ed25519
Identity ID derivation          SHA-256
Public-key key agreement        X25519
Key derivation                  HKDF-SHA-256
Authenticated encryption        XChaCha20-Poly1305
Network frame integrity         XChaCha20-Poly1305 tag
```

For network frame integrity, `Network.md` invokes XChaCha20-Poly1305 with an
empty plaintext and authenticates the visible frame header and payload as
additional data. This produces a 16-byte tag without encrypting the payload.

Random values and cryptographic keys that require randomness must be generated using a cryptographically secure random number generator.

An implementation must not substitute another algorithm while representing the result as CR2SE version 1 cryptographic data.

Future CR2SE versions may define additional algorithms.

---

# Part I: Cryptographic Concepts

## 3. Signing

Signing allows an identity to prove that it authorized particular bytes.

A signature does not hide those bytes.

Conceptually:

```text
data
  +
identity private signing key
  |
  v
Ed25519
  |
  v
signature
```

Another participant can verify the signature using the corresponding public signing key:

```text
data
  +
signature
  +
identity public signing key
  |
  v
Ed25519 verification
  |
  +---- valid
  |
  +---- invalid
```

If verification succeeds, the verifier knows that the signature was created by a party possessing the corresponding private signing key.

The verifier also knows that the signed bytes have not been modified since the signature was created.

A valid signature does not imply that the contents are true, correct, trustworthy, or acceptable.

It establishes only cryptographic authorization of the signed bytes.

---

## 4. Identity Proof

CR2SE identities are defined in `Identity.md`.

The CR2SE ID is derived from the identity's Ed25519 public key.

Knowing a public key and its corresponding CR2SE ID does not prove that a remote peer possesses the private key.

To prove control of an identity, the peer must sign data that could not simply have been copied from an earlier authentication exchange.

Conceptually:

```text
Peer A                                  Peer B

claims Identity A
--------------------------------------->

fresh challenge
<---------------------------------------

sign challenge using
Identity A private key
--------------------------------------->

verify signature using
Identity A public key
```

Peer B must also verify that the public signing key derives the claimed CR2SE ID according to `Identity.md`.

Successful identity proof therefore establishes:

```text
claimed ID
    |
    v
corresponding Ed25519 public key
    |
    v
remote peer proves possession
of corresponding private key
```

The exact bytes signed during a particular protocol exchange must be defined by that exchange.

Implementations must not treat possession of a public key as proof of identity.

---

## 5. Encryption for an Identity

CR2SE defines a generic operation for encrypting data for one CR2SE identity.

Conceptually:

```text
encrypt(
    data,
    recipient_identity
)
```

The result can be decrypted only using cryptographic material belonging to the recipient identity.

The recipient may be another identity:

```text
Alice
  |
  | encrypt for Bob
  v
encrypted data
  |
  | store / forward / transfer
  v
Bob
  |
  | Bob's private encryption key
  v
original data
```

Or the recipient may be the same identity performing the encryption:

```text
Alice
  |
  | encrypt for Alice
  v
encrypted data
  |
  | store anywhere
  v
encrypted data
  |
  | Alice's private encryption key
  v
original data
```

CR2SE does not define a separate "encrypt for myself" operation.

Self-encryption is simply encryption where the sender and recipient are the same identity.

CR2SE version 1 encrypted data has exactly one recipient.

Encryption for multiple recipients is not defined by version 1.

---

## 6. Encryption Through an Intermediary

Encrypted data does not need to travel directly between sender and recipient.

For example:

```text
Alice
  |
  | encrypt for Bob
  v
ciphertext
  |
  v
Charlie
  |
  | store or forward
  v
ciphertext
  |
  v
Bob
  |
  | decrypt
  v
plaintext
```

Charlie does not need the decryption key.

Charlie may store, transfer, replicate, cache, or otherwise handle the ciphertext as ordinary bytes.

This is an important separation in CR2SE:

```text
ability to handle data
        !=
ability to read data
```

A service may therefore operate on encrypted data without understanding its plaintext contents.

The service using encrypted data defines who may request, store, retrieve, forward, or delete the encrypted bytes.

This document defines only their cryptographic protection.

---

## 7. Key Agreement

Sometimes two peers need to establish a shared secret rather than encrypt a persistent object for one identity.

CR2SE uses key agreement for this purpose.

Conceptually:

```text
Alice private key
        +
Bob public key
        |
        v
   key agreement
        |
        v
   shared secret
```

Bob independently performs the complementary operation:

```text
Bob private key
        +
Alice public key
        |
        v
   key agreement
        |
        v
   shared secret
```

Both obtain the same shared secret.

The secret itself is never transmitted.

An observer may know both public keys and observe all exchanged network data without being able to derive the shared secret from those values alone.

The raw result of key agreement must not be used directly as an XChaCha20-Poly1305 key.

It must first be passed through the key-derivation procedure defined later in this document.

---

## 8. Encryption and Integrity

CR2SE encryption provides both:

```text
confidentiality
+
integrity
```

Confidentiality means that a party without the required secret cannot recover the plaintext.

Integrity means that unauthorized modification of the encrypted data is detected.

CR2SE version 1 uses authenticated encryption.

Conceptually:

```text
plaintext
   +
encryption key
   +
nonce
   |
   v
authenticated encryption
   |
   +----> ciphertext
   |
   +----> authentication tag
```

During decryption:

```text
ciphertext
   +
authentication tag
   +
encryption key
   +
nonce
   |
   v
authenticated decryption
   |
   +---- valid ----> plaintext
   |
   +---- invalid --> reject
```

An implementation must not return unauthenticated plaintext when authentication fails.

Modified, corrupted, truncated, or incorrectly encrypted data must be treated as decryption failure.

---

## 9. Large-Data Encryption

CR2SE must support data substantially larger than available memory.

Large data must therefore be encryptable incrementally.

A large object is divided into chunks by the protocol or service responsible for that object.

Conceptually:

```text
large plaintext

+---------+
| chunk 0 |
+---------+
| chunk 1 |
+---------+
| chunk 2 |
+---------+
|   ...   |
+---------+
```

Each chunk is encrypted and authenticated as an independent encryption unit:

```text
chunk 0 -> encrypt -> encrypted chunk 0
chunk 1 -> encrypt -> encrypted chunk 1
chunk 2 -> encrypt -> encrypted chunk 2
...
```

This permits implementations to process large data without loading the complete object into memory.

It also permits data to flow through CR2SE incrementally:

```text
source
  |
  v
read chunk
  |
  v
encrypt chunk
  |
  v
send/store chunk
  |
  v
read next chunk
```

The protocol or service using large-data encryption defines:

* how the object is divided into chunks;
* the chunk size;
* chunk ordering;
* how the complete object is represented;
* how incomplete objects are handled.

For example, a CR2SE storage specification may define these properties for stored objects.

This document defines the cryptographic requirements for encrypting each encryption unit, not the storage layout.

A nonce must never be reused with the same encryption key.

Therefore, when several chunks are encrypted under the same derived key, the mechanism using the encryption primitive must assign a unique nonce to every encrypted chunk.

---

# Part II: Keys

## 10. Identity Signing Key Pair

Every CR2SE identity has an Ed25519 signing key pair as defined by `Identity.md`.

```text
Ed25519 private key
        |
        +---- sign
        |
        +---- prove identity

Ed25519 public key
        |
        +---- verify signatures
        |
        +---- derive CR2SE ID
```

The Ed25519 private key must remain secret.

The Ed25519 public key is not secret.

Identity generation and CR2SE ID derivation are defined by `Identity.md` and are not redefined here.

---

## 11. Encryption Key Pair

In addition to its Ed25519 identity key pair, every CR2SE identity has a persistent X25519 encryption key pair.

Conceptually:

```text
CR2SE Identity
    |
    +---- Ed25519 key pair
    |       |
    |       +---- identity
    |       +---- signatures
    |       +---- identity proof
    |
    +---- X25519 key pair
            |
            +---- encryption
            +---- key agreement
```

The X25519 private key must remain secret.

The X25519 public key may be distributed to other participants.

The encryption key pair is persistent because other participants must be able to encrypt data for an identity even when that identity is not currently connected.

For example, Alice may know Bob's public encryption key and encrypt data for Bob while Bob is offline.

---

## 12. Binding an Encryption Key to an Identity

An X25519 public key is not itself a CR2SE identity.

A participant receiving:

```text
CR2SE ID
+
X25519 public key
```

must not simply assume that the encryption key belongs to that identity.

The encryption public key must be cryptographically bound to the identity.

CR2SE version 1 does this using the identity's Ed25519 signing key.

Conceptually:

```text
X25519 public key
        |
        | signed using
        | identity Ed25519 private key
        v
encryption-key binding signature
```

A participant receiving an encryption public key must be able to verify:

```text
CR2SE ID
    |
    v
Ed25519 public key
    |
    +---- derives expected CR2SE ID
    |
    +---- verifies binding signature
                         |
                         v
                X25519 public key
```

Only after both checks succeed may the X25519 public key be treated as belonging to that CR2SE identity.

---

## 13. Encryption-Key Binding Bytes

Independent implementations must sign exactly the same bytes.

For CR2SE version 1, the encryption-key binding input is:

```text
"CR2SE-ENCRYPTION-KEY-V1" || X25519_Public_Key
```

where:

```text
"CR2SE-ENCRYPTION-KEY-V1"
```

means the ASCII bytes of that exact string, without a terminating zero byte.

`X25519_Public_Key` is the canonical 32-byte X25519 public key.

The binding signature is:

```text
Ed25519_Sign(
    identity_private_key,
    ASCII("CR2SE-ENCRYPTION-KEY-V1")
    ||
    x25519_public_key
)
```

Verification uses the Ed25519 public key belonging to the claimed CR2SE identity.

The constant prefix provides domain separation.

It prevents a signature created for an unrelated CR2SE purpose from accidentally being interpreted as authorization of an encryption key.

---

## 14. Generating Cryptographic Keys

A new CR2SE identity requires:

```text
Ed25519 signing key pair
+
X25519 encryption key pair
```

Both must be generated using cryptographically secure randomness according to the requirements of their respective algorithms.

Conceptually:

```text
cryptographically secure randomness
              |
       +------+------+
       |             |
       v             v
    Ed25519        X25519
       |             |
       v             v
 signing pair    encryption pair
       |             |
       +------+------+
              |
              v
       CR2SE identity
```

After generation:

1. the CR2SE ID is derived from the Ed25519 public key according to `Identity.md`;
2. the X25519 public key is signed using the Ed25519 private key;
3. the private keys are stored securely by the implementation.

Private-key storage is implementation-specific.

CR2SE does not require a particular keystore, file format, hardware security module, operating-system facility, or password-protection mechanism.

---

# Part III: Algorithms

## 15. Ed25519

CR2SE version 1 uses Ed25519 for digital signatures.

Conceptually:

```text
signature = Ed25519_Sign(
    private_key,
    data
)
```

Verification is:

```text
valid = Ed25519_Verify(
    public_key,
    data,
    signature
)
```

An Ed25519 public key is 32 bytes.

An Ed25519 signature is 64 bytes.

The exact data passed to the signing operation is defined by the protocol operation requiring the signature.

For example, identity-key binding defines its signing bytes in this document.

Other CR2SE documents may define signing inputs for credits, requests, records, messages, or other structures.

Implementations must sign the exact defined byte representation.

Signing an equivalent object serialized differently does not produce a signature over the required bytes.

---

## 16. X25519

CR2SE version 1 uses X25519 for public-key key agreement.

An X25519 public key is 32 bytes.

Conceptually, Alice calculates:

```text
shared_secret = X25519(
    alice_private_key,
    bob_public_key
)
```

Bob calculates:

```text
shared_secret = X25519(
    bob_private_key,
    alice_public_key
)
```

Both obtain the same 32-byte X25519 shared result.

The raw X25519 result is intermediate cryptographic material.

It must not be used directly as an application encryption key.

A derived encryption key must be produced using HKDF-SHA-256.

An implementation must reject an X25519 operation when the underlying X25519 implementation reports an invalid or unacceptable shared result.

---

## 17. HKDF-SHA-256

CR2SE version 1 uses HKDF with SHA-256 to derive usable encryption keys from key-agreement results.

Conceptually:

```text
X25519 shared secret
        |
        v
   HKDF-SHA-256
        |
        v
32-byte encryption key
```

Key derivation serves several purposes.

It converts key-agreement output into suitable key material and allows different protocol contexts to derive independent keys from cryptographic material.

The context used for a particular operation must therefore be defined by that operation.

Different cryptographic purposes must not silently reuse derived keys merely because they originated from the same X25519 result.

---

## 18. XChaCha20-Poly1305

CR2SE version 1 uses XChaCha20-Poly1305 for authenticated encryption.

It takes:

```text
plaintext
key
nonce
optional authenticated data
```

and produces authenticated ciphertext.

Conceptually:

```text
ciphertext = XChaCha20Poly1305_Encrypt(
    key,
    nonce,
    plaintext,
    authenticated_data
)
```

Decryption is:

```text
plaintext = XChaCha20Poly1305_Decrypt(
    key,
    nonce,
    ciphertext,
    authenticated_data
)
```

The encryption key is 32 bytes.

The nonce is 24 bytes.

The same nonce must never be reused with the same encryption key.

Authenticated data, when present, is authenticated but not encrypted.

This allows protocol metadata to be cryptographically bound to ciphertext without hiding that metadata.

If authentication fails, decryption fails.

No plaintext from a failed authenticated decryption may be accepted.

---

# Part IV: Workflows

## 19. Workflow: Sign Data

To sign arbitrary bytes:

```text
input:
    data
    identity private signing key

operation:
    Ed25519 sign

output:
    signature
```

Conceptually:

```text
data -------------------+
                        |
private signing key ----+
                        |
                        v
                     Ed25519
                        |
                        v
                    signature
```

To verify:

```text
data -------------------+
signature --------------+
public signing key -----+
                        |
                        v
                Ed25519 verify
                        |
                  +-----+-----+
                  |           |
                valid       invalid
```

The operation using the signature must define the exact bytes being signed.

---

## 20. Workflow: Verify an Identity

Suppose Bob receives a claim that the remote participant is Alice.

Bob must first obtain Alice's:

```text
claimed CR2SE ID
Ed25519 public key
```

Bob derives the CR2SE ID from the public key according to `Identity.md`.

If it does not equal the claimed ID, verification fails.

Bob then obtains proof that the remote participant possesses the corresponding private key.

A typical challenge workflow is:

```text
Bob                                      Alice

generate fresh challenge

challenge
--------------------------------------->

                              sign challenge
                              using Alice's
                              Ed25519 private key

signature
<---------------------------------------

verify using Alice's
Ed25519 public key
```

The protocol performing the authentication must define the exact challenge and
signed context. For a CR2SE network connection, `Network.md` defines a
role-bound transcript containing both peers' fresh nonces, identity keys, and
ephemeral keys.

The challenge must contain sufficient freshness to prevent a previously observed proof from simply being replayed as a new proof.

---

## 21. Workflow: Obtain an Identity's Encryption Key

Before Alice encrypts something for Bob, Alice needs Bob's authenticated X25519 public key.

Alice obtains:

```text
Bob CR2SE ID
Bob Ed25519 public key
Bob X25519 public key
Bob encryption-key binding signature
```

Alice performs:

```text
1. derive CR2SE ID from Bob's Ed25519 public key

2. compare derived ID with claimed Bob ID

3. construct:

   ASCII("CR2SE-ENCRYPTION-KEY-V1")
   ||
   Bob_X25519_Public_Key

4. verify the binding signature using Bob's
   Ed25519 public key

5. accept the X25519 key only if all checks succeed
```

Conceptually:

```text
Bob CR2SE ID
      ^
      | compare
      |
derive ID
      ^
      |
Bob Ed25519 public key
      |
      | verify signature
      v
Bob X25519 public key
```

After successful verification, Alice may treat the X25519 public key as Bob's encryption public key.

---

## 22. Workflow: Encrypt Data for an Identity

CR2SE uses hybrid encryption.

Public-key cryptography establishes a secret.

Symmetric authenticated encryption encrypts the actual data.

Suppose Alice wants to encrypt data for Bob.

Alice already has Bob's authenticated persistent X25519 public key.

Alice generates a new temporary X25519 key pair for this encrypted object:

```text
ephemeral_private
ephemeral_public
```

This key pair is used only for this encryption operation.

Alice calculates:

```text
shared_secret = X25519(
    ephemeral_private,
    bob_persistent_public_key
)
```

Alice derives a 32-byte encryption key from the shared secret using HKDF-SHA-256 with a context specific to CR2SE identity encryption.

Conceptually:

```text
Bob persistent public key
            +
ephemeral private key
            |
            v
          X25519
            |
            v
       shared secret
            |
            v
      HKDF-SHA-256
            |
            v
      encryption key
```

Alice generates a fresh 24-byte nonce using a cryptographically secure random number generator.

Alice encrypts the plaintext using XChaCha20-Poly1305.

The resulting encrypted object must carry enough non-secret information for Bob to perform decryption, including:

```text
ephemeral X25519 public key
nonce
ciphertext
```

The ephemeral private key is not included.

It may be discarded after encryption is complete.

---

## 23. Workflow: Decrypt Data for an Identity

Bob receives:

```text
ephemeral X25519 public key
nonce
ciphertext
```

Bob calculates:

```text
shared_secret = X25519(
    bob_persistent_private_key,
    ephemeral_public_key
)
```

This produces the same shared secret calculated by the sender.

Bob applies the same HKDF-SHA-256 derivation and obtains the same encryption key.

Conceptually:

```text
Bob persistent private key
            +
ephemeral public key
            |
            v
          X25519
            |
            v
       shared secret
            |
            v
      HKDF-SHA-256
            |
            v
      encryption key
            |
            v
XChaCha20-Poly1305 decrypt
            |
            v
         plaintext
```

If authenticated decryption fails, the encrypted data must be rejected.

---

## 24. Workflow: Encrypt Data for Yourself

No separate algorithm is required.

Alice obtains her own persistent X25519 public key and performs the normal "encrypt for an identity" operation with Alice as the recipient.

```text
recipient = Alice

Alice persistent public encryption key
            |
            v
normal identity encryption
            |
            v
ciphertext
```

Later:

```text
ciphertext
    |
    +
Alice persistent private encryption key
    |
    v
normal identity decryption
    |
    v
plaintext
```

The ciphertext can therefore be stored on a peer that is not trusted with the plaintext.

The storage peer needs no special cryptographic behavior.

From its perspective, the ciphertext is ordinary binary data.

---

## 25. Workflow: Send Encrypted Data Through Another Peer

Suppose Alice wants Bob to receive data through Charlie.

Alice performs the normal encryption-for-Bob workflow:

```text
plaintext
    |
    | encrypt for Bob
    v
ciphertext
```

Alice gives the ciphertext to Charlie.

```text
Alice
  |
  v
Charlie
  |
  v
Bob
```

Charlie does not participate in the cryptographic relationship between Alice and Bob.

Charlie only handles the encrypted bytes.

Bob eventually receives the encrypted object and performs the normal identity-decryption workflow.

Therefore:

```text
Alice ---- encryption relationship ---- Bob

  \                                  /
   \                                /
    +---- Charlie transports ------+
```

The permissions governing when Charlie accepts, stores, returns, or forwards those bytes belong to the service using the encryption mechanism.

They are not encryption rules.

---

## 26. Workflow: Establish Confidential Peer Communication

Every CR2SE version 1 network connection already performs the mandatory
handshake in `Network.md`. That handshake authenticates both identities,
performs an ephemeral X25519 exchange, and integrity-protects every later frame.
It deliberately leaves frame payloads visible.

Two connected peers may additionally encrypt application content when they
require confidentiality:

```text
Peer A                                  Peer B

   authenticated, integrity-protected CR2SE connection
<======================================================>

       application encryption negotiation
<------------------------------------------------------>

       application encryption negotiation
------------------------------------------------------->

       derive distinct encryption keys locally

        encrypted application payloads
<======================================================>
```

The application protocol must define the exact negotiation messages, encrypted
representation, key-confirmation behavior, and authenticated context. It may
use the persistent identity-encryption workflow defined in this document or a
new ephemeral X25519 exchange bound to the already authenticated connection.

Application encryption keys must be cryptographically distinct from the
network connection-integrity keys. An implementation must not reuse a network
integrity key, nonce prefix, or implicit frame sequence number for content
encryption.

The additional encryption must provide:

```text
the intended identities are already authenticated;
encryption keys are bound to the intended operation and identities;
application content is authenticated and encrypted;
nonces are unique for their key;
and replayed encryption negotiations or ciphertext are rejected where the
application semantics require freshness.
```

---

## 27. Content Encryption Is Above the Network Layer

`Network.md` defines how CR2SE frames are transferred and how their plaintext
headers and payloads receive mandatory connection-level integrity protection.
The framing layer does not assign confidentiality or application meaning to a
payload.

Content encryption operates on the bytes carried by the appropriate CR2SE
operation or service.

Conceptually:

```text
CR2SE application/service
        |
        | plaintext
        v
encryption layer
        |
        | ciphertext
        v
CR2SE operation payload
        |
        v
CR2SE Network frames
        |
        v
TCP
```

The network layer therefore continues to transport and integrity-protect bytes
normally.

It does not need to determine whether those bytes represent:

```text
plaintext
ciphertext
compressed data
file data
application data
or another representation
```

This separation is intentional.

A CR2SE implementation must not require modifications to the basic network
frame format merely because an application or service chooses to encrypt its
content. The resulting ciphertext is an ordinary network payload and also
receives the mandatory connection integrity tag.

---

## 28. Encrypted Communication Does Not Imply Encrypted Storage

Encryption properties apply to the specific data or operation for which they were requested.

For example:

```text
encrypted while communicating
```

does not automatically mean:

```text
encrypted when later stored
```

Likewise:

```text
encrypted object stored on a peer
```

does not require:

```text
encrypted CR2SE connection
```

An already encrypted object may be transferred through a plaintext CR2SE connection without exposing its plaintext.

These are independent properties.

Applications and services must explicitly select the protection required for their data.

---

## 29. Private Keys Must Not Be Transmitted

CR2SE private keys must not be transmitted as part of normal protocol operation.

This applies to:

```text
Ed25519 identity private keys

persistent X25519 private keys

ephemeral X25519 private keys
```

Public keys may be transmitted.

Signatures may be transmitted.

Nonces may be transmitted.

Ciphertext may be transmitted.

Private keys must remain under the control of the party that owns or generated them.

---

## 30. Nonces Are Not Secrets

The XChaCha20-Poly1305 nonce is not a password or secret key.

It may be stored or transmitted alongside the ciphertext.

For example:

```text
encrypted object

+------------------------------+
| ephemeral public key         |
+------------------------------+
| nonce                        |
+------------------------------+
| ciphertext + authentication  |
+------------------------------+
```

Security does not depend on hiding the nonce.

Security does depend on not reusing the same nonce with the same encryption key.

Implementations must therefore follow the nonce-generation rules of the operation using XChaCha20-Poly1305.

---

## 31. Ciphertext Is Untrusted Input

Encrypted data may be stored or transported by untrusted peers.

Implementations must therefore treat all received ciphertext and associated cryptographic metadata as untrusted input.

Before releasing plaintext, the implementation must successfully authenticate the encrypted data.

Malformed cryptographic structures must be rejected.

Invalid signatures must be rejected.

Invalid key bindings must be rejected.

Failed authenticated decryption must be rejected.

An implementation must not partially accept cryptographic data after verification failure.

---

## 32. Encryption Does Not Establish Trust

Successful cryptographic verification establishes cryptographic facts.

For example:

```text
signature valid
```

means that the corresponding private signing key produced the signature over the verified bytes.

It does not mean:

```text
the signer is trustworthy
```

Likewise:

```text
identity successfully authenticated
```

does not mean:

```text
the identity should receive resources
```

and:

```text
ciphertext successfully decrypted
```

does not mean:

```text
the plaintext is safe or correct
```

Trust, credits, service permissions, resource allocation, and reputation are separate CR2SE concerns.

Cryptography provides mechanisms those systems may rely upon.

It does not define their policy.

---

## 33. Algorithm Separation

CR2SE version 1 intentionally assigns different cryptographic jobs to different algorithms.

```text
Ed25519
    |
    +---- signatures
    +---- identity proof
    +---- authorize encryption key

X25519
    |
    +---- key agreement
    +---- establish encryption secrets

HKDF-SHA-256
    |
    +---- derive encryption keys
    +---- derive network integrity keys and nonce prefixes

XChaCha20-Poly1305
    |
    +---- encrypt bytes
    +---- authenticate encrypted bytes
    +---- authenticate visible network frames with empty plaintext

SHA-256
    |
    +---- CR2SE ID derivation
```

An implementation must not assume that because two algorithms use similarly named or related key types, their keys are interchangeable.

An Ed25519 private key is not an X25519 private key.

An Ed25519 public key is not an X25519 public key.

The CR2SE version 1 identity keeps these purposes explicit.

---

## 34. Summary

CR2SE does not make encryption mandatory for ordinary data.

Plaintext communication and plaintext storage are valid CR2SE behavior.
Plaintext network frames still receive the mandatory connection integrity tag
defined by `Network.md`.

Cryptography is used when a protocol operation requires identity, authorization, confidentiality, integrity, or secure key establishment.

A CR2SE version 1 identity contains:

```text
Ed25519 key pair
    identity + signatures

X25519 key pair
    encryption + key agreement
```

The X25519 public key is bound to the identity using an Ed25519 signature.

Data encryption uses:

```text
X25519
    |
    v
shared secret
    |
    v
HKDF-SHA-256
    |
    v
encryption key
    |
    v
XChaCha20-Poly1305
    |
    v
authenticated ciphertext
```

Encryption for oneself and encryption for another identity are the same operation with different recipients.

Encrypted data may be handled by intermediaries without granting those intermediaries access to the plaintext.

Large data is encrypted incrementally using independently authenticated encryption units, while the service responsible for the object defines chunking and object layout.

Confidential peer communication is implemented above the CR2SE network
transport layer.

The network layer remains responsible for transporting CR2SE frames,
authenticating the connected identities, and integrity-protecting every
post-handshake frame. It does not provide payload confidentiality.

This separation allows CR2SE to support both public resource sharing and private communication without forcing either model onto all services.
