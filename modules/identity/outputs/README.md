# Identity outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Result | Consumer / guarantee |
|---|---|
| Local public identity | [Transport](../../transport/inputs/README.md), [Ledger](../../ledger/inputs/README.md), publishing clients and codecs: ID, Ed25519 public key, persistent X25519 public key and binding signature. Exact public lengths and valid binding. |
| ID / normalized text / contact | Clients and Transport: exact binary ID, canonical text or validated endpoint paired with expected ID. Contact lookup does not prove reachability or key possession. |
| Purpose-scoped signer/decryptor capability | Authorized module adapter; opaque local authority, not a raw private key or serializable bearer credential for peers. |
| Signature / authenticated plaintext | Authorized requester; exact Cryptography guarantees and requested purpose. No plaintext before authentication. |
| Validation decision / structured failure | Caller; malformed ID, mismatched key, invalid binding, unavailable key store or denied authority. No fallback to another identity. |

Creation success means both persistent pairs and their association are durably
recoverable through the configured key store. It grants no trust or credits.
Transport supplies fresh proof of possession; Ledger alone owns trust decisions.
Recovery catalog data belongs to the application and is backed up separately.
Several processes may use protected key services, but sharing key authority does
not remove the need to coordinate Ledger, Board and service state.

## Independent acceptance examples

- Reproduce the known ID from the Transport vector; lowercase input normalizes
  to canonical text, while whitespace and nonzero padding bits fail.
- Load the same backed-up pairs after restart and obtain the same public
  credential. An unavailable or mismatched key produces failure, not a new ID.
- With Cryptography and key-store substitutes, confirm that contact parsing
  returns an expected ID and endpoint without opening a socket or changing trust.
