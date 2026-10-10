# Ledger inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Required in the minimum node. Ledger owns trust, issuer-separated balances,
reservations and replay records. It needs Identity/Cryptography capabilities
and durable platform transactions, not a service-family database, a paid
Storage lease or a live Peer Control process.

## Accepted calls

| Input / source | Values and expectations |
|---|---|
| Local account authority / [Identity](../../identity/outputs/README.md) and administration | Local identity, protected signer/decryptor, finite issuance budgets and authorized trust/grant policy. Unknown trust starts at zero; no implicit grants. |
| Trust/balance query / Services or authorized local caller | Exact peer and issuer/owner identities. Specify owned-by-issuer versus issued-to-owner view; never sum currencies. |
| Reserve / [Services](../../services/outputs/README.md) | Durable operation key, requester/provider/issuer IDs, settlement mode, accepted price or maximum, exact transfer fee if applicable, terms reference and local authority. Validate trust/policy and finite capacity under serialization. |
| Prepare settlement / Services | Same operation key and reservation, complete validated result reference, final price within the bound, and any contract-authorized adjustment. Messaging release credits are separately recorded, not an arbitrary refund command. |
| Commit/abort/status / authorized local coordinator | Operation key, exact prepared effect token and durable decision under the common recovery protocol. Repeated calls are idempotent; conflicting terms fail. |
| Transfer controls / [Peer Control](../../peer-protocol/outputs/README.md) | Authenticated owner, canonical 121-byte order, 32-byte owner key, 64-byte signature, maximum fee and later exact fee acceptance. Query supplies owner ID and 16-byte transfer ID with authorized caller context. |
| Claim redemption / Peer Control | Authenticated redeemer and generic encrypted envelope. Verify embedded issuer/owner, claim commitment, restrictions and stored authoritative amount. |
| Create/invalidate claim, grant/revoke credits, set trust / local administrator | Explicit target, finite amount/authority and policy; these are never unsolicited peer operations. Preserve in-flight reservations and accepted obligations. |
| Third-party settlement evidence / authenticated exchange adapter | Original issuer connection context and complete transfer result matching the bound invocation, order, fee and net price. Forwarded requester JSON is insufficient. |

Identity supplies key authority; Cryptography supplies canonical signature/hash
and envelope operations. A third-party query is requested through composition
and Peer Control, not by reading another ledger. The Ledger core can be tested
with supplied authenticated receipts or refusals.

All amounts are exact uint64; trust is a bounded local value in `[0,1]` with an
implementation-defined exact representation. Reject overflow/underflow. Use
durable replay guards for transfers and claims, and preserve local operation
bindings across restart. A timeout cannot release a committed reservation.
