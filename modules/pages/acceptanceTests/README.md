# Static Pages acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
suite; wire service `cr2se.page`. B publishes `/` as `text/html`, bytes `abc`,
and `/style.css` as `text/css`, bytes `x`. Fixed price4, maximumPathBytes1024,
maximumResourceBytes100. `get` input contains path/maximumBytes, without an
invented operation discriminator. Content is a local snapshot port.

```text
TEST PG-01 local publication and root
  ACT advertise valid Page offering with fixture root
  ASSERT root exists, mediaType="text/html", content fits offering limits
  FOR EACH [missing root, root wrong mediaType, root exceeds offering limit]:
    ACT advertise; ASSERT cannot expose a conforming unusable Page offering
  ACT authorized local replace/remove asset
  ASSERT affects current resource map; no peer publish/edit/list operation invented

TEST PG-02 exact get output
  ACT get(path="/",maximumBytes3), accept price4
  ASSERT path="/"; mediaType="text/html"; contentSize3; content=ASCII("abc"); price4
  ASSERT contentHash=hex("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
  ASSERT one complete consistent result attributed to authenticated B

TEST PG-03 canonical paths
  FOR EACH valid path IN ["/","/about","/a/b", "/%2e%2e", "/a?b#c"]:
    ACT validate; ASSERT valid literal protocol path within limits
  FOR EACH invalid path IN ["about","/about/","//a","/a/./b","/a/../b",
                            backslash, control character, invalidUTF8, component256 bytes]:
    ACT get; ASSERT rejected before unsafe resource access; no charge
  ASSERT percent signs never decoded by Page service; ?/# not query/fragment separators
  ACT paths differing in case or Unicode normalization
  ASSERT distinct logical names, without implicit normalization

TEST PG-04 media types
  FOR EACH valid IN ["text/html","image/svg+xml","application/octet-stream"]:
    ACT publish within limits; ASSERT exact media label retained
  FOR EACH invalid IN ["Text/html","text/html; charset=utf-8","text /html",
                      "text", "a/b/c", tokenLength64, nonASCII]:
    ACT publish; ASSERT invalid resource not made available
  ASSERT content not transformed/compressed/charset-converted by media label

TEST PG-05 bounded and empty resources
  ACT get root with maximumBytes2; ASSERT failure without charge
  ACT maximumBytes101 exceeds offering100; ASSERT failure before output
  ACT get asset at exact byte bound; ASSERT succeeds
  ACT publish empty asset, then get maximumBytes0
  ASSERT contentSize0; empty SHA256 hash; fixed price4 still applies
  ACT path byte length above1024 using valid components
  ASSERT rejected before allocation/access

TEST PG-06 missing resource and access safety
  ACT get("/missing",100)
  ASSERT failure, not root or an HTML error document presented as success
  ACT filesystem adapter fixture with symlink/path escape under permitted logical path
  ASSERT no read outside configured root; safely refuse or use confined mapping
  ASSERT no peer-supplied path grants host filesystem authority

TEST PG-07 immutable response snapshot
  ACT accept root get, pin old bytes; replace root with different complete content
  ACT finish first response
  ASSERT metadata/hash/content all refer to old bytes, price4
  ACT new explicit get
  ASSERT complete new snapshot permitted, separately charged4
  ASSERT no mixed old/new bytes even across fragmented transfer

TEST PG-08 static selection and multiple offerings
  ACT same path through two valid offerings with different price/size limits
  ASSERT same currently published resource, subject to each selected bound
  ACT two eligible visitors request pinned same resource
  ASSERT content selection does not depend on visitor/cookies/balance/history
  ASSERT get does not evaluate visitor code, templates or server-side logic
  ASSERT pre-generated content may change only through publication

TEST PG-09 local check matrix
  ACT check complete PG-02 result with original request/price
  ASSERT pass; no remote check invocation or charge
  FOR EACH [different path, invalid media, wrong size/hash, wrong accepted price,
            modified content in a complete response]:
    ACT check; ASSERT fail
  ACT missing required request/content or local resource exhaustion
  ASSERT inconclusive, not pass
  ASSERT pass does not create a resource signature or transferable publisher proof

TEST PG-10 interruption and accounting
  ACT output truncation, explicit content read failure before success, or cancellation before effects
  ASSERT no successful result/charge; partial content not successful page
  ACT possible commitment followed by lost reply
  ASSERT common outcome_unknown rules, not fabricated rollback
  RUN applicable Services SV-09 completion/accounting cuts

TEST PG-11 assets, cache and budgets
  ACT root contains reference to /style.css; client authorizes only root price4
  ASSERT no automatic additional debit or invocation
  ACT explicitly authorize asset price4; ASSERT separate output and charge4
  ACT inspect cached result keyed by B/path/hash
  ASSERT no implied freshness period or free conditional-get operation
  ACT new paid get; ASSERT observes selected current snapshot

TEST PG-12 untrusted content and independent composition
  ACT page content contains scripts, descriptions or instructions
  ASSERT no authority to invoke other services, publish, sign or spend
  ACT start Pages with Services/authenticated context/hash/content adapters only
  ASSERT get/check works without Files, Discovery, Computation or paid Storage calls
```
