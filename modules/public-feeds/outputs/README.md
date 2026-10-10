# Public Feeds outputs

[Specification](../README.md) · [Inputs](../inputs/README.md) ·
[Common service boundary](../../../ModuleContracts.md#common-service-handler-boundary)

## Results and consumers

| Output | Consumer / guarantee |
|---|---|
| Local publication result | Authorized publisher application: immutable complete signed message and ID/hash association, durable before success. Failed publication exposes no partial message. |
| Read result | [Services](../../services/inputs/README.md), then requester: `operation:"read"`, original `selector`, complete `messages`, `more:bool`, `price:uint64`. Messages include canonical fields/attachments, signature and calculated 32-byte `messageHash`. |
| Local check | Requester: pass/fail/inconclusive from original request/terms and complete returned messages, not a provider assertion. |
| Combined feed | Requester application: locally merged verified messages with publisher provenance and deduplication; not a new network service result. |

Select matching messages in the specified newest-first order and apply the
exclusive cursor. Take consecutive entries until count or response-byte bound;
never skip a large matching entry to fit smaller later ones. Empty output is a
charged success with `more:false`; otherwise `more` describes the immediate
selection state. Output is not a permanent frozen feed snapshot.

Services settles only a complete valid invocation result at the accepted price.
Any retained result/effect reference obeys local coordination rules; repeating a
peer read is a new paid invocation. A valid signature proves publisher key
control and exact signed content, not truth, safety or feed completeness.
Missing check data or local limits yield inconclusive. Checks do not change
Ledger trust or refund credits automatically.

## Independent acceptance examples

- Reproduce canonical message bytes/signature and publish with a fake signer
  and durable feed port; a failed commit exposes no partial message.
- Read latest/since/interval with exact cursor pairs and byte limits; ensure no
  eligible large entry is skipped and empty results have `more:false`.
- Tamper with attachment bytes or publisher signature: requester verification
  fails before displaying/caching content as authentic, with no Messaging runtime.
