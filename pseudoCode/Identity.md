# Identity pseudocode

This document translates the normative identity contract in
[`Identity.md`](../Identity.md) into implementation-neutral pseudocode. The
specification remains authoritative. Names such as `SecureKeyStore`, byte
arrays, and cryptographic operations describe responsibilities, not required
classes, storage formats, or APIs.

The pseudocode assumes conventional implementations of Ed25519, SHA-256, and
RFC 4648 Base32. Private-key serialization, backup, recovery, and key-store
protection are not wire formats defined by CR2SE version 1.

---

## 1. Constants and data structures

```text
IDENTITY_VERSION              = 0x01
KEY_ALGORITHM_ED25519         = 0x01
PUBLIC_KEY_SIZE               = 32
ID_SIZE                       = 32

TEXT_PREFIX                   = ASCII("cr2se:")
BASE32_ALPHABET               = ASCII("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
BASE32_ENCODED_ID_SIZE        = 52
TEXTUAL_ID_SIZE               = 58

PublicIdentity:
    version                   uint8
    keyAlgorithm              uint8
    publicKey                 32 bytes
    id                        32 bytes

LocalIdentity:
    publicIdentity            PublicIdentity
    privateKeyHandle          protected Ed25519 private-key handle

ContactBootstrap:
    expectedRemoteId          32 bytes
    address                   application-validated network address
    port                      application-validated network port
```

The binary 32-byte ID is the canonical identity identifier. A node is
configured with exactly one `LocalIdentity`, although the same identity may be
installed on more than one node.

---

## 2. Version 1 identity generation

```text
function generateIdentity(secureKeyStore):
    keyPair = Ed25519.generateKeyPair(CSPRNG)

    publicKey = Ed25519.canonicalPublicKeyBytes(keyPair.publicKey)
    if length(publicKey) != PUBLIC_KEY_SIZE:
        securelyErase(keyPair.privateKey)
        raise InternalError("unexpected Ed25519 public-key size")

    id = deriveVersion1Id(publicKey)

    // The key store chooses its protected local representation. It must not
    // alter the key pair visible to other CR2SE implementations.
    try:
        privateKeyHandle = secureKeyStore.storeEd25519PrivateKey(
            keyPair.privateKey
        )
    finally:
        securelyEraseTemporaryCopies(keyPair.privateKey)

    if privateKeyHandle is ERROR:
        raise IdentityStorageFailure

    return LocalIdentity {
        publicIdentity: PublicIdentity {
            version: IDENTITY_VERSION,
            keyAlgorithm: KEY_ALGORITHM_ED25519,
            publicKey: publicKey,
            id: id
        },
        privateKeyHandle: privateKeyHandle
    }
```

Generation is local and requires no registration, network connection,
certificate authority, or uniqueness lookup. `CSPRNG` and the Ed25519 library
must provide cryptographically secure key generation.

Failure to store the private key successfully fails identity creation. An
implementation must not report a durable identity while retaining its only
private-key copy merely in volatile temporary memory.

---

## 3. ID derivation

```text
function deriveVersion1Id(ed25519PublicKey):
    if length(ed25519PublicKey) != PUBLIC_KEY_SIZE:
        raise InvalidPublicKey("Ed25519 public key must be exactly 32 bytes")

    hashInput = byte(IDENTITY_VERSION)
        || byte(KEY_ALGORITHM_ED25519)
        || ed25519PublicKey

    assert length(hashInput) == 34

    id = SHA256(hashInput)
    assert length(id) == ID_SIZE
    return id


function deriveId(version, keyAlgorithm, publicKey):
    if version != IDENTITY_VERSION:
        raise UnsupportedIdentityVersion(version)

    if keyAlgorithm != KEY_ALGORITHM_ED25519:
        raise UnsupportedIdentityKeyAlgorithm(keyAlgorithm)

    return deriveVersion1Id(publicKey)
```

The two leading bytes are part of the hash input. They must not be omitted,
encoded as text, reordered, or replaced by implementation-specific algorithm
identifiers.

`deriveVersion1Id` defines the deterministic identifier calculation. When a
received public key will also be used for signature verification, the
cryptographic library must parse and validate it according to that library's
Ed25519 rules.

---

## 4. Public identity validation

```text
function validatePublicIdentity(version, keyAlgorithm, publicKey, claimedId):
    if length(claimedId) != ID_SIZE:
        raise InvalidIdentity("CR2SE ID must be exactly 32 bytes")

    derivedId = deriveId(version, keyAlgorithm, publicKey)

    if derivedId != claimedId:
        raise IdentityMismatch

    verificationKey = Ed25519.parsePublicKey(publicKey)
    if verificationKey is ERROR:
        raise InvalidPublicKey

    return PublicIdentity {
        version: version,
        keyAlgorithm: keyAlgorithm,
        publicKey: publicKey,
        id: derivedId
    }
```

A matching ID establishes only the relationship between the public-key bytes
and the identifier. It does not establish that a peer controls the private
key.

---

## 5. Canonical textual representation

```text
function formatTextualCr2seId(id):
    if length(id) != ID_SIZE:
        raise InvalidIdentity("CR2SE ID must be exactly 32 bytes")

    encoded = Base32.RFC4648.encode(
        bytes = id,
        alphabet = BASE32_ALPHABET,
        includePadding = false,
        letterCase = UPPERCASE
    )

    assert length(encoded) == BASE32_ENCODED_ID_SIZE
    assert '=' not in encoded

    return TEXT_PREFIX || encoded
```

The prefix is textual metadata and is not included in the binary ID or its
hash input.

---

## 6. Textual ID parsing and normalization

```text
function parseTextualCr2seId(text):
    if text is not a string:
        raise InvalidTextualId("textual CR2SE ID must be a string")

    if byteLengthUtf8(text) != TEXTUAL_ID_SIZE:
        raise InvalidTextualId("wrong textual CR2SE ID length")

    if not text starts with exact ASCII bytes TEXT_PREFIX:
        raise InvalidTextualId("missing cr2se: prefix")

    encoded = bytes after TEXT_PREFIX

    if any byte in encoded is ASCII whitespace:
        raise InvalidTextualId("whitespace is forbidden")

    if '=' in encoded:
        raise InvalidTextualId("Base32 padding is forbidden")

    for each byte in encoded:
        if byte is not one of ASCII A..Z, ASCII a..z, ASCII 2..7:
            raise InvalidTextualId("invalid RFC 4648 Base32 character")

    uppercaseEncoded = ASCII-uppercase(encoded)

    id = Base32.RFC4648.decodeStrict(
        text = uppercaseEncoded,
        alphabet = BASE32_ALPHABET,
        padding = FORBIDDEN,
        requireZeroUnusedBits = true
    )

    if decoding failed or length(id) != ID_SIZE:
        raise InvalidTextualId("Base32 value must decode to exactly 32 bytes")

    // This also rejects an alternative final symbol with nonzero unused bits.
    canonicalEncoded = Base32.RFC4648.encode(
        bytes = id,
        alphabet = BASE32_ALPHABET,
        includePadding = false,
        letterCase = UPPERCASE
    )
    if canonicalEncoded != uppercaseEncoded:
        raise InvalidTextualId("non-canonical Base32 bits")

    return id


function normalizeTextualCr2seId(text):
    return formatTextualCr2seId(parseTextualCr2seId(text))
```

Only Base32 letters are case-insensitive. Parsing does not apply Unicode case
folding, trim surrounding text, permit internal whitespace, accept padding, or
infer a missing prefix. Canonical output always uses the lowercase `cr2se:`
prefix and uppercase Base32.

For 32 input bytes, unpadded RFC 4648 Base32 is exactly 52 characters. Strict
unused-bit checking ensures that case is the only accepted textual variation
for a particular binary ID.

---

## 7. Identity comparison

```text
function sameIdentity(left, right):
    leftId = obtainCanonicalBinaryId(left)
    rightId = obtainCanonicalBinaryId(right)

    require length(leftId) == ID_SIZE
    require length(rightId) == ID_SIZE

    return leftId == rightId


function obtainCanonicalBinaryId(value):
    if value is a 32-byte binary CR2SE ID:
        return value

    if value is a textual CR2SE ID:
        return parseTextualCr2seId(value)

    if value is a validated PublicIdentity:
        return value.id

    raise InvalidIdentity
```

Formatted strings are not compared directly because uppercase and lowercase
Base32 forms represent the same identity.

---

## 8. Signing and proof of private-key possession

```text
function signProtocolMessage(localIdentity, protocolDefinedMessage):
    require localIdentity.publicIdentity.version == IDENTITY_VERSION
    require localIdentity.publicIdentity.keyAlgorithm == KEY_ALGORITHM_ED25519

    return Ed25519.sign(
        localIdentity.privateKeyHandle,
        protocolDefinedMessage
    )


function verifyProtocolProof(
    claimedId,
    version,
    keyAlgorithm,
    publicKey,
    protocolDefinedMessage,
    signature
):
    publicIdentity = validatePublicIdentity(
        version,
        keyAlgorithm,
        publicKey,
        claimedId
    )

    if not Ed25519.verify(
        publicIdentity.publicKey,
        protocolDefinedMessage,
        signature
    ):
        raise InvalidIdentityProof

    return publicIdentity
```

The calling protocol must define the exact signed bytes and provide any
required domain separation, roles, freshness, and replay protection. These
helpers do not define a generic CR2SE authentication wire exchange. Network
connections use the HELLO transcript, role-bound AUTH message, and connection
state machine in [`Network.md`](./Network.md).

A service may rely on the remote identity already authenticated by that
connection. It need not repeat an identity proof on every stream.

---

## 9. Loading an existing local identity

Local serialization is implementation-specific, but loading must not allow
mismatched stored fields to change the externally visible identity.

```text
function loadLocalIdentity(secureKeyStore, privateKeyHandle):
    privateKey = secureKeyStore.openEd25519PrivateKey(privateKeyHandle)
    if privateKey is ERROR:
        raise IdentityUnavailable

    try:
        publicKey = Ed25519.deriveCanonicalPublicKey(privateKey)
        id = deriveVersion1Id(publicKey)
    finally:
        securelyEraseTemporaryCopies(privateKey)

    return LocalIdentity {
        publicIdentity: PublicIdentity {
            version: IDENTITY_VERSION,
            keyAlgorithm: KEY_ALGORITHM_ED25519,
            publicKey: publicKey,
            id: id
        },
        privateKeyHandle: privateKeyHandle
    }
```

If local storage also contains cached public-key or ID fields, recompute them
from the private key and reject any mismatch. Copying the same valid key pair
to another implementation produces the same public key and CR2SE ID.

CR2SE version 1 defines no portable private-key encoding, password recovery,
central recovery, key replacement preserving an ID, or standard export
format. Those operations must not be inferred from the textual ID.

---

## 10. Identity QR payload

```text
function makeIdentityQrPayload(id):
    return formatTextualCr2seId(id)


function parseIdentityQrPayload(scannedText):
    return parseTextualCr2seId(scannedText)
```

An identity QR identifies a CR2SE identity only. It does not assert a current
network address or prove possession of the corresponding private key.

---

## 11. Contact QR bootstrap handling

A version 1 contact QR has the URI-style shape:

```text
cr2se:<base32-id>?address=<address>&port=<port>
```

`Identity.md` does not define an address grammar, a hostname or IP-literal
preference, query-value escaping, or numeric port-validation rules. Those
details remain with the application and network-address layer; an identity
parser must not make them part of the CR2SE ID.

After that layer has parsed and validated the contact fields, identity handling
is:

```text
function useContactBootstrap(identityText, validatedAddress, validatedPort):
    expectedId = parseTextualCr2seId(identityText)

    contact = ContactBootstrap {
        expectedRemoteId: expectedId,
        address: validatedAddress,
        port: validatedPort
    }

    connection = Network.connect(
        address = contact.address,
        port = contact.port,
        expectedRemoteId = contact.expectedRemoteId
    )

    if connection authentication fails:
        raise BootstrapResolutionFailed

    if connection.authenticatedRemoteId != contact.expectedRemoteId:
        close connection
        raise BootstrapResolutionFailed

    return connection
```

The address and port are mutable bootstrap hints. Cache updates, redirects, or
later discovery results may replace them, but must not replace
`expectedRemoteId` while claiming to resolve the same contact.

---

## 12. Node configuration and identity lifecycle

```text
function startNode(configuredIdentityHandles, secureKeyStore):
    if count(configuredIdentityHandles) != 1:
        raise ConfigurationError("a CR2SE node operates using exactly one identity")

    localIdentity = loadLocalIdentity(
        secureKeyStore,
        configuredIdentityHandles[0]
    )

    return Node {localIdentity: localIdentity}


function classifyConfiguredKeyChange(currentIdentity, candidateIdentity):
    if candidateIdentity.publicIdentity.id == currentIdentity.publicIdentity.id:
        return SAME_IDENTITY

    // A different key pair is a different version 1 identity. There is no
    // transparent rotation or transfer of identity-bound history.
    return NEW_IDENTITY
```

Credits, trust, reputation, relationships, and prior resource commitments are
associated with the binary ID. Creating or configuring another identity does
not copy those properties. Several nodes configured with the same key pair are
indistinguishable as identities to peers.

If the private key is lost, version 1 cannot recover control of the identity.
If it is copied or compromised, every holder can act as that identity; the
protocol cannot identify a preferred or original holder.

---

## 13. Private-key handling invariants

```text
never include a private key in:
    a binary CR2SE ID;
    a textual CR2SE ID;
    an identity QR;
    a contact QR;
    a public identity descriptor;
    or a message sent merely to identify a node

protect private keys using mechanisms appropriate to the environment;
use private keys only through the minimum required signing or derivation API;
erase avoidable plaintext temporary copies;
do not log private keys or deterministic test private keys used in production;
make backup and compromise consequences clear to the operator;
and treat a newly generated key pair as a newly generated identity.
```

Hardware-backed stores, operating-system key stores, encrypted files, secure
elements, and other storage designs are all permitted if they preserve the
same Ed25519 public key and derived CR2SE ID.

---

## 14. Layer boundaries

```text
Identity:
    generate or load the Ed25519 key pair
    derive and format the stable CR2SE ID
    validate an ID/public-key relationship
    sign protocol-defined proof messages

Network:
    locate or connect to an address
    define the mutual proof transcript
    authenticate the remote identity
    protect connection frames

Discovery and Board:
    associate mutable addresses and advertised services with an identity

Ledger and trust:
    associate credits, history, relationships, and policy with an identity
```

An address, socket, process, machine, connection-local handle, account name, or
service name must not be used as a substitute for the binary CR2SE ID.

---

## 15. Minimum conformance cases

An implementation should test at least these cases against identity generation,
derivation, parsing, formatting, proof verification, and key loading:

```text
Ed25519 generation using a CSPRNG and canonical 32-byte public keys;
ID derivation over exactly 0x01 || 0x01 || publicKey;
rejection of public keys and claimed IDs shorter or longer than 32 bytes;
rejection of unsupported identity versions and key algorithms;
claimed-ID match and mismatch for the same public key;
valid and invalid Ed25519 proof signatures;
a correct signature checked against the wrong ID, key, message, and protocol role;
canonical text with exact lowercase cr2se: prefix and 52 uppercase symbols;
uppercase and lowercase Base32 input producing the same 32-byte ID;
rejection of a missing or altered prefix;
rejection of Base32 padding, whitespace, punctuation, Unicode lookalikes,
    wrong encoded lengths, and nonzero unused final bits;
format(parse(text)) producing canonical uppercase output;
binary identity comparison across differently cased textual inputs;
identity QR round trips without adding address semantics;
contact bootstrap authentication as the expected ID;
contact bootstrap rejection when the endpoint authenticates as another ID;
loading a copied key pair in another implementation and deriving the same ID;
rejection of mismatched cached public-key or ID storage fields;
node startup with zero, one, and more than one configured identities;
and generation of a new key pair producing a new identity without inherited state.
```

The fixed public keys and expected binary IDs in
[`NetworkTestVectors.md`](./NetworkTestVectors.md) also test identity derivation.
Their canonical textual forms are:

```text
initiator:
cr2se:3FEKTKCHTGJQLPTATWZZ3HFFBN6JGGCOYNV56CAPN5DECXQZSJOQ

acceptor:
cr2se:O5CQJ3PUPOXCRJHRCVF7IULK45HQSDXFWAZEMRMG2DBB2JGZWJEQ
```
