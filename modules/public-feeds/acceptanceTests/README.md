# Public Feeds acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
suite; wire name remains `cr2se.open-social-messaging`. Publisher B, readPrice3,
maximumResults10, otherwise complete valid limits. Seed independently signed
messages m1=(time100,id1), m2=(time100,id2), m3=(time101,id3), with id1<id2.
Unless testing byte caps, every fixture message fits the response bound.

```text
TEST PF-01 canonical bytes, identity and signature
  ACT encode/hash/sign corrected canonical vector in specification
  ASSERT exact canonical bytes, messageHash and signature equal pinned vector
  ASSERT publisherId=oracleSHA256(hex("0101") || publisherPublicKey)
  ASSERT signing input=ASCII("CR2SE-OPEN-SOCIAL-SIGNATURE-V1") || messageHash
  ACT legacy fixture using SHA256(publicKey) alone, even with valid signature for those bytes
  ASSERT reader rejects mismatched CR2SE identity; legacy vector is not a valid publisher

TEST PF-02 signed attachments and optional strings
  ACT encode message with two attachments and multibyte UTF8 body
  ASSERT length prefixes count UTF8 bytes; attachment order part of signed bytes
  ASSERT dataSize/hash equals exact embedded bytes
  ACT omit fileName versus present empty fileName in independent fixtures
  ASSERT canonical bytes/hashes differ via optional-string presence tag
  ACT reorder attachments or alter altText after signing
  ASSERT signature/hash validation fails

TEST PF-03 publication validation
  ACT publish valid message through locally authorized application
  ASSERT random messageId32, B publisher ID, complete signed message durable before success
  FOR EACH [empty body with no attachment, invalid UTF8, duplicate ID with changed bytes,
            excessive body/attachment/count/message size, wrong data length/hash,
            media type uppercase/parameters/whitespace, fileName containing slash/backslash/NUL,
            signing or persistence failure]:
    ACT publication; ASSERT no partially visible new message
  ACT empty body with valid attachment; ASSERT allowed

TEST PF-04 author provenance
  FOR EACH [public key derives another ID, publisher differs from authenticated feed,
            signature mutation, false supplied messageHash]:
    ACT validate returned complete message
    ASSERT reject as authentic content before display/index/cache
  ACT valid signed imported message for B
  ASSERT same validation as reader before local publication

TEST PF-05 newest-first latest read
  ACT read(latest,limit2)
  ASSERT messages=[m3,m2]; selector="latest"; more=true; price3
  ACT cursor=(100,id2),limit2
  ASSERT messages=[m1]; more=false
  ASSERT ordering is time descending then unsigned messageId descending

TEST PF-06 since and interval boundaries
  ACT read(since,fromInclusive101)
  ASSERT [m3],price3
  ACT read(interval,fromInclusive100,toExclusive101)
  ASSERT [m2,m1],price3; m3 excluded at upper bound
  ACT adjacent interval[101,102)
  ASSERT [m3]; no boundary message duplicated between intervals

TEST PF-07 selectors, cursors and limits
  FOR EACH [unknown selector, latest with either time bound, since missing from/with to,
            interval missing bound or from>=to, partial cursor pair, limit0 or11,
            malformed32-byte cursor ID]:
    ACT read; ASSERT rejected without charge
  ACT latest/interval with valid exclusive cursor
  ASSERT selector applied before cursor; response remains within both constraints

TEST PF-08 byte-bounded consecutive selection
  fixture newest eligible message canonical length200, next150, next50
  fixture maximumMessageBytes200, maximumResponseBytes300
  ACT read(limit10)
  ASSERT returns first200-byte message only,more=true
  ASSERT does not skip150-byte next message to include older50-byte one
  ACT offering maximumMessageBytes>maximumResponseBytes
  ASSERT invalid offering
  ASSERT response accounting uses canonical message bytes, not JSON/frame overhead

TEST PF-09 empty page, retries and concurrent changes
  ACT read with no matches
  ASSERT messages=[],more=false,price3; successful charged result
  ACT new explicit read after local publication changes
  ASSERT separately charged current page, not a frozen snapshot or free retry
  publish newer entry between cursor pages
  ASSERT exclusive older-page cursor does not repeat newer entry

TEST PF-10 immutability and availability scope
  ACT change bytes under available messageId
  ASSERT refused; correction needs new message ID
  ACT publisher stops serving old message through local policy
  ASSERT no implied retention promise or deletion tombstone
  ASSERT cached verified content retains its original signature/hash

TEST PF-11 complete output and independent verification
  ACT read then truncate an attachment/body before result completion
  ASSERT no complete successful result/charge for uncommitted failure
  FOR EACH [good complete page, bad complete page, missing evidence]:
    ACT local check with original publisher/request/terms
    ASSERT outcomes pass,fail,inconclusive respectively
  ASSERT check verifies counts/byte limits/cursor/signatures/hashes, not provider's assertion
  ASSERT no remote check charge or automatic trust update/refund

TEST PF-12 merged feed and content authority
  ACT combine independently verified responses from two publishers, including repeated messages
  ASSERT retain publisher provenance; deduplicate by publisher/message identity
  ASSERT same opaque messageId from different publishers not collapsed as same message
  ACT body contains markup/instructions/links and attachment misleading extension
  ASSERT body treated as text; no automatic execution, unsafe path use or extra paid fetch

TEST PF-13 restart and family independence
  ACT publish; restart feed provider
  ASSERT acknowledged durable publication intact with same immutable bytes
  RUN applicable Services SV-09 completion/accounting cuts
  ASSERT feed publication/read works without Messaging, Files, Pages, Discovery or paid Storage calls
```
