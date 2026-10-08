# Cryptography diagrams

[Specification](../README.md) · [Architecture and dependencies](../../../Architecture.md)

```mermaid
sequenceDiagram
    participant Sender
    participant Store as Untrusted storage peer
    participant Recipient
    Recipient-->>Sender: Public signing key, encryption key, binding signature
    Sender->>Sender: Verify recipient identity and key binding
    Sender->>Sender: Generate ephemeral key and nonce, derive key, encrypt
    Sender->>Store: Opaque encrypted object
    Store-->>Recipient: Same encrypted bytes
    Recipient->>Recipient: Validate header and intended recipient
    Recipient->>Recipient: Derive key and authenticate ciphertext
    alt Authentication succeeds
        Recipient->>Recipient: Release plaintext
    else Authentication fails
        Recipient->>Recipient: Reject entire object
    end
```
