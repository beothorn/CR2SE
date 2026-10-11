# Messaging acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
suite. A is sender, C recipient, B provider; B explicitly trusts/funds both
callers. Payload `abc`, encoding `opaque`, retention10, time1000. Use valid
signed metadata from an independent fixture encoder. Pricing factors B/X/R/N
are1/2, minimum1, discover/status1, remove2, check3; release quote is5 where
allowed. Limits permit payload, retention and extensions; total retention200.
All charges use B credits. Local persistence is not a paid Storage invocation.

```text
TEST MS-01 signature canonicalization
  ACT construct message signing bytes
  ASSERT bytes = ASCII("CR2SE-MESSAGE-V1") || messageId || A.id || C.id
    || u64be(senderCreatedAt) || hex("00") || u64be(3) || oracleSHA256(abc) || abc
  ASSERT signature is ordinary Ed25519 over exact bytes, length64
  FOR EACH metadata field or payload byte: mutate while retaining original signature
    ACT store; ASSERT rejected without charge

TEST MS-02 durable placement
  ACT store complete signed fixture
  ASSERT placementId length32; messageId unchanged; acceptedAt1000; expiresAt1010; price17
  ASSERT payload and receipt metadata durable before success
  ACT restart; recipient discovers placement; sender queries status
  ASSERT pending placement remains; one store charge17
  ACT independently accept same message a second time
  ASSERT separate placement ID; no silent replacement or inferred retry deduplication

TEST MS-03 input and issuer rejection
  FOR EACH [sender key/ID mismatch, sender differs from authenticated caller,
            invalid signature, payload0, wrong size/hash, unsupported encoding,
            forbidden operation fields, invalid retention, time addition overflow,
            unpersisted/incomplete body, issuer other than B]:
    ACT affected store/invocation; ASSERT no successful placement or charge
  ACT price calculation size1,time1 at half factors
  ASSERT storePrice1, not2; zero denominators/overflowing advertised maxima rejected

TEST MS-04 role authorization and privacy
  FOR EACH operation IN [status,renew,remove,check]:
    ACT as C or U on A's placement; ASSERT denied without protected metadata
  ACT recover as A or U; ASSERT denied
  ACT discover as C; ASSERT only C's pending messages returned
  ASSERT unknown placement and another caller's placement are indistinguishable across denied boundary

TEST MS-05 discovery order and cursor
  seed C's pending placements [(1000,id1),(1000,id2),(1001,id3)] with id1<id2
  ACT discover(limit2); ASSERT returned[(1000,id1),(1000,id2)]; more=true; price1
  ACT discover(after1000/id2,limit2); ASSERT returned[(1001,id3)]; more=false
  ACT no matching pending placements; ASSERT empty page, more=false and charge1
  FOR EACH [only one cursor field, limit0, limit above maximum]:
    ACT discover; ASSERT failure without charge
  ASSERT discovery's sender ID is not trusted as cryptographic sender until recovery verification

TEST MS-06 recovery request binding
  requestBytes = ASCII("CR2SE-MESSAGE-RECOVERY-REQUEST-V1") || B.id
    || placementId || messageId || payloadHash || recoveryId
  ACT C signs and requests recover
  ASSERT recipient key derives C; exact request signature verified
  FOR EACH [wrong provider/message/hash/recoveryId, wrong recipient key, bad signature]:
    ACT mutated request; ASSERT no transition or charge

TEST MS-07 recovery output and receipt
  ACT valid recovery while pending
  ASSERT complete original signed metadata and abc payload returned
  ASSERT recoveryId matches; recoveredAt=current controlled time
  receiptBytes = ASCII("CR2SE-MESSAGE-RECOVERY-RECEIPT-V1") || B.id || placementId
    || messageId || A.id || C.id || payloadHash || recoveryId || u64be(recoveredAt)
  ASSERT providerSignature verifies receiptBytes with B key
  ASSERT recipientSignature is original request signature
  ASSERT state=recovered; pending discovery excludes placement; envelope finalPrice2
  ASSERT recovery logical output has no invented price field

TEST MS-08 recovery retry and conflict
  ACT recover; lose response; restart; change current price/balance
  ACT same authenticated C retries identical request and recoveryId before expiry
  ASSERT byte-identical complete cached output and original price; no new quote/charge
  ACT different recoveryId or changed original field
  ASSERT failure; cannot recover a second time
  ACT sender renews recovered placement then original recipient retries before new expiry
  ASSERT cached full payload/receipt remains until extended expiresAt

TEST MS-09 sender status
  ACT status pending; ASSERT state=pending with exact IDs/hash/expiry and price1
  ACT recover then status; ASSERT state=recovered with original recovery/recipient/provider signatures
  ASSERT both signatures independently verify; no payload returned by status
  ASSERT status asserts identity-authorized recovery, not human reading

TEST MS-10 renewal
  FOR EACH state IN [pending,recovered]:
    ACT renew(expected1010,additional4) by A
    ASSERT previousExpiresAt1010; expiresAt1014; price6; state unchanged
    ACT retry expected1010; ASSERT no second extension/charge
  race two renewals from expected1010
  ASSERT one may succeed; definite serialized expiry
  FOR EACH [wrong owner, expired, excessive duration/total, overflowing expiry]:
    ACT renew; ASSERT prior valid commitment unchanged; no charge

TEST MS-11 release-credit quote and atomic removal
  fixture cumulative store+renew payments=17 and active pending placement
  ACT remove(minimumReleaseCredits4,expected1010,removalId), quote release5 and removePrice2
  ASSERT exact release amount accepted before deletion
  ACT commit; ASSERT removed=true; releaseCredits5; price2
  ASSERT separate debit2 and issuance5, net owner balance increase3, once
  ASSERT no later pending discovery/recovery; no physical-erasure claim

TEST MS-12 removal refusal and replay
  FOR EACH [release below minimum, release above cumulative store/renew payments,
            stale expiry, recovered placement, insufficient remove debit capacity,
            overflowing release balance]:
    ACT remove; ASSERT no deletion/charge/credit adjustment
  ASSERT discover/recover/status/check/remove prices do not enlarge release ceiling
  ACT successful removal; lose reply; restart; exact same sender/request/removalId
  ASSERT identical original output, no second debit or release issuance
  ACT another removalId for inactive placement; ASSERT failure
  ASSERT removal replay guard survives for lifetime of ledger, beyond lease expiry

TEST MS-13 paid byte evidence
  ACT sender checks offset1 while pending, accepted price3
  ASSERT evidence value=ASCII("b"), matching placement/offset; expected byte never sent
  ACT timely correct/wrong evidence in separate cases
  ASSERT local outcomes pass/fail respectively; each complete valid evidence charged3
  ACT no valid evidence or late response; ASSERT inconclusive under timing rules
  ASSERT timeout without complete evidence is not charged
  FOR EACH [offset>=size, recovered/removed/expired placement, wrong caller]:
    ACT check; ASSERT rejected without charge

TEST MS-14 encrypted representation
  ACT validate recipient Board credential; encode encrypted message with fixed test entropy
  ASSERT prefix1, recipient key32, ephemeral key32, nonce24 and sealed bytes>=16
  ASSERT payload length=105+plaintext length; hash/signature cover stored ciphertext
  ASSERT KDF salt hashes exact metadata domain/message/sender/recipient/time
  ACT recipient decrypts after verifying sender and payload
  ASSERT plaintext exact; provider never receives decryption key
  FOR EACH [wrong key, mutated bound metadata, tag tamper, version change, truncation]:
    ACT recipient decrypt; ASSERT no accepted plaintext
  ASSERT generic132-byte-header envelope is not substituted for this format

TEST MS-15 optional recipient credential
  ACT valid canonical Base32 credential from expected publisher
  ASSERT usable only after ID derivation, binding and X25519 key validation
  FOR EACH [wrong publisher, bad binding, bad Base32 unused bits, missing field]:
    ACT lookup; ASSERT key unusable; unrelated offerings remain usable
  ACT opaque message without credential; ASSERT conforming signed placement still works

TEST MS-16 races, expiry and local recovery
  race valid recover with valid remove on pending placement
  ASSERT exactly one state transition succeeds; other fails without its charge
  ACT recovery accepted just before expiresAt; finish after expiration
  ASSERT complete original accepted recovery; new request at expiry fails
  ACT status racing transition; ASSERT reports one state that actually existed
  RUN Services SV-09 with placement/recovery/removal effects
  ASSERT no committed receipt without matching once-only accounting, or double release credits

TEST MS-17 replica identity and independent handler
  ACT same signed message placed at B and another provider
  ASSERT recipient deduplicates by(senderId,messageId), not placementId alone
  ACT same messageId from different valid sender
  ASSERT treated as a different message
  ASSERT handler calls local persistence, never requires paid Storage or Discovery runtime
```
