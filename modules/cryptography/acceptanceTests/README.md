# Cryptography acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness and common cases](../../../AcceptanceTests.md). Required
suite; no other running module is needed. `V` is the existing
[fixed envelope vector](../pseudocode/README.md#19-fixed-identity-encryption-test-vector).
Compare stored vector bytes, not values produced by the encoder under test.

```text
TEST CR-01 known hashes and chunk independence
  ACT SHA256(empty); ASSERT hex(result)="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  FOR EACH partition of ASCII("abc") including single-byte delivery:
    ACT hash ordered chunks
    ASSERT hex(result)="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

TEST CR-02 exact ordinary Ed25519
  ACT sign fixed Transport AUTH vector bytes with its fixed seed
  ASSERT signature equals pinned AUTH signature; verification=true
  FOR EACH [message bit flip, signature bit flip, wrong public key, wrong domain]:
    ACT verify(mutated fixture); ASSERT false
  ASSERT Ed25519ph or native object serialization is not used

TEST CR-03 persistent key binding
  ACT bind/verify independently generated persistent X25519 public key
  ASSERT signed bytes = ASCII("CR2SE-ENCRYPTION-KEY-V1") || publicKey
  ASSERT no zero terminator or length prefix added
  FOR EACH [claimed ID mismatch, key substitution, signature length 63/65]:
    ACT validateCredential; ASSERT REJECT before encrypting

TEST CR-04 full envelope vector
  ACT encrypt V.plaintext using V.recipient, fixed ephemeral key and nonce
  ASSERT kdfContext, salt, PRK, key, header, sealed bytes and full object = V.expected
  ACT decrypt V.object with V.recipient key
  ASSERT plaintext = V.plaintext; no extra external associated-data parameter

TEST CR-05 self and recipient encryption
  FOR EACH recipient IN [self, another identity]:
    ACT encrypt then decrypt empty plaintext and UTF8("hello €")
    ASSERT returned plaintext equals exact original bytes
    ASSERT header length=132; sealed length=plaintext length+16
    ASSERT entire object length=148+plaintext length
    ASSERT header recipient ID/key match intended recipient

TEST CR-06 authenticated header and ciphertext
  FOR EACH byte position IN valid header, ciphertext and tag:
    ACT decrypt object with one bit flipped at position
    ASSERT REJECT; ASSERT released plaintext byte count=0
  ACT decrypt valid object using wrong identity or persistent key
  ASSERT REJECT; ASSERT released plaintext byte count=0

TEST CR-07 format and length boundaries
  FOR EACH [unsupported format/agreement/KDF/AEAD selector, truncated header,
            sealedLength<16, sealedLength=U64_MAX exceeding input/budget,
            fewer sealed bytes, one trailing byte]:
    ACT decrypt malformed object
    ASSERT REJECT before excessive allocation; ASSERT no plaintext
  ACT stream ciphertext without final tag
  ASSERT no provisional plaintext is released

TEST CR-08 key agreement failures
  FOR EACH [invalid peer X25519 key, primitive returns 32 zero bytes, primitive error]:
    ACT derive envelope or Transport secret
    ASSERT REJECT; ASSERT raw shared result never used directly as encryption key

TEST CR-09 fresh object material and cleanup
  supply two distinct fixture ephemeral pairs/nonces
  ACT encrypt identical plaintext twice for same recipient
  ASSERT each call consumes fresh material; headers and ciphertexts differ
  ASSERT both decrypt correctly; no nonce/key pair reused
  ACT success, failure and cancellation with instrumented protected-secret port
  ASSERT transient key material is released/erased when no longer needed
  ASSERT diagnostics/public results contain none of the fixture secrets
  FOR EACH fault IN [second persistent pair generation, public-key encoding,
                     identity derivation, binding signing, atomic key storage,
                     ephemeral public-key encoding, nonce randomness after ephemeral generation,
                     X25519 error or wrong-length result, HKDF extraction,
                     HKDF expansion after PRK acquisition, wrong-length expanded key,
                     header construction, AEAD encryption/decryption]:
    ACT inject failure, then cancellation, at that boundary with acquired secrets recorded
    ASSERT every acquired staging secret erased; no unowned returned secret
    ASSERT primitive-internal partial secrets erased even if no value was returned
    ASSERT no partial persistent identity committed on generation/storage failure
  ACT successful key generation and successful derivation
  ASSERT staging erased; committed handles remain usable
  ASSERT returned shared/derived secrets owned by caller until erased on its exit

TEST CR-10 construction separation
  ACT parse Messaging-specific envelope as generic 132-byte-header object
  ASSERT it is not accepted as the generic format
  ACT encrypt generic object, store opaque bytes, retrieve and decrypt
  ASSERT sender authenticity is not inferred merely from valid decryption
  ASSERT Transport frame integrity alone is not reported as payload confidentiality

TEST CR-11 independent protected units
  ACT decrypt two valid individually authenticated chunks in changed order
  ASSERT primitive authentication alone does not claim original sequence integrity
  ACT validate an application manifest binding positions, lengths and hashes
  ASSERT reordered/missing chunk fails that manifest's verification
  ASSERT no new CR2SE chunk wire format is inferred from this application test
```
