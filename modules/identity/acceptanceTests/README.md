# Identity acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness and common cases](../../../AcceptanceTests.md). Required
suite; inject a protected key store, randomness and Cryptography port. `V` is
the fixed initiator in [Transport vectors](../../transport/pseudocode/TestVectors.md).

```text
TEST ID-01 canonical derivation
  ACT deriveId(version=1, algorithm=1, publicKey=V.ed25519PublicKey)
  ASSERT result = hex("d948a9a847999305be609db39d9ca50b7c93184ec36bdf080f6f46415e19925d")
  ASSERT hash input observed at crypto port = hex("0101") || V.ed25519PublicKey
  FOR EACH unsupported version/algorithm, key length IN [0,31,33]:
    ACT deriveId(mutated input); ASSERT REJECT

TEST ID-02 canonical text and identity equality
  text = "cr2se:3FEKTKCHTGJQLPTATWZZ3HFFBN6JGGCOYNV56CAPN5DECXQZSJOQ"
  ACT parse(text), parse(lowercase Base32 portion), format(V.id)
  ASSERT both parsed values = V.id; formatted value = text
  ASSERT comparison uses binary IDs, independent of endpoint or display casing

TEST ID-03 reject ambiguous text
  FOR EACH input IN [missing prefix, uppercase prefix, 51 or 53 Base32 chars,
                    added padding, whitespace before/after/inside, digit 0,
                    final Q replaced with R in ID-02]:
    ACT parse(input); ASSERT REJECT
  ASSERT no trimming or acceptance of nonzero unused Base32 bits

TEST ID-04 independent keys and durable creation
  fixture random/key-generation port supplies distinct independent pairs
  ACT createIdentity with authorized local caller
  ASSERT signing algorithm=Ed25519; encryption algorithm=X25519
  ASSERT no Ed25519-to-X25519 conversion requested
  ASSERT binding verifies over ASCII("CR2SE-ENCRYPTION-KEY-V1") || encryptionPublicKey
  ACT restart and load
  ASSERT same ID, both key pairs and binding; no network registration occurred

TEST ID-05 creation/load failures
  FOR EACH [entropy failure, signing-key write failure, encryption-key write failure,
            binding failure, missing key, mismatched public/private pair]:
    ACT create/load affected fixture
    ASSERT no successful usable identity with incomplete credential
    ASSERT no silent replacement of existing keys or claimed existing ID

TEST ID-06 key relation versus possession
  ACT validateKeyForId(V.publicKey,V.id); ASSERT valid
  ACT validateKeyForId(other.publicKey,V.id); ASSERT invalid
  ASSERT validating key relation alone emits no authenticated-connection event
  ACT fresh proof with wrong transcript or another identity's signature
  ASSERT identity authentication is not established

TEST ID-07 contact QR forms
  FOR EACH [ID alone, ID + "?address=127.0.0.1&port=1",
            ID + "?port=65535&address=2001%3Adb8%3A%3A1"]:
    ACT parseContact(input)
    ASSERT result.id=V.id; optional endpoint equals exact supplied IP/port
  ASSERT encoded IPv6 colons use percent escapes; decoding occurs once
  ACT connect parsed contact to a peer proving another ID
  ASSERT connection rejected; contact did not grant identity authority

TEST ID-08 invalid contacts
  FOR EACH [port 0, port 65536, +1, 01, missing port, duplicate address,
            unknown parameter, fragment, DNS address, IPv6 brackets or zone,
            double-escaped colon that does not decode to an IP literal]:
    ACT parseContact(mutated valid contact); ASSERT REJECT

TEST ID-09 key capability authority
  ACT sign exact bytes through an authorized purpose-scoped handle
  ASSERT signature verifies for those bytes only
  ACT same signing/decrypt/backup action without granted capability
  ASSERT REJECT; ASSERT peer-visible output/logs contain no private key
  ASSERT creating identity grants no trust or credits in observed Ledger commands

TEST ID-10 recovery boundaries
  ACT restore signing and encryption pairs plus independent recovery catalog
  ASSERT ID and decrypt capability unchanged; known lease contacts available
  ACT load signing key only
  ASSERT existing encrypted object cannot be claimed decrypted without its encryption key
  ACT restore keys without catalog
  ASSERT no invented provider/lease enumeration or recovery success
  ACT replace signing key
  ASSERT new ID differs; no identity-preserving rotation is claimed
```
