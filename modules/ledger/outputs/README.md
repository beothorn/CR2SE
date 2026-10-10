# Ledger outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Trust and accounting view | [Services](../../services/inputs/README.md), authorized administration or [Peer Control](../../peer-protocol/inputs/README.md): exact identified issuer/owner balances and available capacity. Remote balance control reveals only the issuer's recognized balance for its authenticated caller. |
| Reservation reference | Services: opaque operation-bound finite hold and amount/mode, or rejection with no hold. Same operation cannot reserve twice. |
| Prepared token and settlement status | Local coordinator: `absent`, `prepared`, `committed` or `aborted`, with operation and exact effect association. Successful local settlement applies at most once; unused metered capacity is released. |
| Transfer fee quote/result | Peer Control: fee and exact transfer identity fields; committed result contains owner, new owner, transfer ID, gross amount, fee and net received amount. Only original/new owner may retrieve it. |
| Claim / redemption result | Authorized administrator gets secret bearer claim material; Peer Control gets claim ID and amount for the authenticated redeemer. Never expose the secret in Board, logs or discovery. |
| Settlement action request | Composition/Peer Control: issuer, signed order or authorized query, exact fee/bound and invocation correlation. It cannot authorize repeating service work. |
| Payment state | Services/client: settled, unsettled or unknown as applicable, distinct from service completion. A remote issuer refusal cannot be presented as confirmed payment. |

Ledger changes are durable before reporting commitment. Provider-issued
spending, requester-issued credits and same-identity resource budgets preserve
their distinct meanings. Transfers and consumed claims retain replay records for
the required lifetime; a duplicate exact request returns its original result.
Ledger does not publish trust records, change offerings or cancel leases by
editing another module's data.

## Independent acceptance examples

- Race two reservations each individually affordable but collectively too large:
  at most the available capacity is reserved, without negative balances.
- Lose a commit response and query/retry the same local key after restart:
  exactly one debit or issuance remains; conflicting key reuse fails.
- Repeat a signed transfer or claim redemption through a fake authenticated
  adapter: same authorized retry returns the original result, with no second
  credit effect. An unrelated caller cannot retrieve the protected result.
