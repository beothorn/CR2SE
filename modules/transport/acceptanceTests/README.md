# Transport acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Required
suite. `V` refers to the pinned [wire vectors](../pseudocode/TestVectors.md).
Use test-owned socket/clock/crypto adapters; repeat vector/handshake cases with
real cryptography. Unless testing integrity itself, malformed protected frame
fixtures have a valid independently generated tag so the intended parser/state
rule is reached. Test sequence exhaustion through a controlled state fixture.

```text
TEST TR-01 exact handshake and first frame
  ACT establish initiator/acceptor using V.keys and nonces
  ASSERT HELLO payloads each100 bytes; AUTH payloads each64 bytes
  ASSERT exact transcript, signatures, keys, nonce prefixes and first tag = V
  ASSERT authenticated connection event carries exact local/peer IDs
  ASSERT no application event before peer AUTH verifies
  FOR EACH role IN [initiator, acceptor]:
    ASSERT trace order: write local AUTH completely, verify peer AUTH successfully,
           calculate X25519 shared secret, HKDF extract/expand, install both directions,
           emit authenticated connection
    ASSERT first protected send/receive sequence = 0

TEST TR-02 partial and coalesced I/O
  FOR EACH split position in fixture header/payload/tag and one-byte segmentation:
    ACT deliver valid handshake plus two protected frames in those chunks
    ASSERT same authenticated events and ordered application bytes as unsplit fixture
  ACT one read containing multiple frames and writes accepting only 1..3 bytes
  ASSERT complete wire output equals oracle stream; no interleaved frame bytes

TEST TR-03 header and payload bounds
  ACT encode DATA lengths1 and65536 on active stream
  ASSERT 12-byte big-endian header; length excludes16-byte tag
  ASSERT received payload equals original
  FOR EACH [payload length65537, nonzero flags, unknown frame type, version2,
            stream0 DATA, nonzero stream PING]:
    ACT receive frame; ASSERT TCP closed before excessive allocation or dispatch
  ASSERT unsupported version does not trigger unsafe error encoding

TEST TR-04 handshake failure matrix
  FOR EACH [AUTH before HELLO, duplicate HELLO, duplicate AUTH, application frame early,
            HELLO length99/101, AUTH length63/65, unsupported handshake selector,
            wrong expected identity, bad AUTH signature, all-zero X25519 result]:
    ACT handshake fixture; ASSERT connection rejected; no authenticated application data
  ACT reverse arrival order of valid HELLOs
  ASSERT transcript remains TCP-role ordered
  FOR EACH role IN [initiator, acceptor]:
    ACT valid HELLO then invalid AUTH signature with strict crypto call recording
    ASSERT no shared-secret X25519 or HKDF call; no installed keys/prefixes
    ASSERT TCP closes without response after local AUTH; no authenticated event
    ACT HELLO with all-zero ephemeral public key and invalid AUTH signature
    ASSERT signature failure takes precedence; shared-secret X25519 never called
    ACT same HELLO with a valid signature over its actual transcript
    ASSERT verify succeeds before X25519 returns zero; no HKDF or installed material
    ASSERT TCP closes without response; no authenticated event
  ASSERT expected-ID rejection also makes no shared-secret X25519 or HKDF call
  FOR EACH role IN [initiator, acceptor]:
    ACT peer HELLO with Ed25519 key I from Cryptography negative vectors,
        correctly derived claimed ID and otherwise valid fields;
        peer AUTH = I || zero(32)
    ASSERT rejected before authenticated event or X25519/HKDF derivation
    ASSERT no application data accepted
    ACT valid HELLO with AUTH R replaced by I, then with S replaced by Lbytes
    ASSERT each rejected; no authenticated event or session keys

TEST TR-05 per-direction tag transition
  ACT receive AUTH and first tagged frame together after local handshake prerequisites
  ASSERT AUTH itself untagged; immediately following frame verified with sequence0
  ACT send non-handshake frame before verifying remote AUTH
  ASSERT forbidden even if local AUTH already sent
  ACT withhold peer AUTH after receiving valid HELLO
  ASSERT local AUTH is sent untagged without waiting; keys/prefixes still absent
  ACT expire handshake deadline
  ASSERT close without further bytes or authenticated event
  ACT socket accepts a prefix of local AUTH then fails
  ASSERT close without raw ERROR or subsequent frame; no key derivation
  ACT same-identity handshake with independent fresh ephemeral material
  ASSERT accepted; directional roles remain distinct

TEST TR-06 integrity, replay and secret lifecycle
  FOR EACH mutation IN [header bit, payload bit, tag bit, replay at next sequence,
                        reversed direction key, reversed nonce prefix, old connection tag]:
    ACT receive mutated protected frame
    ASSERT TCP closes without error frame; unauthenticated payload not dispatched
  ASSERT receive sequence advances only after complete valid authentication
  ACT would wrap directional uint64 sequence
  ASSERT closes before wrap; no nonce reuse
  ACT close connection; ASSERT session/ephemeral secret handles released
  FOR EACH handshake exit IN [success, invalid signature, zero shared secret,
                              expected-ID mismatch, I/O failure, timeout]:
    ASSERT local ephemeral private key released

TEST TR-07 exact stream allocation
  ACT initiator opens3 streams; acceptor opens3 streams
  ASSERT IDs=[1,3,5] and[2,4,6] respectively
  FOR EACH [wrong parity, skipped next ID, reused ID, out-of-order ID,
            DATA for never-created ID]:
    ACT receive fixture; ASSERT connection error
  ACT exhaust uint32 stream allocation
  ASSERT GOAWAY ID_EXHAUSTED then drain; no wrapped/reused stream ID

TEST TR-08 OPEN protocol selection
  ACT OPEN("cr2se.peer",1); ASSERT dispatched to registered consumer
  ACT valid unknown protocol/version; ASSERT stream ERROR UNSUPPORTED_PROTOCOL
  FOR EACH [empty ID, >255 bytes, uppercase, adjacent dots, leading/trailing dot,
            protocolVersion0, invalid UTF8, trailing payload bytes]:
    ACT OPEN with correct next stream ID
    ASSERT stream ERROR PROTOCOL_ERROR; ID consumed; other streams usable

TEST TR-09 multiplexing and independent halves
  ACT interleave DATA on streams1 and3 in both directions
  ASSERT each direction's concatenated bytes match its own input order
  FOR EACH firstEnd IN [local,remote]:
    ACT END(firstEnd); ASSERT opposite send direction still usable
    ACT END(other); ASSERT normal closure only after both ENDs
  FOR EACH [DATA after own END, repeated END, invalid END payload]:
    ACT affected active stream; ASSERT stream error; independent stream remains usable

TEST TR-10 cancellation and terminal frames
  ACT CANCEL active stream; then deliver queued DATA/END for same ID
  ASSERT both directions terminal; queued non-OPEN frames discarded
  ACT OPEN reusing terminal ID; ASSERT connection error
  ASSERT cancellation emits no Ledger rollback or automatic application retry

TEST TR-11 PING/PONG
  token=hex("0001020304050607")
  ACT PING on stream0; ASSERT exactly one PONG with same8 bytes
  ACT unsolicited or duplicate PONG; ASSERT ignored without connection error
  ACT wait for token while unrelated PONG arrives, then expire configured timer
  ASSERT ping not reported successful

TEST TR-12 graceful shutdown
  fixture local streams1,3,5 opened; remote GOAWAY lastAccepted=3
  ACT receive GOAWAY; ASSERT stream5 refused; 1/3 may finish; no new local OPEN
  ACT valid next remote OPEN after GOAWAY
  ASSERT REFUSED_STREAM while existing accepted streams drain
  FOR EACH [wrong parity, ID above greatest opened, repeated GOAWAY increasing bound]:
    ACT invalid GOAWAY; ASSERT connection error
  ACT accepted streams finish; ASSERT TCP may close without cancelling completed results

TEST TR-13 errors and diagnostics
  ACT valid ERROR on known stream; ASSERT only that stream terminates
  ACT valid ERROR on stream0; ASSERT connection terminates
  FOR EACH [unregistered error code, NO_ERROR in ERROR/CANCEL, reason>1024 bytes,
            invalid UTF8 reason, trailing control bytes]:
    ACT receive malformed payload; ASSERT connection error
  ASSERT diagnostic text never drives machine state or contains local secrets
  FOR EACH type IN [ERROR, CANCEL, GOAWAY]:
    FOR EACH rejected row IN V.diagnosticReasons:
      ACT parse row payload for type; ASSERT malformed payload
      ACT receive on an applicable active connection/stream with valid tag
      ASSERT connection error; diagnostic not delivered as valid
      ACT encode row reason for type; ASSERT rejection before payload/wire emission
    FOR EACH accepted row IN V.diagnosticReasons:
      ACT encode then parse reason for type
      ASSERT payload exactly equals vector; reason bytes unchanged
  ASSERT byte length includes interior U+FEFF; no normalization or BOM stripping

TEST TR-14 truncation and failed connection
  FOR EACH prefix ending within any header/payload/tag:
    ACT deliver prefix then EOF
    ASSERT truncation failure; no resynchronization scan or provisional data dispatch
  ACT EOF at frame boundary with unfinished streams
  ASSERT each unfinished stream fails; already normally closed streams stay complete

TEST TR-15 bounded consumers and timeouts
  configure finite queue/stream/connection caps and handshake deadline
  ACT silent handshake peer; advance deadline
  ASSERT closed with no authenticated session
  ACT slow consumer while another stream exchanges small data
  ASSERT queued data remains within configured cap or affected stream cancelled
  ASSERT no unbounded allocation; whole-frame writes remain serialized
  ASSERT resource refusal cannot be reported as normal service completion
```

Weak-point and scalar fixtures are defined in the
[Cryptography negative vectors](../../cryptography/acceptanceTests/README.md#negative-ed25519-vectors).
