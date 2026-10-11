# Node API acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
suite, required when this API is supplied. The framing/token cases apply to the
loopback binding; embedded bindings exercise the same logical authority and
operation cases without inventing a token requirement. Use fake module ports
and repeat AT-E08 with real modules.

```text
TEST API-01 session authorization and limits
  ACT connect configured loopback endpoint; session.open(version1,validToken)
  ASSERT version=1; maximum_message_bytes=1048576; maximum_chunk_bytes=65536
  ASSERT maximum_blob_bytes is exact uint64 string, configured value>=65536
  FOR EACH [wrong token, malformed token, operation before open]:
    ACT fresh session; ASSERT no privileged operation; no node secrets disclosed
  ACT unsupported session version; ASSERT unsupported_version and closed
  ACT invalid token; ASSERT not_authorized and closed
  ASSERT no non-loopback administrative bind enabled by default

TEST API-02 JSON lines and response correlation
  ACT split valid request at every byte boundary, including inside multibyte UTF8
  ASSERT one request processed after complete LF-delimited object
  ACT several complete requests in one read; delay first operation
  ASSERT correct original IDs on responses; each has exactly one terminal response
  ASSERT out-of-order completion does not mix results
  ACT optional progress event
  ASSERT event/request_id present, id/ok absent; original terminal response still required

TEST API-03 parser and ID limits
  FOR EACH [invalid UTF8, duplicate JSON member, malformed JSON, depth33,
            message1048577 bytes before LF, duplicate active request ID]:
    ACT receive; ASSERT session closes; no guessed request ID response after parse failure
  ACT valid fixture message at1048576 bytes and ID128 UTF8 bytes
  ASSERT accepted if remaining operation fields valid
  ACT ID empty or129 bytes; ASSERT rejected
  ACT unknown operation; ASSERT unknown_operation; no module dispatch

TEST API-04 blob create/write/finish/read/close
  ACT blob.create(length="3"); save h
  ACT write(h,offset="0",data=Base64("ab")); ASSERT written=2
  ACT write(h,offset="2",data=Base64("c")); ASSERT written=1
  ACT finish(h); ASSERT length="3" and immutable
  ACT read(h,offset="1",length=10); ASSERT data=Base64("bc"); eof=true
  ACT read(h,offset="3",length=1); ASSERT empty data and eof=true
  ACT close(h); ASSERT empty success; later handle use fails
  ACT create0 then finish; ASSERT empty immutable blob is valid

TEST API-05 blob validation and quotas
  FOR EACH [gap, overlap, write past declared length, zero-byte write, chunk65537,
            read length0/65537, offset beyond size, noncanonical Base64]:
    ACT malformed operation on fresh fixture; ASSERT REJECT; blob contents unchanged
  ACT finish before complete length; ASSERT failure; blob not published as complete
  ACT read/invoke unfinished blob or write after finish; ASSERT REJECT
  ACT create/input/output temporary data exceeding configured total quota
  ASSERT resource_limit without unlimited allocation

TEST API-06 session ownership and pinning
  fixture sessions S1,S2; S1 owns h and connection c
  ACT S2 reads/writes/closes h or uses inaccessible c
  ASSERT no access to S1 data or authority
  ACT S1 invokes with h, hold invocation active, then close(h)
  ASSERT conflict while pinned
  ACT terminal completion; ASSERT pin released; close can succeed
  ASSERT any path-shaped handle is opaque, never opened as an arbitrary file

TEST API-07 connection operations
  ACT connection.open(valid endpoint,expected_peer_id=B)
  ASSERT result connection_id scoped to session; peer_id=B only after authentication
  ACT connections.list; ASSERT only accessible connected records with exact endpoint/peer fields
  ACT connection.ping with matched PONG; ASSERT reachable=true
  ACT ping timeout/unrelated PONG; ASSERT reachable=false
  ACT connection.close; ASSERT graceful Transport shutdown command
  FOR EACH [port0/65536, wrong expected ID, prohibited destination]:
    ACT open; ASSERT rejected without a misleading connected handle

TEST API-08 metadata and exact translation
  ACT board.get and service.get through connection c
  ASSERT returned Board/definition matches authenticated module response
  ACT invoke arguments containing U64_MAX, int64 minimum, negative-zero float,
      inline bytes and finished text/blob handles
  ASSERT Peer Control gets exact values, declared byte lengths and ordered contents
  ASSERT Board uint64 JSON numbers not rounded by local serialization

TEST API-09 invocation budgets and issuer
  ACT service.invoke with issuerB, maximum_price="7", valid arguments
  ASSERT accepted quote7 yields service_result and final_price="7"
  FOR EACH [missing issuer, missing bound, issuer changes toC, quote8,
            client budget6, invalid blob handle]:
    ACT invoke; ASSERT no unauthorized acceptance or charge
  fixture Computation maximum60/final2
  ACT invoke; ASSERT final_price="2"; never reinterpret bound as a fixed upfront debit

TEST API-10 wanted offer and installed handler
  ACT service.offer with exact service/version/issuer and maximum_resource_price
  ASSERT existing authorized provider gets bounded work
  ACT same offer without local matching handler; ASSERT unsupported
  ACT peer suggestion to compile/install a provider
  ASSERT no automatic install, execution or additional resource authorization

TEST API-11 checks
  ACT service.check paid Storage evidence with retained expected byte
  ASSERT check_result computed locally and final_price exact
  ACT missing original expected evidence; ASSERT outcome=inconclusive
  ACT Discovery included check with maximum_price="0"; ASSERT permitted when entitled
  ACT local-only check; ASSERT no fabricated remote operation

TEST API-12 ledger operations
  FOR EACH ledger.balance, ledger.transfer, ledger.transfer.get, ledger.claim.redeem:
    ACT documented request fields through authorized session
    ASSERT exact canonical values/authenticated context reach Peer Control
    ASSERT response fields match issuer result with exact decimal/Base64 representation
  ACT malformed order/key/signature/transfer ID or redemption envelope
  ASSERT rejected without exposing bearer secret

TEST API-13 third-party results
  ACT price7 fee2 transfer with maximum_price="9"
  ASSERT final_price="7"; transfer_fee="2"
  ACT authenticated issuer confirms; ASSERT settlement_state="settled"
  ACT issuer unreachable; ASSERT service result separate from settlement_state="unsettled"
  ASSERT no second service invocation to repair payment

TEST API-14 cancellation and session loss
  ACT cancel pending uncommitted request R
  ASSERT cancel_requested does not replace R's terminal response
  ASSERT cancelled only if no accepted effects possible
  ACT cancel after possible remote commit
  ASSERT outcome_unknown when unresolved; no rollback promise
  ACT lose session with unfinished blobs and one committed provider obligation
  ASSERT temporary handles cleaned; uncommitted work cancelled when possible
  ASSERT durable service/Ledger obligations and retained recovery results survive

TEST API-15 large output completion and diagnostics
  ACT partial peer result then disconnect
  ASSERT no finished successful output blob exposed
  ACT complete valid large result
  ASSERT finished read-only session-owned handle returned only after validation
  ASSERT errors/logs contain no token, private key, bearer secret or another client's data
```
