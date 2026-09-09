# Computation pseudocode

This document translates the normative Computation contract in
[`Computation.md`](../Computation.md) into implementation-neutral pseudocode.
The specification remains authoritative. Names such as `RuntimeRegistry`,
`CreditReservations`, clocks, locks, and callbacks describe responsibilities,
not required classes, processes, APIs, or thread models.

Source, result text, diagnostics, Boards, service definitions, and invocation
values are untrusted input. JSON integers below are mathematical integers; an
implementation must not first round them through a binary floating-point type.

Computation version 1 has two service-specific rules:

```text
the requester accepts a maximum price before execution, while the exact final
    price is returned in the completion record and may be lower;

the check is later independent re-execution by the requester or its chosen
    checker, not another invocation of the original provider.
```

---

## 1. Constants and data structures

```text
SERVICE_ID                       = "cr2se.computation"
SERVICE_VERSION                  = 1
PRICING_MODEL                    = "cr2se.computation.v1"
UINT64_MAX                       = 18_446_744_073_709_551_615

OUTCOME_RESULT                   = "result"
OUTCOME_TIME_LIMIT_REACHED       = "timeLimitReached"
OUTCOME_EXECUTION_ERROR          = "executionError"

CHECK_PASS                       = "pass"
CHECK_FAIL                       = "fail"
CHECK_INCONCLUSIVE               = "inconclusive"

RuntimePair:
    language                     nonempty valid language identifier
    languageVersion              nonempty UTF-8 string

ExecutionTimeFactor:
    numerator                    uint64
    denominator                  uint64 in 1 .. UINT64_MAX

ComputationTerms:
    minimumPrice                 uint64 in 1 .. UINT64_MAX
    executionTimeFactor          ExecutionTimeFactor
    minimumExecutionMilliseconds uint64 in 1 .. UINT64_MAX
    maximumExecutionMilliseconds uint64 in 1 .. UINT64_MAX
    maximumSourceBytes           uint64 in 1 .. UINT64_MAX
    runtimes                     nonempty list<RuntimePair>
    runtimeSet                   Set<RuntimePair>

ValidatedInput:
    language                     valid language identifier
    languageVersion              nonempty UTF-8 string
    source                       valid UTF-8 string
    sourceBytes                  exact UTF-8 byte length
    maxExecutionMilliseconds     uint64 in offering range

PriceAuthorization:
    creditIssuer                 canonical 32-byte CR2SE ID
    maximumPrice                 uint64 in 1 .. UINT64_MAX
    offeringId                   string
    offeringRevision             implementation-defined immutable revision

AcceptedInvocation:
    requesterId                  authenticated CR2SE ID
    providerId                   local CR2SE ID
    offering                     immutable accepted offering snapshot
    terms                        ComputationTerms
    input                        ValidatedInput
    authorization               PriceAuthorization
    reservation                 credit reservation handle
    state                        ACCEPTED | EXECUTING | COMPLETED | FAILED
    completion                   CompletionRecord or NONE

CompletionRecord:
    outcome                      RESULT | TIME_LIMIT_REACHED | EXECUTION_ERROR
    billedMilliseconds           uint64
    price                        uint64 credits
    result                       UTF-8 string or NONE
    diagnostic                   untrusted UTF-8 string or NONE

CheckResult:
    outcome                      PASS | FAIL | INCONCLUSIVE
    checkedOutcome               completion outcome or NONE
    checkedResult                UTF-8 string or NONE

ProviderPolicy:
    maximumInputBytes            local transport/resource bound
    maximumResultBytes           local resource bound
    maximumDiagnosticBytes       local resource bound
    maximumConcurrentExecutions  positive integer
    trustAndSecurityPolicy       local policy
```

An implementation may use lower local limits or reject risky work before
acceptance. It must not advertise limits or runtimes that it cannot honor after
acceptance.

---

## 2. Exact value validators

```text
function requireObject(value, name):
    if logical type of value is not object:
        raise ValidationError(name + " must be an object")
    return value


function requireUtf8StringMember(object, name, nonempty):
    if object has no member name:
        raise ValidationError(name + " is required")

    value = object[name]
    if logical type of value is not string or value is not valid UTF-8:
        raise ValidationError(name + " must be valid UTF-8 text")

    if nonempty and byteLengthUtf8(value) == 0:
        raise ValidationError(name + " must not be empty")

    return value


function requireUint64Member(object, name, minimum):
    if object has no member name:
        raise ValidationError(name + " is required")

    value = object[name]
    if logical type of value is not integer:
        raise ValidationError(name + " must be an exact integer")

    if value < minimum or value > UINT64_MAX:
        raise ValidationError(name + " is outside its uint64 range")

    return value


function isValidLanguageIdentifier(language):
    if byteLengthUtf8(language) == 0:
        return false

    bytes = UTF8.encode(language)
    if bytes[0] not in ASCII('a'..'z') and bytes[0] not in ASCII('0'..'9'):
        return false

    for each byte in bytes:
        if byte not in ASCII('a'..'z')
           and byte not in ASCII('0'..'9')
           and byte not in {ASCII('.'), ASCII('-'), ASCII('_')}:
            return false

    return true
```

Booleans, strings containing digits, fractional numbers, infinities, and
floating-point approximations are not integers. Lengths count UTF-8 bytes, not
characters or code points.

---

## 3. Computation offering validation

This validator is registered for `cr2se.computation.v1` with the Board pricing
model registry. Common Board validation has already checked the offering ID,
description, issuer, preconditions, and general JSON shape.

Unlike pricing models whose final price is known from input alone, this handler
returns the maximum authorization before execution and validates the metered
final price afterward. Calls to a generic Board `determineMainPrice` operation
must dispatch to the Computation-specific agreement and finalization functions
below rather than treating the maximum as the final charge.

```text
function validateComputationOffering(offering):
    if offering.service != SERVICE_ID:
        raise ValidationError("pricing model used with the wrong service")

    if offering.serviceVersion != SERVICE_VERSION:
        raise ValidationError("unsupported Computation service version")

    if offering has fixed Board price:
        raise ValidationError("Computation version 1 requires pricing")

    if offering.pricing.model != PRICING_MODEL:
        raise ValidationError("wrong Computation pricing model")

    // The Computation check never invokes the original provider and cannot
    // have a separately charged provider check.
    if offering.checkPrice != NONE:
        raise ValidationError("checkPrice is not applicable to Computation v1")

    pricing = requireObject(offering.pricing, "pricing")
    minimumPrice = requireUint64Member(pricing, "minimumPrice", minimum = 1)

    factorObject = requireObject(
        pricing["executionTimeFactor"],
        "executionTimeFactor"
    )
    numerator = requireUint64Member(factorObject, "numerator", minimum = 0)
    denominator = requireUint64Member(factorObject, "denominator", minimum = 1)

    info = requireObject(offering.info, "info")
    minimumExecutionMilliseconds = requireUint64Member(
        info, "minimumExecutionMilliseconds", minimum = 1)
    maximumExecutionMilliseconds = requireUint64Member(
        info, "maximumExecutionMilliseconds", minimum = 1)
    maximumSourceBytes = requireUint64Member(
        info, "maximumSourceBytes", minimum = 1)

    if minimumExecutionMilliseconds > maximumExecutionMilliseconds:
        raise ValidationError("minimum execution time exceeds maximum")

    runtimeValues = info["runtimes"]
    if logical type of runtimeValues is not array or length(runtimeValues) == 0:
        raise ValidationError("runtimes must be a nonempty array")

    runtimes = empty list
    runtimeSet = empty Set

    for each value in runtimeValues:
        object = requireObject(value, "runtime")
        language = requireUtf8StringMember(object, "language", nonempty = true)
        languageVersion = requireUtf8StringMember(
            object, "languageVersion", nonempty = true)

        if not isValidLanguageIdentifier(language):
            raise ValidationError("invalid language identifier")

        pair = RuntimePair {language, languageVersion}

        append pair to runtimes
        add pair to runtimeSet

    terms = ComputationTerms {
        minimumPrice: minimumPrice,
        executionTimeFactor: {numerator, denominator},
        minimumExecutionMilliseconds: minimumExecutionMilliseconds,
        maximumExecutionMilliseconds: maximumExecutionMilliseconds,
        maximumSourceBytes: maximumSourceBytes,
        runtimes: runtimes,
        runtimeSet: runtimeSet
    }

    // Every request within the advertised range must have a representable
    // maximum price.
    calculateMaximumPrice(
        terms,
        terms.maximumExecutionMilliseconds
    )

    return terms
```

Unknown fields retain the extension behavior defined by Board and Services.
They do not replace, relax, or contradict these required fields.

The provider must use an explicit runtime registry. A runtime name received
from a peer must never be interpolated into a shell command, executable path,
package name, or dynamic download instruction.

Any reader can structurally validate a provided or wanted offering without
having the advertised runtimes locally. Separately, before publishing a
provided offering, its provider checks its own capabilities:

```text
function validateProvidedRuntimeCapabilities(terms, runtimeRegistry):
    for each pair in terms.runtimeSet:
        runtime = runtimeRegistry.get(pair)
        if runtime == NONE:
            raise PublicationError("advertised runtime is unavailable")

        if not runtime.supportsFinalEvaluationValueAndStandardStringConversion:
            raise PublicationError("runtime cannot implement Computation v1 semantics")

        if not runtime.canEnforceTimeLimitThrough(
            terms.maximumExecutionMilliseconds):
            raise PublicationError("advertised time limit cannot be enforced")
```

---

## 4. Overflow-safe price calculation

```text
function ceilMultiplyDivide(left, right, denominator):
    require left >= 0
    require right >= 0
    require denominator > 0

    // product is mathematical arbitrary precision, not uint64 multiplication.
    product = BigInteger(left) * BigInteger(right)
    quotient = product div denominator
    remainder = product mod denominator

    if remainder != 0:
        quotient = quotient + 1

    return quotient


function calculatePriceForDuration(terms, billedMilliseconds):
    if billedMilliseconds < 1:
        raise InvalidBilledDuration

    ratePrice = ceilMultiplyDivide(
        billedMilliseconds,
        terms.executionTimeFactor.numerator,
        terms.executionTimeFactor.denominator
    )

    price = maximum(terms.minimumPrice, ratePrice)
    if price < 1 or price > UINT64_MAX:
        raise PriceOverflow

    return price


function calculateMaximumPrice(terms, requestedMaximumMilliseconds):
    if requestedMaximumMilliseconds < terms.minimumExecutionMilliseconds
       or requestedMaximumMilliseconds > terms.maximumExecutionMilliseconds:
        raise InvalidRequestedTimeLimit

    return calculatePriceForDuration(terms, requestedMaximumMilliseconds)


function calculateFinalPrice(terms, billedMilliseconds, authorization):
    price = calculatePriceForDuration(terms, billedMilliseconds)

    if price > authorization.maximumPrice:
        raise PriceExceedsAuthorization

    return price
```

The numerator may be zero, in which case both maximum and final prices equal
`minimumPrice`. Floating-point arithmetic must not be used anywhere in price
validation or calculation.

---

## 5. Invocation input validation

```text
function validateInvocationInput(value, terms, runtimeRegistry, providerPolicy):
    object = requireObject(value, "Computation input")

    language = requireUtf8StringMember(object, "language", nonempty = true)
    languageVersion = requireUtf8StringMember(
        object, "languageVersion", nonempty = true)
    source = requireUtf8StringMember(object, "source", nonempty = false)
    requestedMaximum = requireUint64Member(
        object, "maxExecutionMilliseconds", minimum = 1)

    if not isValidLanguageIdentifier(language):
        raise ValidationError("invalid language identifier")

    pair = RuntimePair {language, languageVersion}
    if pair not in terms.runtimeSet:
        raise UnsupportedRuntimePair

    runtime = runtimeRegistry.get(pair)
    if runtime == NONE:
        raise UnsupportedRuntimePair

    if not runtime.supportsFinalEvaluationValueAndStandardStringConversion:
        raise UnsupportedRuntimePair

    sourceBytes = byteLengthUtf8(source)
    effectiveSourceLimit = minimum(
        terms.maximumSourceBytes,
        providerPolicy.maximumInputBytes
    )
    if sourceBytes > effectiveSourceLimit:
        raise SourceTooLarge

    if requestedMaximum < terms.minimumExecutionMilliseconds
       or requestedMaximum > terms.maximumExecutionMilliseconds:
        raise InvalidRequestedTimeLimit

    // Empty source is accepted only when this exact runtime pair defines a
    // final evaluation value and result conversion for it.
    if sourceBytes == 0 and not runtime.acceptsEmptySourceWithDefinedResult:
        raise ValidationError("empty source has no defined result")

    return ValidatedInput {
        language: language,
        languageVersion: languageVersion,
        source: source,
        sourceBytes: sourceBytes,
        maxExecutionMilliseconds: requestedMaximum
    }
```

The transport must enforce the source limit while receiving bytes, before
uncontrolled allocation. Invalid UTF-8 is rejected; it is not repaired or
decoded using another character encoding.

---

## 6. Price agreement and acceptance

The maximum price is an authorization bound, not an advance debit and not
necessarily the final charge.

```text
function preparePriceAuthorization(offeringSnapshot, terms, validatedInput):
    maximumPrice = calculateMaximumPrice(
        terms,
        validatedInput.maxExecutionMilliseconds
    )

    return PriceAuthorization {
        creditIssuer: offeringSnapshot.creditIssuer,
        maximumPrice: maximumPrice,
        offeringId: offeringSnapshot.id,
        offeringRevision: offeringSnapshot.revision
    }


function acceptInvocation(
    authenticatedRequesterId,
    selectedOfferingId,
    completeInput,
    requesterAcceptedIssuer,
    requesterAcceptedMaximumPrice,
    boardState,
    runtimeRegistry,
    creditReservations,
    providerPolicy
):
    // Receive and validate without executing source or loading instructions
    // chosen by the source.
    offeringSnapshot = boardState.getCurrentProvidedOffering(selectedOfferingId)
    if offeringSnapshot == NONE:
        return UnchargedRejection(STALE_OR_UNAVAILABLE_OFFERING)

    try:
        terms = validateComputationOffering(offeringSnapshot)
        input = validateInvocationInput(
            completeInput, terms, runtimeRegistry, providerPolicy)
        authorization = preparePriceAuthorization(
            offeringSnapshot, terms, input)
    catch ValidationError or UnsupportedRuntimePair or PriceOverflow:
        return UnchargedRejection(INVALID_OR_UNSUPPORTED_REQUEST)

    if requesterAcceptedIssuer != authorization.creditIssuer:
        return UnchargedRejection(CREDIT_ISSUER_DISAGREEMENT)

    if requesterAcceptedMaximumPrice != authorization.maximumPrice:
        return UnchargedRejection(MAXIMUM_PRICE_DISAGREEMENT)

    if not allPreconditionsSatisfied(
        authenticatedRequesterId,
        offeringSnapshot.preconditions
    ):
        return UnchargedRejection(PRECONDITION_FAILED)

    if not providerPolicy.trustAndSecurityPolicy.permits(
        authenticatedRequesterId, offeringSnapshot, input)
    ):
        return UnchargedRejection(PROVIDER_POLICY_REJECTION)

    // Recheck availability and reserve under serialization appropriate to the
    // Board and ledger implementation. Concurrent reservations must not spend
    // the same available balance more than once.
    atomically:
        if not boardState.isStillCurrent(offeringSnapshot):
            return UnchargedRejection(STALE_OR_UNAVAILABLE_OFFERING)

        if provider has no execution capacity to commit:
            return UnchargedRejection(CAPACITY_UNAVAILABLE)

        reservation = creditReservations.reserve(
            debtor = authenticatedRequesterId,
            issuer = authorization.creditIssuer,
            maximumAmount = authorization.maximumPrice
        )
        if reservation is ERROR:
            return UnchargedRejection(INSUFFICIENT_ACCEPTED_CREDITS)

        accepted = AcceptedInvocation {
            requesterId: authenticatedRequesterId,
            providerId: local identity ID,
            offering: offeringSnapshot,
            terms: terms,
            input: input,
            authorization: authorization,
            reservation: reservation,
            state: ACCEPTED,
            completion: NONE
        }

        commit provider to attempt exactly one execution

    return Accepted(accepted)
```

Logical transports may order metadata, bounded source transfer, and the two
price-agreement messages differently, but acceptance occurs only after the
complete input is validated, the current offering and issuer agree, the exact
maximum price is accepted, funds are reserved, and the provider commits to the
execution. Source is never executed during validation.

---

## 7. Timed execution and outcome selection

The timed interval includes runtime initialization, parsing, compilation,
evaluation, and standard conversion of the evaluation value to UTF-8 result
text. Conversion is part of the computation: if it errors before the limit,
the outcome is `executionError`; if it does not finish before the limit, the
outcome is `timeLimitReached`.

```text
function executeAcceptedInvocation(
    invocation,
    runtimeRegistry,
    monotonicClock,
    providerPolicy
):
    require invocation.state == ACCEPTED
    invocation.state = EXECUTING

    pair = RuntimePair {
        invocation.input.language,
        invocation.input.languageVersion
    }
    runtime = runtimeRegistry.get(pair)

    if runtime == NONE or runtime cannot be started:
        return failAcceptedInvocationWithoutCharge(
            invocation, PROVIDER_COULD_NOT_START_RUNTIME)

    start = monotonicClock.now()
    deadline = monotonicClock.checkedAddMilliseconds(
        start,
        invocation.input.maxExecutionMilliseconds
    )
    if deadline is ERROR:
        return failAcceptedInvocationWithoutCharge(
            invocation, PROVIDER_CLOCK_RANGE_FAILURE)

    // Start exactly once. The runtime operation encompasses parse, compile,
    // evaluate, and standard locale-independent string conversion.
    execution = runtime.startEvaluateAndConvertToUtf8(invocation.input.source)
    limitSignal = monotonicClock.signalAtOrAfter(deadline)

    event = waitForFirstObservableEvent(
        execution.producedResultText,
        execution.reportedLanguageError,
        execution.providerInfrastructureFailure,
        limitSignal
    )

    observedAt = monotonicClock.nowAtObservation(event)

    // The limit wins unless a completed result or language error was observed
    // strictly before it. A result finishing at the limit is discarded.
    if observedAt >= deadline:
        chosenOutcome = TIME_LIMIT_REACHED
        resultText = NONE
        diagnostic = NONE
        stopOrAbandon(execution)
    else if event is producedResultText:
        if event.text is not valid UTF-8:
            return failAcceptedInvocationWithoutCharge(
                invocation, INVALID_RUNTIME_RESULT_ENCODING)
        if byteLengthUtf8(event.text) > providerPolicy.maximumResultBytes:
            return failAcceptedInvocationWithoutCharge(
                invocation, RESULT_RESOURCE_LIMIT)
        else:
            chosenOutcome = RESULT
            resultText = event.text
            diagnostic = NONE
    else if event is reportedLanguageError:
        chosenOutcome = EXECUTION_ERROR
        resultText = NONE
        diagnostic = optionalBoundedUntrustedDiagnostic(event, providerPolicy)
    else if event is providerInfrastructureFailure:
        return failAcceptedInvocationWithoutCharge(
            invocation, PROVIDER_EXECUTION_FAILURE)

    if chosenOutcome == TIME_LIMIT_REACHED:
        billedMilliseconds = invocation.input.maxExecutionMilliseconds
    else:
        elapsed = observedAt - start
        measuredMilliseconds = maximum(
            1,
            ceilDurationToWholeMilliseconds(elapsed)
        )
        billedMilliseconds = minimum(
            measuredMilliseconds,
            invocation.input.maxExecutionMilliseconds
        )

    price = calculateFinalPrice(
        invocation.terms,
        billedMilliseconds,
        invocation.authorization
    )

    if chosenOutcome == TIME_LIMIT_REACHED:
        assert billedMilliseconds == invocation.input.maxExecutionMilliseconds
        assert price == invocation.authorization.maximumPrice

    completion = CompletionRecord {
        outcome: chosenOutcome,
        billedMilliseconds: billedMilliseconds,
        price: price,
        result: resultText,
        diagnostic: diagnostic
    }

    atomically:
        if invocation.completion != NONE:
            raise InternalError("completion already chosen")
        invocation.completion = completion
        invocation.state = COMPLETED

    prevent execution from changing completion or adding later charges
    return completion
```

`reportedLanguageError` includes syntax, compilation, evaluation, and result
conversion errors reported through the selected language semantics. Such an
error is a valid billable completion. A provider/runtime crash, inability to
start, or failure to construct and return a valid record is a service failure
and is not charged.

The implementation must attempt to stop execution at the limit. Delayed or
imperfect termination cannot increase billed time beyond the request and
cannot change the chosen completion. Preventing abandoned code from continuing
to affect the host is a provider security responsibility, not a protocol
guarantee.

---

## 8. Result and diagnostic bounds

Computation version 1 does not advertise a portable result-size or diagnostic-
size guarantee. A provider therefore applies disclosed local resource policy
without changing the computation's defined pricing behavior.

```text
function acceptRuntimeResultTextIncrementally(chunks, providerPolicy):
    decoder = new strict incremental UTF-8 decoder
    result = bounded buffer

    for each chunk in chunks:
        if adding chunk exceeds providerPolicy.maximumResultBytes:
            raise ProviderInfrastructureFailure(RESULT_RESOURCE_LIMIT)
        decoder.accept(chunk)
        append chunk to result

    decoder.finishOrReject()
    return result as UTF-8 string


function optionalBoundedUntrustedDiagnostic(errorEvent, providerPolicy):
    if errorEvent has no valid UTF-8 diagnostic:
        return NONE

    return safelyTruncateUtf8AtByteLimit(
        errorEvent.diagnostic,
        providerPolicy.maximumDiagnosticBytes
    )
```

A result that the provider cannot return as a valid completion makes the
operation an uncharged service failure. Diagnostics are optional, so they may
be omitted or safely truncated without changing `executionError`.

---

## 9. Completion-record validation

```text
function validateCompletionRecord(value, acceptedInvocation):
    object = requireObject(value, "Computation completion")

    outcomeText = requireUtf8StringMember(object, "outcome", nonempty = true)
    billed = requireUint64Member(object, "billedMilliseconds", minimum = 1)
    statedPrice = requireUint64Member(object, "price", minimum = 1)

    if billed > acceptedInvocation.input.maxExecutionMilliseconds:
        raise InvalidCompletionRecord("billed time exceeds accepted limit")

    hasResult = object has member "result"
    hasDiagnostic = object has member "diagnostic"

    if outcomeText == OUTCOME_RESULT:
        if not hasResult or hasDiagnostic:
            raise InvalidCompletionRecord("invalid result fields")
        result = requireUtf8StringMember(object, "result", nonempty = false)
        diagnostic = NONE
        outcome = RESULT

    else if outcomeText == OUTCOME_TIME_LIMIT_REACHED:
        if hasResult or hasDiagnostic:
            raise InvalidCompletionRecord("time limit has no result or diagnostic")
        if billed != acceptedInvocation.input.maxExecutionMilliseconds:
            raise InvalidCompletionRecord("time limit must bill accepted maximum time")
        result = NONE
        diagnostic = NONE
        outcome = TIME_LIMIT_REACHED

    else if outcomeText == OUTCOME_EXECUTION_ERROR:
        if hasResult:
            raise InvalidCompletionRecord("execution error has no result")
        if hasDiagnostic:
            diagnostic = requireUtf8StringMember(
                object, "diagnostic", nonempty = false)
        else:
            diagnostic = NONE
        result = NONE
        outcome = EXECUTION_ERROR

    else:
        raise InvalidCompletionRecord("unknown completion outcome")

    calculatedPrice = calculateFinalPrice(
        acceptedInvocation.terms,
        billed,
        acceptedInvocation.authorization
    )

    if statedPrice != calculatedPrice:
        raise InvalidCompletionRecord("incorrect final price")

    if outcome == TIME_LIMIT_REACHED
       and statedPrice != acceptedInvocation.authorization.maximumPrice:
        raise InvalidCompletionRecord("time limit must charge maximum price")

    return CompletionRecord {
        outcome: outcome,
        billedMilliseconds: billed,
        price: statedPrice,
        result: result,
        diagnostic: diagnostic
    }
```

Unknown fields follow the common compatible-extension rule and do not override
the meanings of known fields. Result and diagnostic text remain untrusted even
after the record validates.

---

## 10. Settlement and service failure

The exact charged credits travel with the answer as `completion.price`.

```text
function providerFinishInvocation(invocation, completion, transport, ledger):
    require invocation.state == COMPLETED

    if transport.returnCompleteRecord(completion) is ERROR:
        creditReservations.release(invocation.reservation)
        mark invocation as service failure without charge
        stopOrAbandonAnyRemainingExecution(invocation)
        return SERVICE_FAILURE

    atomically:
        creditReservations.settle(
            invocation.reservation,
            finalAmount = completion.price
        )
        ledger.recordCompletedService(
            counterparty = invocation.requesterId,
            issuer = invocation.authorization.creditIssuer,
            amount = completion.price,
            offeringId = invocation.authorization.offeringId
        )
        release unused reservation amount

    return SUCCESS


function requesterReceiveCompletion(invocation, receivedValue, ledger):
    try:
        completion = validateCompletionRecord(receivedValue, invocation)
    catch any validation or transport failure:
        release requester-side authorization
        return SERVICE_FAILURE_WITHOUT_CHARGE

    atomically:
        ledger.recordCompletedService(
            counterparty = invocation.providerId,
            issuer = invocation.authorization.creditIssuer,
            amount = completion.price,
            offeringId = invocation.authorization.offeringId
        )
        release unused authorization amount

    return completion


function failAcceptedInvocationWithoutCharge(invocation, cause):
    atomically:
        if invocation.completion != NONE:
            return invocation.completion
        invocation.state = FAILED
        creditReservations.release(invocation.reservation)

    stopOrAbandonAnyRemainingExecution(invocation)
    return ServiceFailure(cause)
```

A pre-acceptance rejection, malformed record, provider infrastructure failure,
or loss of the record is uncharged. If communication makes the peers disagree
about whether a complete record was returned, their ledgers may differ; CR2SE
version 1 has no global adjudicator or completion-recovery operation.

---

## 11. Independent check

The requester retains the original input and completion if it may check later.
The original provider need not retain them and is not contacted or paid for the
check.

```text
function checkComputation(
    originalInput,
    originalCompletion,
    checkerRuntimeRegistry,
    requesterEstablishedDeterminism
):
    pair = RuntimePair {
        originalInput.language,
        originalInput.languageVersion
    }

    runtime = checkerRuntimeRegistry.get(pair)
    if runtime == NONE:
        return CheckResult {
            outcome: INCONCLUSIVE,
            checkedOutcome: NONE,
            checkedResult: NONE
        }

    checked = independentlyExecuteWithSameTimeLimit(
        runtime,
        originalInput.source,
        originalInput.maxExecutionMilliseconds
    )

    if originalCompletion.outcome != RESULT or checked.outcome != RESULT:
        return CheckResult {
            outcome: INCONCLUSIVE,
            checkedOutcome: checked.outcome,
            checkedResult: result text if checked.outcome == RESULT else NONE
        }

    if UTF8.encode(originalCompletion.result)
       == UTF8.encode(checked.result):
        return CheckResult {
            outcome: PASS,
            checkedOutcome: RESULT,
            checkedResult: checked.result
        }

    if requesterEstablishedDeterminism:
        return CheckResult {
            outcome: FAIL,
            checkedOutcome: RESULT,
            checkedResult: checked.result
        }

    return CheckResult {
        outcome: INCONCLUSIVE,
        checkedOutcome: RESULT,
        checkedResult: checked.result
    }
```

```text
function applyCheckToLocalTrust(checkResult, originalCompletion, localPolicy):
    observation = {
        checkOutcome: checkResult.outcome,
        originalOutcome: originalCompletion.outcome,
        checkedOutcome: checkResult.checkedOutcome,
        resultsDiffer: both results exist and differ
    }

    // A requester may lower trust when a deterministic result fails, when it
    // believes an executionError was unjustified, when timing is implausible,
    // or for another locally assessed reason. The protocol does not dictate a
    // numeric trust change.
    localPolicy.updateProviderTrustFromObservation(observation)

    do not modify or refund the already settled service price automatically
```

A `pass` proves only byte-for-byte agreement between two result texts. A
`fail` requires determinism to have been established before checking. Errors,
timeouts, unavailable runtimes, incomplete checks, and unexplained differences
without established determinism are `inconclusive`, but may still influence
the requester's local trust policy.

---

## 12. Retry and concurrency rules

```text
for each accepted invocation:
    execute source at most once;
    choose at most one terminal completion;
    settle at most one final price;
    never silently retry after a runtime or transport failure;
    never resume or query the job after the invocation ends;
    and never let late runtime activity change its outcome or charge.

across concurrent invocations:
    enforce a bounded execution-capacity limit;
    reserve every accepted maximum price independently;
    serialize balance checks and reservations sufficiently to prevent
        authorizing the same available credits more than once;
    isolate invocation completion state;
    and do not infer ordering or priority from Board array position.
```

Submitting the same logical input again is a new, separately accepted and
potentially charged invocation. Computation is not idempotent because source
may have external side effects or depend on mutable inputs.

---

## 13. Optional confidentiality

CR2SE Network authenticates peers and protects frame integrity, but does not
provide payload confidentiality by itself.

```text
function prepareSourceTransport(sourceBytes, confidentialityRequested):
    if not confidentialityRequested:
        return sourceBytes carried by authenticated CR2SE streams

    encryptionContext = negotiateApplicationEncryptionAccordingToEncryptionSpec()
    return encryptionContext.encryptForTransport(sourceBytes)
```

Application-layer encryption is optional. When used, it protects source in
transit from parties that lack the negotiated keys; it does not hide source
from the provider that must decrypt and execute it. The provider may inspect,
log, copy, or retain source, results, timing, and diagnostics.

---

## 14. Security boundaries

```text
before acceptance:
    validate all exact integers, strings, runtime pairs, limits, and prices;
    enforce source bounds while receiving;
    retrieve runtimes only from an explicit provider registry;
    and never evaluate source, definitions, metadata, or suggestions.

during execution:
    treat source as actively malicious;
    bound concurrency and implementation-owned queues;
    avoid command-shell interpolation;
    keep provider secrets out of the execution environment;
    use a monotonic clock;
    attempt termination at the accepted limit;
    and contain late or abandoned execution as far as the implementation can.

after execution:
    treat result and diagnostic text as untrusted data;
    do not execute results or render them as trusted markup;
    validate the complete record and exact price before ledger update;
    and do not claim that a check proves runtime safety or honest timing.
```

CR2SE version 1 does not guarantee process, filesystem, network, memory, CPU,
thread, side-channel, or host isolation. A provider may reject any invocation
before acceptance when its local security policy cannot safely execute it.

---

## 15. Service-definition consistency

```text
function validateComputationServiceDefinition(definition, offering):
    require definition.id == offering.id
    require definition.service == SERVICE_ID
    require definition.serviceVersion == SERVICE_VERSION
    require definition.description == offering.description

    require definition input logically contains these standard required fields:
        language: string
        languageVersion: string
        source: string
        maxExecutionMilliseconds: uint64

    require definition output logically contains these fields:
        outcome: required string
        billedMilliseconds: required uint64
        price: required uint64
        result: optional string
        diagnostic: optional string

    require definition check input logically contains:
        language: required string
        languageVersion: required string
        source: required string
        maxExecutionMilliseconds: required uint64
        originalOutcome: required string
        originalResult: optional string

    require definition check output logically contains:
        outcome: required string
        checkedOutcome: optional string
        checkedResult: optional string

    require every named field has a nonempty, noncontradictory description
    return VALID
```

Unknown compatible schema fields follow the Services extension rules. A field
must not redefine the standard version 1 computation, pricing, completion, or
check semantics.

---

## 16. Minimum conformance cases

An implementation should test at least these cases against its offering
validator, pricing arithmetic, acceptance state machine, runtime integration,
completion validator, settlement logic, and independent check:

```text
the exact service, service version, and pricing-model identifiers;
rejection of a fixed price, wrong pricing model, and provider checkPrice;
minimumPrice at 1 and UINT64_MAX, and rejection of 0 and overflow;
factor numerator at 0 and UINT64_MAX;
factor denominator at 1 and UINT64_MAX, and rejection of 0;
exact ceiling division where the product divides evenly and has a remainder;
arbitrary-precision products larger than uint64;
advertised maximum-price overflow rejected with the offering;
language identifiers beginning with a letter and digit;
allowed full stop, hyphen, and underscore after the first character;
rejection of uppercase, non-ASCII, whitespace, and punctuation in language;
byte-for-byte languageVersion comparison;
empty, boundary-size, and oversized UTF-8 source;
invalid UTF-8 rejected without replacement;
runtime-pair match and mismatch;
requested time at both offering bounds and immediately outside each bound;
maximum-price and credit-issuer agreement and disagreement;
concurrent reservations unable to over-authorize one balance;
offering replacement immediately before acceptance;
provider rejection before acceptance without charge;
one-millisecond minimum billing for zero or sub-millisecond clock duration;
upward rounding just above an exact millisecond;
result observed strictly before, exactly at, and after the deadline;
language error during parsing, evaluation, and result conversion;
result conversion completing, throwing, and reaching the time limit;
timeLimitReached always billing requested time and maximum price;
executionError billing its elapsed time and calculated price;
result completion with an empty result string;
optional empty, absent, invalid, oversized, and malicious diagnostic text;
provider inability to start and provider crash as uncharged service failures;
malformed completion outcomes and forbidden result/diagnostic combinations;
completion billed below 1, above the limit, and inconsistent with timeout;
completion price mismatch and price above the authorization;
complete record settlement releasing unused authorization;
record loss or truncation producing no requester charge;
late runtime activity unable to change completion or add a charge;
no automatic retry after any accepted execution;
check pass for equal result bytes;
check fail for unequal result bytes with prior determinism;
check inconclusive for nondeterminism, error, timeout, unavailable runtime,
    or incomplete re-execution;
trust updates never automatically modifying settled credits;
and plaintext transport versus optional application-layer encryption.
```

The pricing examples from `Computation.md` must produce:

```text
minimumPrice = 1
executionTimeFactor = 1 / 1000

requested maximum 60_000 ms  -> maximum price 60
billed duration 1 ms         -> final price 1
billed duration 1_201 ms     -> final price 2
time limit at 60_000 ms      -> final price 60 and timeLimitReached
```
