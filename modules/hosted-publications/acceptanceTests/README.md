# Hosted Publications acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md) · [Vectors](../vectors/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
suite. P is the publisher, R and S readers, H and H2 hosts; H explicitly
trusts and funds all callers. Pricing: minimum 1, B=1/2, X=1/2, R=1/2, N=1/2,
list 1, remove 2, check 3; release quote 5 where allowed. Time 1000, retention
10, total retention 200, maximumListResults 2. All charges use H credits. Use the
fixed [vectors](../vectors/README.md) from an independent encoder.

```text
TEST HP-01 signing canonicalization and vectors
  ACT construct signing bytes for each vector publication V1, V2, V3
  ASSERT bytes equal the vector signing bytes; signature equals the vector signature
  FOR EACH metadata field, the audience, or one content byte: mutate keeping the signature
    ACT store; ASSERT rejected without charge

TEST HP-02 durable placement and exact bytes
  ACT store V1 and V2 at H
  ASSERT placementId length32; acceptedAt1000; expiresAt1010; price per formula
  ACT restart H; ACT R get each publication
  ASSERT returned bytes, signature and key identical to the stored ones; R verifies without trusting H

TEST HP-03 store rejections
  FOR EACH [publisherId differs from derived ID or authenticated caller, invalid signature,
            kind unknown, resource with sequence1, content0, wrong size/hash,
            public with non-empty audience, restricted with empty/unsorted/duplicate audience,
            restricted envelope count differs, retention outside limits, price disagreement,
            duplicate (publisherId, publicationId), same-kind same-sequence different publicationId]:
    ACT store; ASSERT no placement and no charge

TEST HP-04 visibility
  ACT P stores public V2 and restricted V3 (audience R)
  ACT R lists and gets V3; ASSERT success and R decrypts the feed message exactly
  ACT S lists feed-post; ASSERT empty page, more=false, same shape as an empty publisher
  ACT S gets V3 and an unknown ID; ASSERT indistinguishable failure without charge
  ACT P lists and gets V3; ASSERT permitted

TEST HP-05 list order and cursor
  seed feed-post sequences [(9,idB),(7,idA),(5,idC)]
  ACT store feed-post (7,idD); ASSERT conflict failure without charge
  ACT list(limit2); ASSERT [(9,idB),(7,idA)]; more=true; price1
  ACT list(before 7/idA, limit2); ASSERT [(5,idC)]; more=false
  FOR EACH [one cursor field, limit0, limit above maximum, kind resource]:
    ACT list; ASSERT failure without charge

TEST HP-06 get bounds and prices
  ACT get with maximumBytes below contentSize; ASSERT failure without charge
  ACT get within bound; ASSERT price = max(1, ceil(S*1/2)); repeat get charges again

TEST HP-07 envelope vector and decryption
  ACT build V3 envelope from the vector inputs; ASSERT every byte equals the vector
  ACT reader with the matching key opens it; ASSERT plaintext equals the feed message bytes
  FOR EACH [wrong reader key, damaged wrapped key, damaged ciphertext, altered metadata,
            invalid X25519 result, wrong version byte, entry count mismatch]:
    ACT open; ASSERT failure and no plaintext

TEST HP-08 hosted page assembly
  ACT P stores resource V1 and manifest V2; ACT reader readPage
  ASSERT manifest verifies; root "/" text/html; resource matches size/hash/ID
  FOR EACH [resource wrong publisher, wrong kind, different visibility, size or hash mismatch,
            unsorted/duplicate path, missing root, root not text/html, trailing bytes]:
    ACT readPage; ASSERT that resource or manifest is rejected and the page is not accepted

TEST HP-09 hosted feed post
  ACT P stores a feed post whose content is the canonical message bytes
  ASSERT reader accepts only when messageId==publicationId, publisherId and publishedAt match
  ACT use a mismatching field; ASSERT post invalid

TEST HP-10 versions and equivocation
  ACT P stores page sequence1 at H and sequence2 at H2; ACT reader readPage across both
  ASSERT sequence2 chosen
  ACT store a second page with sequence2 and another publicationId at H2; ASSERT conflict rejected at H2
  ACT inject two verified publications with one sequence in a reader's view from H and H2
  ASSERT reader reports equivocation and keeps the latest unconflicted sequence
  ACT H omits sequence2; ASSERT reader reports best-known, not proven-latest

TEST HP-11 renew
  ACT renew with the current expiration; ASSERT expiresAt extended; charged per formula
  FOR EACH [stale expectedExpiresAt, duration outside limits, total above maximum, non-publisher, inactive]:
    ACT renew; ASSERT failure without charge

TEST HP-12 remove and release credits
  ACT remove with minimumReleaseCredits5 and quoted release5
  ASSERT placement removed; removePrice2 charged; release5 applied; one replay record
  ACT retry same removalId; ASSERT identical output and no second charge or release
  ACT another removalId; ASSERT failure without charge; ACT get; ASSERT not found

TEST HP-13 check
  ACT publisher checks one offset; ASSERT pass/fail/inconclusive per Messaging rules; charged checkPrice
  ACT non-publisher checks; ASSERT denied without metadata

TEST HP-14 authorization
  FOR EACH operation IN [renew, remove, check] ACT as R on P's placement; ASSERT denied
  ASSERT unknown placement and another publisher's placement are indistinguishable

TEST HP-15 definitions and independence
  ACT service.get; ASSERT offering/definition fields, preconditions and issuer
  ACT replicate at H and H2; ASSERT separate placement IDs; losing H does not affect reading from H2
  ASSERT hosting does not enable cr2se.page or cr2se.open-social-messaging under the host identity
```
