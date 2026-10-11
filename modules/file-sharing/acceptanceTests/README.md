# Public File Sharing acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
suite. Use canonical vector `V` from the specification and a second complete
share with file `a.bin` containing16,385 known bytes plus empty file `empty`.
Piece size16,384, minimumPrice1, manifestByteFactor1/100,
downloadByteFactor1/16384, catalogPrice3; remaining limits fit valid fixtures.
Hashes/signatures are independently pinned or calculated with test-owned oracles.

```text
TEST FS-01 canonical minimum manifest
  ACT encode one empty file at path["a"], pieceSize16384
  ASSERT bytes equal specification's70-byte vector
  ASSERT shareId=hex("8faf21bb74074d60be59a2b014739ba4fc9bc194bdc40396cf4bdc3c35a1fbd1")
  ACT decode pinned bytes; ASSERT path["a"], size0, pieceCount0, empty SHA256 file hash

TEST FS-02 piece and file construction
  ACT build second fixture manifest
  ASSERT a.bin pieceCount2; piece lengths[16384,1]; empty file pieceCount0
  ASSERT piece/file hashes equal independent hashes of exact source ranges/whole file
  ASSERT records sorted by unsigned UTF8 path components, not input traversal order
  FOR EACH pieceSize IN [16384,4194304]: ASSERT permitted with otherwise valid fixture
  FOR EACH pieceSize IN [0,16383,16385,4194305]: ACT build; ASSERT REJECT

TEST FS-03 path and manifest rejection
  FOR EACH [no files, duplicate path, file path prefix of another, unsorted records,
            empty/dot/dot-dot component, separator/control character, component256 bytes,
            invalid UTF8, invalid count/length, wrong piece count, trailing manifest bytes,
            size requiring more than U32_MAX pieces]:
    ACT parse/build mutated fixture; ASSERT REJECT
  ASSERT parser does not reorder received bytes before validating share identity
  ACT source traversal encounters symlink
  ASSERT not followed into share; no unsupported symlink record invented

TEST FS-04 host import and availability
  ACT local import manifest with complete matching files
  ASSERT share advertised only after complete validation/availability
  ACT import missing/corrupt piece or hash mismatch
  ASSERT cannot advertise as a complete hosted share
  ACT invoke manifest on non-hosted share
  ASSERT pre-acceptance unavailable failure with no charge

TEST FS-05 manifest operation and quote
  ACT manifest(V.shareId,maximumManifestBytes70)
  ASSERT quote.manifestBytes=70; price1; exact70-byte output and shareId
  ASSERT requester verifies length/hash before deep canonical parse
  FOR EACH [maximumManifestBytes69, above offering limit, quoted length mismatch,
            response wrong shareId/hash, over-bound response]:
    ACT affected request/result; ASSERT no accepted valid complete result
  ACT quote independently fixed manifest length101
  ASSERT price2 under rate1/100, irrespective of frame/compression overhead

TEST FS-06 consecutive piece download
  ACT download(a.bin,fileIndex0,firstPiece0,pieceCount2)
  ASSERT quote.downloadBytes=16385; price2; output data equals complete source
  ASSERT exact range metadata; no separators between pieces
  ACT final piece only(firstPiece1,count1)
  ASSERT one byte matching source last byte; price1
  ASSERT verified empty file requires no download invocation

TEST FS-07 range rejection
  FOR EACH [fileIndex=fileCount, firstPiece=pieceCount, requested count0,
            requested count>remaining, U32_MAX range overflow, data length above current limit,
            any piece request for empty file]:
    ACT download; ASSERT rejected without charge or arithmetic wrap
  ASSERT requester needs verified matching manifest before treating ranges as meaningful

TEST FS-08 piece and whole-file integrity
  ACT receive complete correctly hashed pieces
  ASSERT each piece marked verified only after its own hash matches
  ACT assemble all verified pieces in order
  ASSERT file complete only after complete file hash matches
  FOR EACH [corrupt byte, swapped pieces, wrong metadata/length, wrong final file hash]:
    ACT verify; ASSERT fail and no false completed file

TEST FS-09 interrupted resumption and multiple hosts
  ACT incomplete download containing one independently verifiable complete piece
  ASSERT operation not successful; no successful-result charge
  ASSERT only hash-verified complete piece may be retained as valid progress
  ACT explicitly authorized new range at another host of same share
  ASSERT new quote/charge; assemble with retained verified piece
  ASSERT original complete file hash matches; different manifest cannot be mixed

TEST FS-10 signed catalog and cursor
  fixture advertised shares s1<s2<s3 with current positive records signed by B
  ACT catalog(limit2); ASSERT records for[s1,s2],more=true,price3
  ACT afterShareId=s2; ASSERT[s3],more=false
  ACT no matches; ASSERT empty page charged3
  ASSERT each hostId=B; available=true; catalogAt and lifetime/skew constraints satisfied
  ASSERT catalog uses Discovery record format without calling its runtime

TEST FS-11 catalog validation
  FOR EACH [record signed by another host, negative availability, expired record,
            invalid signature, duplicate/out-of-order share IDs, violated cursor/limit]:
    ACT local catalog check on complete result
    ASSERT fail
  ACT withdraw hosted share
  ASSERT no new positive catalog entry claims it remains fully hosted
  ASSERT prior catalog page is not proof of continuing availability or a frozen snapshot

TEST FS-12 local check outcomes and prices
  FOR EACH operation IN [manifest,download,catalog]:
    ACT check original request/terms and correct complete output; ASSERT pass
    ACT complete output with one violated property; ASSERT fail
    ACT missing required input/output or insufficient local verification resources; ASSERT inconclusive
    ASSERT no remote check request, separate checkPrice or automatic refund
  ACT invalid zero denominator/minimum or overflowing advertised maximum
  ASSERT offering rejected before paid work

TEST FS-13 extraction safety
  FOR EACH local collision/escape fixture IN [case-folding, Unicode normalization,
    reserved device name, drive-relative interpretation, trailing-dot alias,
    pre-existing symlink, path replaced between check/write, mount-point escape]:
    ACT extract verified manifest into authorized destination
    ASSERT no write outside destination or silent overwrite through alias
    ASSERT either safe explicit mapping/content-store retention or refusal
    ASSERT transformed paths not falsely reported as original canonical paths
  ASSERT downloaded content never automatically executed

TEST FS-14 snapshots and module independence
  ACT read while administrator withdraws/replaces local hosting references
  ASSERT successful output still matches pinned immutable manifest/pieces
  RUN applicable Services SV-09 completion/accounting cuts
  ASSERT Files works without paid Storage, Discovery indexer, Feeds or Pages
  ASSERT offering hints never authorize unsolicited catalog enumeration or downloads
```
