# Board pseudocode

This document translates the normative Board contract in
[`Board.md`](../Board.md) into implementation-neutral pseudocode. The
specification remains authoritative. Names such as `Map`, `Set`, `Registry`,
and callbacks describe responsibilities, not required classes or APIs.

Board JSON, service definitions, pricing data, and descriptive metadata are
untrusted input. JSON integers below are mathematical integers; an
implementation must not first round them through a binary floating-point type.

The Board layer does not define a peer protocol for `board.get`, `service.get`,
or invocation. Calls such as `remote.getBoard` and
`remote.getServiceDefinition` stand for operations supplied by another layer.

---

## 1. Constants, policies, and data structures

```text
BOARD_VERSION            = 1
UINT64_MAX               = 18_446_744_073_709_551_615

InvalidOfferingPolicy:
    REJECT_BOARD
    QUARANTINE_OFFERING

ResourceLimits:
    maximumBoardBytes            positive integer
    maximumJsonDepth             positive integer
    maximumJsonNodes             positive integer
    maximumArrayElements         positive integer
    maximumStringBytes           positive integer

BoardReaderPolicy:
    resourceLimits               ResourceLimits
    invalidOfferingPolicy       InvalidOfferingPolicy
    preserveUnknownFields       boolean

ImplementationSuggestion:
    name                         nonempty string
    version                      string or NONE
    uri                          string or NONE
    description                  string or NONE
    unknownFields                JSON object

Offering:
    direction                    PROVIDED | WANTED
    id                           nonempty string
    service                      nonempty string
    serviceVersion               positive integer
    description                  nonempty string
    creditIssuer                 canonical 32-byte CR2SE ID
    creditIssuerText             original textual CR2SE ID

    fixedPrice                   uint64 or NONE
    pricing                      JSON object or NONE
    pricingModel                 nonempty string or NONE
    pricingIsUnderstood          boolean

    checkPrice                   uint64 or NONE
    info                         JSON object or NONE
    preconditions                list<string>
    implementationSuggestions    list<ImplementationSuggestion>
    unknownFields                JSON object
    source                       original JSON object

ValidatedBoard:
    version                      BOARD_VERSION
    providedServices             list<Offering>
    wantedServices              list<Offering>
    offeringsById               Map<string, Offering>
    rejectedOfferings           list<OfferingError>
    unknownFields                JSON object
    source                       original JSON object

UnsupportedBoard:
    version                      nonnegative integer
    source                       original JSON object

OfferingError:
    direction                    PROVIDED | WANTED
    arrayIndex                   nonnegative integer
    offeringId                   string or NONE
    reason                       diagnostic value

BoardSnapshot:
    publisherId                  canonical 32-byte CR2SE ID
    board                        ValidatedBoard | UnsupportedBoard
    retrievedAt                  local time value
    retrievalContext            implementation-defined value

PricingModelRegistry:
    Map<model string, PricingModel>

PricingModel:
    validateOfferingTerms(service, serviceVersion, completeOfferingObject)
    calculatePrice(offering, validatedInvocationInput) -> exact integer

PreconditionRegistry:
    Map<precondition string, PreconditionHandler>
```

Resource-limit values, cache lifetime, offering selection, and the choice to
reject a whole Board or quarantine malformed offerings are local policy. The
version 1 specification intentionally does not choose them.

Offering IDs are unique across both arrays. Therefore `offeringsById` can serve
both `service.get` and invocation lookup without a direction argument.

---

## 2. Bounded JSON decoding

```text
function decodeBoardJson(encodedBytes, policy, pricingRegistry):
    if length(encodedBytes) > policy.resourceLimits.maximumBoardBytes:
        raise BoardResourceLimit("Board byte limit exceeded")

    value = parseJsonWithLimits(
        encodedBytes,
        maximumDepth = policy.resourceLimits.maximumJsonDepth,
        maximumNodes = policy.resourceLimits.maximumJsonNodes,
        maximumArrayElements = policy.resourceLimits.maximumArrayElements,
        maximumStringBytes = policy.resourceLimits.maximumStringBytes,
        requireValidUtf8 = true,
        retainExactIntegerTokens = true
    )

    return validateBoardValue(value, policy, pricingRegistry)
```

Limits must be enforced while parsing, before uncontrolled allocation. The
handling of duplicate member names inside one JSON object is a JSON-interface
policy because version 1 does not assign them Board semantics. It must be
deterministic and must not let validation inspect one value while later use
observes another.

---

## 3. Primitive validators

```text
function requireObject(value, fieldName):
    if JSON type of value is not object:
        raise ValidationError(fieldName + " must be an object")
    return value


function requireArrayMember(object, fieldName):
    if object has no member fieldName:
        raise ValidationError(fieldName + " is required")

    value = object[fieldName]
    if JSON type of value is not array:
        raise ValidationError(fieldName + " must be an array")
    return value


function requireStringMember(object, fieldName, nonempty):
    if object has no member fieldName:
        raise ValidationError(fieldName + " is required")

    value = object[fieldName]
    if JSON type of value is not string:
        raise ValidationError(fieldName + " must be a string")

    if nonempty and byteLengthUtf8(value) == 0:
        raise ValidationError(fieldName + " must not be empty")
    return value


function optionalStringMember(object, fieldName):
    if object has no member fieldName:
        return NONE

    value = object[fieldName]
    if JSON type of value is not string:
        raise ValidationError(fieldName + " must be a string")
    return value


function requireExactNonnegativeIntegerMember(object, fieldName):
    if object has no member fieldName:
        raise ValidationError(fieldName + " is required")

    value = object[fieldName]
    if JSON type of value is not number:
        raise ValidationError(fieldName + " must be a number")
    if value is not an exact integer or value < 0:
        raise ValidationError(fieldName + " must be an unsigned integer")
    return value


function requirePositiveIntegerMember(object, fieldName):
    value = requireExactNonnegativeIntegerMember(object, fieldName)
    if value == 0:
        raise ValidationError(fieldName + " must be greater than zero")
    return value


function requireCreditAmountMember(object, fieldName):
    value = requirePositiveIntegerMember(object, fieldName)
    if value > UINT64_MAX:
        raise ValidationError(fieldName + " exceeds uint64")
    return value


function optionalCreditAmountMember(object, fieldName):
    if object has no member fieldName:
        return NONE
    return requireCreditAmountMember(object, fieldName)


function parseCreditIssuer(object):
    text = requireStringMember(object, "creditIssuer", nonempty = true)

    // Identity.md requires the textual form:
    //     cr2se:<unpadded RFC 4648 Base32 encoding of exactly 32 bytes>
    // The prefix is required, whitespace and padding are forbidden, and
    // Base32 letters are accepted without regard to ASCII letter case.
    id = Identity.parseTextualCr2seId(text)
    if id is ERROR:
        raise ValidationError("invalid creditIssuer")

    return {canonicalId: id.bytes, originalText: text}
```

JSON booleans and strings must not be accepted as integers even in languages
that normally coerce them. Values larger than a native integer type must be
range-checked with an exact parser or big integer.

---

## 4. Board version and top-level validation

```text
function validateBoardValue(value, policy, pricingRegistry):
    object = requireObject(value, "Board")
    version = requireExactNonnegativeIntegerMember(object, "version")

    if version != BOARD_VERSION:
        // Do not apply version 1 field meanings to another version.
        return UnsupportedBoard {version: version, source: object}

    providedValues = requireArrayMember(object, "providedServices")
    wantedValues = requireArrayMember(object, "wantedServices")

    locations = collectOfferingLocations(providedValues, wantedValues)
    duplicateIds = findDuplicateCandidateIds(locations)
    acceptedProvided = empty list
    acceptedWanted = empty list
    rejected = empty list

    for each location in locations:
        try:
            candidateId = candidateOfferingId(location.value)
            if candidateId != NONE and candidateId in duplicateIds:
                raise ValidationError("offering ID is not unique in Board")

            offering = validateOffering(
                location.value,
                location.direction,
                pricingRegistry,
                policy.preserveUnknownFields
            )

            if offering.direction == PROVIDED:
                append offering to acceptedProvided
            else:
                append offering to acceptedWanted

        catch ValidationError as error:
            append OfferingError {
                direction: location.direction,
                arrayIndex: location.arrayIndex,
                offeringId: candidateOfferingId(location.value),
                reason: error
            } to rejected

    if not isEmpty(rejected)
       and policy.invalidOfferingPolicy == REJECT_BOARD:
        raise InvalidBoard(rejected)

    byId = new empty Map
    for each offering in acceptedProvided followed by acceptedWanted:
        assert not byId.contains(offering.id)
        byId[offering.id] = offering

    return ValidatedBoard {
        version: BOARD_VERSION,
        providedServices: acceptedProvided,
        wantedServices: acceptedWanted,
        offeringsById: byId,
        rejectedOfferings: rejected,
        unknownFields: copyUnknownMembersIfRequested(
            object,
            {"version", "providedServices", "wantedServices"},
            policy.preserveUnknownFields
        ),
        source: object
    }
```

`QUARANTINE_OFFERING` implements the permission to reject one malformed entry
without hiding unrelated valid offerings. Applications must be told that
rejected entries existed and must never receive them as valid offerings. A
strict implementation chooses `REJECT_BOARD`.

```text
function collectOfferingLocations(providedValues, wantedValues):
    result = empty list

    for index from 0 to length(providedValues) - 1:
        append {
            direction: PROVIDED,
            arrayIndex: index,
            value: providedValues[index]
        } to result

    for index from 0 to length(wantedValues) - 1:
        append {
            direction: WANTED,
            arrayIndex: index,
            value: wantedValues[index]
        } to result

    return result


function candidateOfferingId(value):
    if JSON type of value is object
       and value has member "id"
       and JSON type of value["id"] is string
       and byteLengthUtf8(value["id"]) > 0:
        return value["id"]
    return NONE


function findDuplicateCandidateIds(locations):
    counts = new Map<string, integer> with default 0

    for each location in locations:
        id = candidateOfferingId(location.value)
        if id != NONE:
            counts[id] = counts[id] + 1

    result = empty Set
    for each (id, count) in counts:
        if count > 1:
            add id to result
    return result
```

All entries sharing a duplicate ID are rejected in tolerant mode. Selecting
the first or last duplicate would make lookup and invocation ambiguous.

---

## 5. Offering validation

```text
function validateOffering(value, direction, pricingRegistry, preserveUnknown):
    object = requireObject(value, "offering")

    id = requireStringMember(object, "id", nonempty = true)
    service = requireStringMember(object, "service", nonempty = true)
    serviceVersion = requirePositiveIntegerMember(object, "serviceVersion")
    description = requireStringMember(object, "description", nonempty = true)
    issuer = parseCreditIssuer(object)

    if object has member "input"
       or object has member "output"
       or object has member "check":
        raise ValidationError("service schemas must not occur on a Board")

    hasFixedPrice = object has member "price"
    hasVariablePricing = object has member "pricing"
    if hasFixedPrice == hasVariablePricing:
        raise ValidationError("exactly one of price or pricing is required")

    checkPrice = optionalCreditAmountMember(object, "checkPrice")
    info = validateOptionalInfo(object)
    preconditions = validateOptionalPreconditions(object)
    suggestions = validateOptionalImplementationSuggestions(
        object, preserveUnknown
    )

    if hasFixedPrice:
        fixedPrice = requireCreditAmountMember(object, "price")
        pricing = NONE
        pricingModel = NONE
        pricingIsUnderstood = true
    else:
        fixedPrice = NONE
        pricingResult = validatePricing(
            object["pricing"], service, serviceVersion, object, pricingRegistry
        )
        pricing = object["pricing"]
        pricingModel = pricingResult.model
        pricingIsUnderstood = pricingResult.understood

    knownNames = {
        "id", "service", "serviceVersion", "description", "creditIssuer",
        "price", "pricing", "checkPrice", "info", "preconditions",
        "implementationSuggestions"
    }

    return Offering {
        direction: direction,
        id: id,
        service: service,
        serviceVersion: serviceVersion,
        description: description,
        creditIssuer: issuer.canonicalId,
        creditIssuerText: issuer.originalText,
        fixedPrice: fixedPrice,
        pricing: pricing,
        pricingModel: pricingModel,
        pricingIsUnderstood: pricingIsUnderstood,
        checkPrice: checkPrice,
        info: info,
        preconditions: preconditions,
        implementationSuggestions: suggestions,
        unknownFields: copyUnknownMembersIfRequested(
            object, knownNames, preserveUnknown
        ),
        source: object
    }
```

The `cr2se.` service prefix is reserved, but an unknown service using it does
not by itself invalidate the Board. Service support is separate from
structural validity.

---

## 6. Variable pricing

```text
function validatePricing(
    value,
    service,
    serviceVersion,
    completeOfferingObject,
    pricingRegistry
):
    pricing = requireObject(value, "pricing")
    model = requireStringMember(pricing, "model", nonempty = true)

    handler = pricingRegistry.get(model)
    if handler == NONE:
        // Preserve and display it, but do not calculate, accept, or invoke it.
        return {model: model, understood: false}

    // The model's service specification owns its required pricing and info
    // fields, exact numeric rules, limits and relations, required checkPrice
    // and preconditions, and permitted service/version association.
    handler.validateOfferingTerms(
        service, serviceVersion, completeOfferingObject
    )
    return {model: model, understood: true}


function determineMainPrice(offering, validatedInvocationInput, registry):
    if offering.fixedPrice != NONE:
        return offering.fixedPrice

    if not offering.pricingIsUnderstood:
        raise OfferingNotUsable("unknown pricing model")

    handler = registry.get(offering.pricingModel)
    if handler == NONE:
        raise OfferingNotUsable("pricing model no longer available")

    price = handler.calculatePrice(offering, validatedInvocationInput)
    if price is not an exact integer or price < 1 or price > UINT64_MAX:
        raise InvalidCalculatedPrice
    return price


function determineCheckPrice(offering):
    if offering.checkPrice == NONE:
        return INCLUDED_IN_MAIN_SERVICE_PRICE
    return offering.checkPrice
```

Pricing handlers use the exact arithmetic and rounding specified by their
service. The final price and `creditIssuer` must be known and accepted before
chargeable execution or acceptance of a large streamed body begins.

An unknown model affects only its offering's automatic usability. It neither
invalidates unrelated offerings nor prevents this offering being displayed.

---

## 7. Optional standard fields

```text
function validateOptionalInfo(object):
    if object has no member "info":
        return NONE
    return requireObject(object["info"], "info")


function validateOptionalPreconditions(object):
    if object has no member "preconditions":
        return empty list

    values = object["preconditions"]
    if JSON type of values is not array:
        raise ValidationError("preconditions must be an array")

    result = empty list
    for each value in values:
        if JSON type of value is not string:
            raise ValidationError("each precondition must be a string")
        append value to result
    return result


function validateOptionalImplementationSuggestions(object, preserveUnknown):
    if object has no member "implementationSuggestions":
        return empty list

    values = object["implementationSuggestions"]
    if JSON type of values is not array:
        raise ValidationError("implementationSuggestions must be an array")

    result = empty list
    for each value in values:
        suggestion = requireObject(value, "implementation suggestion")
        name = requireStringMember(suggestion, "name", nonempty = true)

        append ImplementationSuggestion {
            name: name,
            version: optionalStringMember(suggestion, "version"),
            uri: optionalStringMember(suggestion, "uri"),
            description: optionalStringMember(suggestion, "description"),
            unknownFields: copyUnknownMembersIfRequested(
                suggestion,
                {"name", "version", "uri", "description"},
                preserveUnknown
            )
        } to result
    return result
```

Version 1 does not say that precondition identifiers or optional suggestion
strings must be nonempty. Such values may still be unknown or unusable.
Implementations must not infer behavior from descriptions, arbitrary `info`
members, unknown fields, or array position.

Reading `implementationSuggestions` must never automatically download,
install, or execute anything named by them.

---

## 8. Discoverability, usability, and preconditions

Structural validity, discoverability, and local usability are distinct.

```text
function assessOffering(offering, capabilities):
    result = {
        structurallyValid: true,
        discoverable: true,
        canAutomaticallyInvoke: true,
        reasons: empty list
    }

    if not capabilities.understandsService(
        offering.service,
        offering.serviceVersion
    ):
        result.canAutomaticallyInvoke = false
        append "unknown service or version" to result.reasons

    if offering.pricing != NONE and not offering.pricingIsUnderstood:
        result.canAutomaticallyInvoke = false
        append "unknown pricing model" to result.reasons

    for each precondition in offering.preconditions:
        if not capabilities.preconditionRegistry.contains(precondition):
            result.canAutomaticallyInvoke = false
            append {"unknown precondition", precondition} to result.reasons

    return result


function satisfyPreconditions(offering, context, registry):
    for each name in offering.preconditions:
        handler = registry.get(name)
        if handler == NONE:
            raise OfferingNotUsable({"unknown precondition", name})

        outcome = handler.verify(context)
        if outcome != SATISFIED:
            raise PreconditionsNotSatisfied({name, outcome})

    return SATISFIED
```

All listed preconditions are required unless the specification defining one
explicitly supplies different combination semantics. Those semantics belong
inside its handler. An unknown precondition is never treated as satisfied.

An unknown service or an unknown type in its separately retrieved definition
does not invalidate the Board entry. An application that understands the
extension may still handle it.

---

## 9. Board publication and atomic state

```text
PublishedBoardState:
    lock                         Lock
    currentBoard                 ValidatedBoard
    definitionsByOfferingId      Map<string, ServiceDefinition>


function prepareBoardForPublication(
    encodedBoard,
    definitionsById,
    strictPolicy,
    pricingRegistry,
    definitionValidator
):
    require strictPolicy.invalidOfferingPolicy == REJECT_BOARD

    board = decodeBoardJson(encodedBoard, strictPolicy, pricingRegistry)
    if board is UnsupportedBoard:
        raise UnsupportedBoardVersion(board.version)

    for each offering in allOfferings(board):
        if offering.pricing != NONE and not offering.pricingIsUnderstood:
            raise PublicationError(
                {offering.id, "publisher cannot calculate its pricing model"}
            )

        definition = definitionsById.get(offering.id)
        if definition == NONE:
            raise PublicationError(
                {offering.id, "service definition is not retrievable"}
            )

        validateDefinitionForOffering(
            offering, definition, definitionValidator
        )

    groups = group allOfferings(board) by (service, serviceVersion)
    for each group in groups:
        groupDefinitions = definitionsById entries for group offering IDs
        if not definitionValidator.haveSameLogicalContract(groupDefinitions):
            raise PublicationError(
                "same service and version have different logical contracts"
            )

    return {
        board: board,
        definitionsByOfferingId: definitionsById restricted to board IDs
    }


function publishPreparedBoard(state, prepared):
    with state.lock:
        // Readers observe matching Board and definition snapshots together.
        state.currentBoard = prepared.board
        state.definitionsByOfferingId = prepared.definitionsByOfferingId


function handleLocalBoardGet(state):
    with state.lock:
        return state.currentBoard.source


function handleLocalServiceGet(state, offeringId):
    with state.lock:
        if not state.currentBoard.offeringsById.contains(offeringId):
            raise ServiceNotFound

        definition = state.definitionsByOfferingId.get(offeringId)
        if definition == NONE:
            raise InternalError
        return definition
```

A new snapshot removes every old offering absent from it; no deletion record
is required. Removal prevents new selection but does not cancel an accepted
ongoing service or shorten an active lease.

Keeping an ID stable is recommended only while the same logical offering
continues. A publisher should use a new ID after a substantial change, but
version 1 does not make that recommendation a validation rule.

---

## 10. Retrieving and caching a remote Board

```text
function refreshRemoteBoard(
    remote,
    authenticatedPublisherId,
    readerPolicy,
    pricingRegistry,
    cache
):
    encodedBoard = remote.getBoard()
    board = decodeBoardJson(encodedBoard, readerPolicy, pricingRegistry)

    snapshot = BoardSnapshot {
        publisherId: authenticatedPublisherId,
        board: board,
        retrievedAt: currentLocalTime(),
        retrievalContext: remote.context()
    }

    cache.replaceRelevantSnapshotAtomically(snapshot)
    return snapshot


function getOffering(snapshot, offeringId):
    if snapshot.board is UnsupportedBoard:
        raise UnsupportedBoardVersion(snapshot.board.version)

    offering = snapshot.board.offeringsById.get(offeringId)
    if offering == NONE:
        raise OfferingNotFound
    return offering
```

Cache refresh interval, expiry, and storage key are implementation-dependent.
A cached Board must never be assumed permanent. The Board belongs to the
publisher identity rather than its TCP address or process; retrieval context
may still be retained for refresh and diagnostics.

Unknown top-level, offering, and `info` fields are ignored for version 1
semantics. They may be preserved when Board JSON is passed to applications.

---

## 11. Service-definition consistency

```text
function retrieveDefinitionForOffering(
    remote,
    snapshot,
    offeringId,
    definitionValidator
):
    offering = getOffering(snapshot, offeringId)
    definition = remote.getServiceDefinition(offeringId)

    try:
        validateDefinitionForOffering(
            offering, definition, definitionValidator
        )
    catch any mismatch or validation error:
        // The cached Board may be stale or the publisher inconsistent.
        raise StaleOrInconsistentDefinition

    return definition


function validateDefinitionForOffering(
    offering,
    definition,
    definitionValidator
):
    definitionValidator.validateStructure(definition)

    if definition.id != offering.id:
        raise DefinitionMismatch("id")
    if definition.service != offering.service:
        raise DefinitionMismatch("service")
    if definition.serviceVersion != offering.serviceVersion:
        raise DefinitionMismatch("serviceVersion")
    if definition.description != offering.description:
        raise DefinitionMismatch("description")

    if definition contains any of {
        "creditIssuer", "price", "pricing", "checkPrice"
    }:
        raise InvalidServiceDefinition(
            "offering-specific economic terms belong on the Board"
        )

    // Services.md validates the input, output, and mandatory check schemas,
    // including descriptions for every named nested field.
    return VALID
```

An inconsistent definition must not be used. The client should refresh the
Board and repeat selection. An unknown schema type may leave a definition
discoverable, but a client that does not understand the type must not claim it
can construct, validate, invoke, or check that contract.

---

## 12. Selection and stale-offering checks

Array order supplies no priority. Selection is an application decision.

```text
function selectOffering(board, direction, applicationPolicy, capabilities):
    if board is UnsupportedBoard:
        raise UnsupportedBoardVersion(board.version)

    if direction == PROVIDED:
        candidates = board.providedServices
    else:
        candidates = board.wantedServices

    acceptable = empty list
    for each offering in candidates:
        assessment = assessOffering(offering, capabilities)
        if applicationPolicy.accepts(offering, assessment):
            append offering to acceptable

    // Do not infer priority from position, price, issuer, or trust.
    return applicationPolicy.choose(acceptable)


function resolveCurrentInvocationOffering(
    publishedState,
    requestedOfferingId,
    requestedService,
    requestedServiceVersion
):
    with publishedState.lock:
        offering = publishedState.currentBoard.offeringsById.get(
            requestedOfferingId
        )

        if offering == NONE:
            raise ServiceNotFoundOrStaleSelection

        if offering.service != requestedService
           or offering.serviceVersion != requestedServiceVersion:
            raise StaleOrInconsistentSelection

        return offering
```

Before initial execution, the provider resolves identifiers against its current
Board, validates input against the retrieved contract, determines the exact
price, obtains price and issuer agreement, and satisfies all preconditions. If
current terms differ from a cached Board, it rejects rather than executing at
an undisclosed price.

---

## 13. Conservative wanted/provided matching

Version 1 defines no universal compatibility algorithm. This helper only
removes definitely incompatible candidates and delegates the rest.

```text
function findPossibleMatch(wanted, provided, matchingPolicy):
    require wanted.direction == WANTED
    require provided.direction == PROVIDED

    if wanted.service != provided.service:
        return NO_MATCH
    if wanted.serviceVersion != provided.serviceVersion:
        // Never silently substitute another version.
        return NO_MATCH

    wantedDefinition = matchingPolicy.getValidatedDefinition(wanted)
    providedDefinition = matchingPolicy.getValidatedDefinition(provided)

    if not matchingPolicy.logicalContractsCompatible(
        wantedDefinition, providedDefinition
    ):
        return NO_MATCH

    return matchingPolicy.evaluateTerms({
        wantedInfo: wanted.info,
        providedInfo: provided.info,
        wantedPrice: wanted.fixedPrice or wanted.pricing,
        providedPrice: provided.fixedPrice or provided.pricing,
        wantedCreditIssuer: wanted.creditIssuer,
        providedCreditIssuer: provided.creditIssuer,
        wantedCheckPrice: wanted.checkPrice,
        providedCheckPrice: provided.checkPrice,
        wantedPreconditions: wanted.preconditions,
        providedPreconditions: provided.preconditions
    })
```

Equal service identifiers alone are insufficient. Compatibility may depend on
the exact version, definitions and checks, service-specific constraints,
pricing, issuer, and preconditions.

---

## 14. Unknown-field preservation

```text
function copyUnknownMembersIfRequested(object, knownNames, enabled):
    if not enabled:
        return empty object

    result = empty object
    for each (name, value) in object:
        if name not in knownNames:
            result[name] = deepCopyJsonValue(value)
    return result
```

Preservation is optional; tolerance is mandatory. Unknown fields do not gain
Board semantics and do not invalidate an otherwise valid Board. This permits
another specification to define a top-level field such as
`identityEncryption` without requiring the Board parser to understand it.

---

## 15. Minimum conformance cases

An implementation should test at least these cases against its decoder,
validator, publication state, and selection boundary:

```text
the minimal version 1 Board with two empty arrays;
provided-only, wanted-only, and mixed Boards;
unsupported nonnegative versions not interpreted as version 1;
missing, negative, fractional, string, and boolean version values;
missing or non-array providedServices and wantedServices;
offering IDs duplicated within one array and across both arrays;
all duplicate-ID entries quarantined instead of first- or last-entry wins;
empty and non-string id, service, and description;
zero, negative, fractional, string, and very large serviceVersion;
textual CR2SE IDs with required prefix and exactly 32 decoded bytes;
case-insensitive Base32 acceptance and canonical uppercase output;
rejection of missing prefix, padding, whitespace, invalid alphabet, and wrong
    decoded length in creditIssuer;
an offering with neither price form and with both price forms;
fixed price and checkPrice at 1 and UINT64_MAX;
fixed price and checkPrice at 0, UINT64_MAX + 1, fractional, string, and
    boolean values;
pricing that is not an object or has a missing, empty, or non-string model;
known pricing models with every service-defined invalid term and relation;
unknown pricing models discoverable but not automatically usable;
calculated prices below 1, above UINT64_MAX, fractional, or overflowing;
info absent, an object, and every non-object JSON type;
preconditions absent, empty, non-string, known, and unknown;
unknown preconditions never treated as satisfied;
valid and malformed implementation suggestions;
input, output, or check embedded in a Board offering;
unknown fields at Board, offering, suggestion, pricing, and info levels;
unknown services remaining discoverable;
unknown definition types preventing unsupported automatic use;
definition id, service, version, and description mismatches;
definition retrieval for an ID removed by a concurrent Board replacement;
atomic publication of a Board and all its definitions;
removal preventing new selection without cancelling accepted ongoing work;
array reordering having no priority or semantic effect;
exact-integer parsing above the IEEE-754 safe-integer range;
invalid UTF-8, malformed JSON, and deterministic duplicate-member handling;
every configured byte, depth, node, array, and string resource boundary;
suggestions never triggering code execution or downloads;
stale cached terms causing rejection and refresh;
price and issuer agreement before chargeable work or a large body.
```
