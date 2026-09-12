# Services pseudocode

This document translates [`Services.md`](../Services.md) into
implementation-neutral validation and lifecycle algorithms. The specification
remains authoritative. Definitions, schemas, values, descriptions, and remote
results are untrusted.

## 1. Definitions and schemas

```text
PRIMITIVES = {bool, int32, int64, uint32, uint64, float, double, string, bytes}
STANDARD_NAMESPACE = "cr2se."

ServiceDefinition:
    id                         offering ID
    service                    nonempty UTF-8 identifier
    serviceVersion             positive integer
    description                nonempty UTF-8 string
    input                      TypeDescription
    output                     TypeDescription
    check                      CheckDefinition
```

```text
function validateDefinitionBounded(rawBytes, limits):
    require length(rawBytes) <= limits.maximumDefinitionBytes
    value = parseJsonWithExactNumbersAndLimits(rawBytes, limits)
    requireDefinitionMembers(value)
    definition = ServiceDefinition {
        id: requireNonemptyString(value.id),
        service: requireNonemptyString(value.service),
        serviceVersion: requirePositiveExactInteger(value.serviceVersion),
        description: requireNonemptyString(value.description),
        input: validateType(value.input, context = INPUT),
        output: validateType(value.output, context = OUTPUT),
        check: validateCheck(value.check)
    }
    if definition.service startsWith STANDARD_NAMESPACE:
        require standardRegistry contains exact service/version
        require definition is logically equivalent to registered contract
    else:
        requireEveryNamedFieldHasNonemptyDescription(definition)
    return definition

function validateType(schema, context, depth = 0):
    enforce depth, node, field, string, and array limits
    kind = requireString(schema.type)
    if kind in PRIMITIVES:
        reject members not allowed for that primitive
        return PrimitiveType(kind, constraints)
    if kind == "object":
        require schema.fields is an object with unique names
        for each (name, child) in schema.fields:
            require name is nonempty UTF-8
            validateType(child, context, depth + 1)
        validate optional-field declarations refer exactly to known fields
        return ObjectType(...)
    if kind == "array":
        return ArrayType(validateType(schema.items, context, depth + 1), bounds)
    raise UnsupportedType
```

Unknown schema extensions may be preserved but must not change known semantics.
An unsupported required extension makes the definition unusable.

## 2. Logical value validation

```text
function validateValue(value, schema, limits, path = "$", depth = 0):
    enforce aggregate byte/node/depth limits
    switch schema.kind:
      bool:   require logical boolean
      int32:  require exact integer in -2^31 .. 2^31-1
      int64:  require exact integer in -2^63 .. 2^63-1
      uint32: require exact integer in 0 .. 2^32-1
      uint64: require exact integer in 0 .. 2^64-1
      float:  require finite representable IEEE-754 binary32 logical value
      double: require finite representable IEEE-754 binary64 logical value
      string: require valid UTF-8 and applicable byte limits
      bytes:  require byte sequence and applicable byte limits
      array:
        require array and length within schema/local bounds
        return map each element through validateValue
      object:
        require object with unique field names
        require every non-optional schema field is present
        reject unknown fields unless schema extension rules allow them
        validate each present field recursively
    return value
```

Integer values must not pass through floating point. A binding or wire encoding
may differ from JSON but must preserve the same logical values and ranges.

## 3. Offering consistency and agreement

```text
function requireDefinitionMatchesOffering(definition, offering):
    require definition.id == offering.id
    require definition.service == offering.service
    require definition.serviceVersion == offering.serviceVersion
    require definition.description == offering.description
    return definition

function prepareInvocation(requester, offering, definition, rawInput,
                           requesterMaximumPrice):
    requireDefinitionMatchesOffering(definition, offering)
    input = validateValue(rawInput, definition.input, localLimits)
    require all offering preconditions are understood and satisfied
    priceAuthorization = pricingRegistry[offering.pricing model or FIXED]
        .authorize(offering, input)
    require priceAuthorization.maximum <= requesterMaximumPrice
    reservation = Ledger.reserveCharge(
        requester, offering.creditIssuer, priceAuthorization.maximum)
    return Invocation {uniqueId, requester, immutable offering snapshot,
        definition, input, priceAuthorization, reservation, state: ACCEPTED}
```

Selection uses a current Board snapshot. If terms change before acceptance,
the requester must reselect and explicitly accept the new price; providers do
not silently substitute offerings.

## 4. Execution and settlement

```text
function executeProviderInvocation(invocation, implementation):
    require invocation.state == ACCEPTED
    try:
        rawOutput = implementation.perform(invocation.input,
                                            invocation.priceAuthorization)
        output = validateValue(rawOutput, invocation.definition.output, limits)
        finalPrice = pricingRegistry.finalize(invocation, rawOutput)
        require 1 <= finalPrice <= invocation.priceAuthorization.maximum
        atomically:
            Ledger.commitExact(invocation.reservation, finalPrice)
            invocation.state = SUCCEEDED
            persist completion for replay safety
        return {output, price: finalPrice}
    catch failure:
        atomically:
            Ledger.releaseReservation(invocation.reservation)
            invocation.state = FAILED
        return ServiceFailure(boundedDiagnostic(failure))
```

Only a complete valid success is charged. Invalid input, refusal, timeout,
cancellation, malformed or incomplete output, and provider failure are not
successful service performance. Transport retry must not execute or charge an
accepted invocation twice.

## 5. Checks

```text
function runCheck(invocation, successfulOutput):
    checkInput = constructExactlyAsDefinitionRequires(
        invocation.input, successfulOutput, invocation.agreement)
    if check cannot run because required data/resource is unavailable:
        return INCONCLUSIVE
    if check is local:
        candidate = localCheck(checkInput)
    else:
        checkPrice = requirePreviouslyAgreedCheckPrice(invocation.offering)
        checkReservation = Ledger.reserveCharge(..., checkPrice)
        candidate = invokeIndependentChecker(checkInput)
        settle checkReservation only on complete check success
    validateValue(candidate, invocation.definition.check.output, limits)
    require candidate outcome in {PASS, FAIL, INCONCLUSIVE}
    return candidate
```

A check evaluates evidence; it does not reverse a charge or globally settle a
dispute. Requesters calculate local checks themselves and use outcomes as input
to local trust. Standard service handlers own their normative pricing,
validation, and check algorithms; custom definitions cannot redefine standard
contracts.
