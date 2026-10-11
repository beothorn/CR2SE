# Computation acceptance tests

[Specification](../README.md) · [Inputs](../inputs/README.md) · [Outputs](../outputs/README.md)

Use the [shared harness](../../../AcceptanceTests.md) and common cases. Optional
suite. Use an explicitly installed runtime pair `R`, an authorized deterministic
source fixture whose language-defined evaluation string is `"42"`, and a
controllable runtime adapter. Rate1/1000, minimumPrice1, requested limit60000ms
give maximumPrice60. Fixture limits permit that source and duration. Re-run
evaluation cases on the real advertised runtime; do not require a particular
implementation language or assume every language evaluates the same source.

```text
TEST CO-01 exact runtime and source
  ACT request exact advertised R with valid UTF8 source
  ASSERT that runtime selected; source unchanged
  FOR EACH [unadvertised version, case-changed language, malformed language syntax,
            invalid UTF8, source beyond advertised byte limit, duration outside limits]:
    ACT invoke; ASSERT no execution; no charge
  ACT empty source; ASSERT accepted only when R defines valid evaluation for it

TEST CO-02 price vectors and finite reservation
  ACT quote duration60000; ASSERT maximumPrice=60
  ACT bill duration1201; ASSERT finalPrice=2
  ACT rate0/minimum3 on fresh valid offering; ASSERT final and maximum price=3
  FOR EACH [denominator0, minimum0, maximum formula>U64_MAX]:
    ACT validate terms; ASSERT REJECT before execution
  fixture available credits59; ACT request maximum60
  ASSERT no execution; reservation failure

TEST CO-03 result completion and evaluation semantics
  ACT runtime produces evaluation value strictly before limit after1200.1ms
  ASSERT outcome="result"; billedMilliseconds=1201; price=2; result="42"
  ASSERT diagnostic absent; settled2, unused reservation58 released
  runtime also wrote distinct stdout "not the result"
  ASSERT output result remains language evaluation string, not stdout

TEST CO-04 measured interval
  queue100ms before start; execute0.1ms; convert/transmit/cleanup500ms afterward
  ACT complete; ASSERT billedMilliseconds=1; price=1
  ACT coarse monotonic clock reports0ms; ASSERT billedMilliseconds=1
  ACT runtime startup/parsing after clock starts takes1200.1ms
  ASSERT included in measured duration
  ACT civil clock jumps backward while monotonic execution clock advances
  ASSERT duration follows monotonic clock only

TEST CO-05 language errors
  ACT runtime reports syntax/language error at1201ms
  ASSERT outcome="executionError"; billedMilliseconds=1201; price=2
  ASSERT result absent; diagnostic optional valid bounded UTF8
  ASSERT successful billable completion, not generic service failure

TEST CO-06 limit and race precedence
  FOR EACH value observed IN [at60000ms, after60000ms, same observation as timeout]:
    ACT runtime emits value
    ASSERT outcome="timeLimitReached"; billedMilliseconds=60000; price=60
    ASSERT result and diagnostic absent
  ACT value observed strictly before limit
  ASSERT result outcome permitted, with capped rounded billed duration
  ACT termination delayed to65000ms
  ASSERT still billed60000 and price60; late events cannot change completion

TEST CO-07 completion shape and price validation
  FOR EACH [unknown outcome, result outcome missing result, result with diagnostic,
            error with result, limit with result/diagnostic, billed0 or>limit,
            wrong final price, price above accepted maximum]:
    ACT requester validates mutated completion
    ASSERT invalid result; no recognition as conforming successful settlement
  ACT result empty string from runtime defining that value; ASSERT valid

TEST CO-08 execution boundary and startup failure
  fixture authorized host facilities and concurrency limits
  ACT peer source/description requests unauthorized facility or runtime install
  ASSERT local boundary/authority unchanged; no automatic installation
  ACT provider cannot start runtime
  ASSERT explicit uncharged service failure; reservation released when safe
  ASSERT diagnostic text not interpreted as instructions or machine outcome

TEST CO-09 no silent re-execution
  runtime increments externally observed counter once; lose reply or crash adapter
  ACT recover accepted local attempt
  ASSERT recover durable completion or outcome_unknown
  ASSERT counter never increments again due to automatic retry
  ACT explicitly authorized new invocation
  ASSERT distinct attempt and separately priced work

TEST CO-10 independent check matrix
  FOR EACH (provider,checker,deterministic,expected) IN [
    (result42,result42,true,pass), (result42,result43,true,fail),
    (result42,result43,false,inconclusive), (result42,timeLimit,false,inconclusive),
    (executionError,result42,true,inconclusive), (result42,unavailable,true,inconclusive)]:
    ACT local check same input/runtime/time limit
    ASSERT outcome=expected; no call to original provider; no automatic refund
  ASSERT pass does not certify billed duration or program safety

TEST CO-11 concurrency and completion recovery
  configure two attempts with independently finite maximum reservations
  ACT run concurrently with controlled runtimes
  ASSERT completions and charges remain correlated, within each accepted bound
  RUN applicable Services SV-09 result/settlement cuts
  ASSERT local recovery does not imply a remote job-status/resume operation
```
