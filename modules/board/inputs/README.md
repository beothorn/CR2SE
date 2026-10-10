# Board inputs

[Specification](../README.md) · [Outputs](../outputs/README.md) ·
[Common boundary rules](../../../ModuleContracts.md)

Required in the minimum node. Board owns offering/definition publication and
attributed caches. It consumes the Services schema **format**, but does not
need a running Services, Ledger, Transport or service-family implementation to
validate and store a snapshot.

## Accepted calls

| Input / source | Values and expectations |
|---|---|
| Publish / authorized local configuration | Publisher ID, complete Board JSON and one matching definition per offering, plus usable capability information from composition. Validate the whole candidate before replacing the prior snapshot. |
| Definition and schema data / [Services](../../services/outputs/README.md) or local configuration | Exact `id`, `service`, `serviceVersion`, `description`, `input`, `output`, `check`. Match identity fields with offering; prices remain on Board. A format validator may be linked locally. |
| Read snapshot / Peer Control, Services or local client | Publisher identity and optional local snapshot reference. Reads return one immutable revision; `version:1` remains a schema version, not a revision counter. |
| Read definition / Peer Control or Services | Offering ID and snapshot reference where consistency is required. Missing offering returns failure; never synthesize a definition from another version. |
| Validate/cache remote publication / [Peer Control](../../peer-protocol/outputs/README.md) | Lossless Board/definition JSON, authenticated publisher provenance and receipt time. A forwarded document has no implied original authentication. |
| Select/invalidate / Services or local caller | Offering ID, expected service/version/description, supported semantics and cached snapshot reference. Selection is not quote acceptance. |

Enforce valid UTF-8, duplicate-member rejection, exact integer prices, unique
offering IDs across both lists, exactly one pricing representation and bounded
documents fitting Peer Protocol control responses. Unknown mandatory semantics
make that offering unusable; unrelated understood offerings can remain usable.

Private state uses a platform persistence port. Local snapshot references are
opaque and are not new peer JSON fields. A changed publication never mutates an
already accepted invocation's copied terms or cancels an existing obligation.
