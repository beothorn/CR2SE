# Peer Protocol encoding vectors

These vectors test the [shared binding](../README.md), not Transport's frame
authentication. They are application-record bytes placed inside DATA streams.
Whitespace in displayed hex is for readability and is not transmitted.

## Control record

The exact UTF-8 body is `{"type":"board.get"}`, with no LF or trailing spaces.
It contains 20 bytes. The complete record is:

```text
01 00000014
7b2274797065223a22626f6172642e676574227d
```

The first byte selects JSON control; the next four encode body length.
Splitting these bytes across different DATA frames must not change decoding.

## Binary body record

Body ID zero, offset zero, and data bytes `61 62 63` produce:

```text
02 0000000f
00000000
0000000000000000
616263
```

The record body has 15 bytes: four for the body ID, eight for the offset, and
three for data. The complete record has 20 bytes. It is valid only when prior
accepted metadata declares the corresponding detached value:

```json
{"$bytes":0,"length":"3"}
```

Although small values normally use inline Base64, a nonempty byte value may be
detached at any size. A sender must use a body for values larger than 4,096 bytes.
Body data before acceptance, offset one as the first chunk, a fourth data byte,
or an undeclared body ID must fail the exchange.

## Schema-bound values

| Schema type | Logical value | Exact JSON value |
|---|---|---|
| `uint32` | Maximum | `4294967295` |
| `uint64` | Maximum | `"18446744073709551615"` |
| `int64` | Minimum | `"-9223372036854775808"` |
| `bytes` | ASCII abc | `{"$base64":"YWJj"}` |
| `bytes` | Empty | `{"$base64":""}` |
| `float` | Negative zero | `{"$float":"80000000"}` |
| `double` | One | `{"$double":"3ff0000000000000"}` |

For a uint64 schema, reject JSON number `1`, strings `"01"`, `"+1"`, `"-0"`,
and `"18446744073709551616"`. Board JSON has a different, lossless numeric
document representation; this string rule applies to schema-bound values.

For a bytes schema, reject whitespace, missing required padding, or nonzero
unused bits in Base64. For example, `"YQ=="` encodes byte `61`, while `"YR=="`
is not a canonical spelling of that byte.
