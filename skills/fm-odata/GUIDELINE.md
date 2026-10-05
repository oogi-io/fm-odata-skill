# FileMaker OData: behaviours observed in production

Point your AI here and it'll be able to work with OData.

Scope: two FileMaker Server hosts, called host A and host B. Host B reports version 22.0 (read 2026-09-30);
host A's version is not pinned yet. Every behaviour states where and when it was observed. The Evidence
table at the end lists, per claim, the observation, any independent corroboration, and what Claris's own
OData guide says. One claim (the `ID` field name) rests on one host and says so; three earlier single-host
claims were retested on the second host on 2026-09-29 and retired. The Verify section shows how to test each one
on your own server in one request.

## Core concepts

### Entity set = table occurrence

An OData entity set maps to a table occurrence in the relationship graph, not to a layout and not to a base
table. A base table occurrence usually carries the table's name (`INV__Invoice`); a prefixed occurrence
(`CUST_INV__Invoice__open`) is the same table seen from another context. A prefixed occurrence is not a
filtered view: it returns the table's rows unless you filter.

An occurrence whose name contains `~` cannot be addressed in the URL path at all, as an entity set or as a
navigation segment. The server answers -1002 "syntax error in URL at:" followed by the text after the `~`:
as an entity set whether the `~` is sent raw, as `%7E` or inside double quotes, and as a navigation segment
raw or as `%7E`. A `~` in a query option value is unaffected (see Query string encoding). Reach the base table through another occurrence, or rename it.

Observed: host B, 2026-09-30.

### Filter on the server

Ask for the rows you need with `$filter`. Fetching a table and filtering client-side costs the server, the
network and, past 10,000 rows, the correctness of the answer (see Paging).

```
GET /fmi/odata/v4/{db}/INV__Invoice?$filter=Status eq 1
```

## Date and timestamp literals

Observed: host A, 2026-09-28; host B, 2026-09-29 (timestamps) and 2026 (dates, day not recorded).

Unquoted ISO 8601 literals work. A quoted literal returns no error and no usable data.

```
$filter=DateCreated ge 2020-01-01          rows
$filter=DateCreated ge '2020-01-01'        zero rows (host A); nulls (host B, as recorded)
```

On both hosts, a timestamp literal without a time zone (`2026-09-27T00:00:00`) failed with -1002 at `T00`,
`2026-09-27T00:00:00Z` returned rows, and the quoted form returned zero rows. An offset form was not tried. Claris: "Date, time, and timestamp
formats conform to ISO 8601. Time zone offsets are relative to the time zone of the server."

## Query string encoding

Observed: host A, 2026-09-28; host B, 2026-09-25 and 2026-09-29.

| Character | Rule | What happens otherwise |
|---|---|---|
| `$` in `$filter`, `$select`, `$top`, `$orderby`, `$count` | stays literal | `%24top` is ignored and the whole table returns: host A, 1,633-row table, all rows; host B, 3,306-row table, all rows |
| space | `%20` | `+` is refused: -1002 "syntax error in URL at: '+'" |
| `:` in a timestamp literal | stays literal | `%3A` is refused: -1002 at `T00%3A00%3A00Z` |
| `,` in a `$select` list | stays literal | `%2C` is refused: -1002 at `%2CCallDuration` |
| `(`, `)`, `'`, `"` | stay literal | they are OData syntax; `%28` and `%22` were accepted on host A, so encoding them is harmless, decoding them is not required |

`URLSearchParams` breaks the first two rules at once. `curl --data-urlencode` keeps the option name literal
and breaks the second: on host A, 2026-09-29, `--data-urlencode '$filter="ID" gt 0'` was sent as
`$filter=%22ID%22+gt+0` and answered -1002 at `+`. An
open-source FileMaker OData client library on GitHub rewrites its own encoded query string afterwards,
turning `%24` back into `$` and `+` into `%20`, which is the same conclusion reached the hard way.

A function that builds a correct URL, Python standard library only:

```python
from urllib.parse import quote

def odata_url(base, entity_set, **options):
    """base: https://host.example/fmi/odata/v4/DB ; options: filter='...', select='...', top=5"""
    def enc(value):
        return quote(str(value), safe="(),'\":=/").replace("~", "%7E")
    query = "&".join(f"${key}={enc(value)}" for key, value in options.items())
    return f"{base}/{quote(entity_set)}" + (f"?{query}" if query else "")
```

`quote` leaves `$` alone because it is only applied to values, encodes a space as `%20`, and keeps the OData
syntax characters listed above including `:` and `,`. `~` is sent as `%7E`, and that is a rule: both hosts
accepted it raw on 2026-09-29, but on 2026-10-05 host B refused a raw `~` in a `$select` field name with -1002
at the text after it, while `%7E` and the double-quoted name both returned the field. That holds for query
option values only: a `~` in a table occurrence name in the path failed in every form tried (see Entity set =
table occurrence).

## Field names and the entity key

Observed: host A, 2026-09-28.

A field named `ID` fails unquoted and works double-quoted, in every option:

```
$select=ID                    -1002 "parse failure in URL"
$select="ID"                  200, the column is in the rows
$orderby="ID" desc            200
$filter="ID" gt 0             200
```

Claris: "Enclose field names that include special characters, such as spaces or underscores, in
double-quotation marks." Unquoted names with underscores also worked on host A, and quoting a plain name is
harmless, so quote any name you are unsure of. Whether `ID` fails because it is a reserved word is an
inference; the observation is that unquoted fails and quoted works.

The entity key in `Table(key)` is FileMaker's record id, the number that `@editLink` and `@id` carry. It is
not the table's `ID` field: `Table(<ID value>)` answered -1023 "record not found" and `Table('<ID value>')`
answered 8309 "incompatible data types". To address one record, filter on the field (`$filter="ID" eq 5`)
or use the row's `@editLink`.

## Paging

Observed: host A, 2026-09-28 (a 22,668-row table, two pages followed); host B, 2026-09-25 (three tables) and
2026-10-05 (the timestamp case below).

A response holds at most 10,000 rows. Claris: "A maximum of 10,000 records are returned at a time. If the
total records in a request exceeds 10,000, the nextLink value is also returned providing the next set of
records." What the guide does not say: the key is `@nextLink`, not the standard `@odata.nextLink`, and it
carries `$skiptoken=s10000t0`. Code that reads one response, or looks for the standard key, reports a
truncated table as complete.

The server breaks its own continuation when the `$filter` holds a timestamp. On host B, 2026-10-05, a
filter `CreatedAt ge 2025-10-05T00:00:00Z` over 11,017 rows returned 10,000 rows and an `@nextLink` in
which the timestamp read `2025-10-05T00%3A00%3A00Z`; following the link as given answered -1002 "syntax
error in URL at: 'T00%3A00%3A00Z'", the same refusal as a hand-written `%3A` (see encoding). With `%3A`
put back to `:` the link returned the remaining 1,017 rows. The loop below does that.

`$top` is not a way to ask for everything: `$top=10000` on the same filter returned 10,000 rows and no
`@nextLink`, so the table read as complete. Leave `$top` off, or compare with `/$count` (11,017 here).

```python
url = odata_url(base, "INV__Invoice", select='"ID"')
while url:
    data = get(url)                       # your HTTP call, returning the parsed JSON
    yield from data.get("value", [])
    url = data.get("@nextLink") or data.get("@odata.nextLink")
    if url:
        url = url.replace("%3A", ":").replace("%3a", ":")   # the server's own link encodes the colon
```

## Annotations

Observed: host A, 2026-09-28; `@nextLink` also host B.

FileMaker omits the `odata.` segment in every annotation seen: `@context`, `@count`, `@nextLink`, `@id`,
`@editLink`. Code that looks for `@odata.count` or `@odata.nextLink` finds nothing.

## $count

Observed: host A, 2026-09-28; host B, 2026-09-29.

`$count=true&$top=1` returned one row and `@count` on both hosts (22,668 on host A, 3,306 on host B): the
count ignores `$top`, the rows honour it, as Claris documents. An earlier 400 recorded on host B in 2026 did
not reproduce; it predates the encoding rules above and was most likely one of them.

## $orderby

Observed: host A, 2026-09-28; host B, 2026-09-29.

Works on both hosts, with and without double quotes around a name with underscores. An earlier -1002
recorded on host B in 2026 did not reproduce and predates the encoding rules. Claris: `$orderby` "doesn't
support OData built-in functions", and the quoting sentence above applies.

## Field names with a dot

Observed: host B, 2026-09-29.

A field whose name contains a dot works in `$filter` and in `$select`, quoted or not, when the literal
matches the field's type: `_trigger.names eq 1` on a numeric field returned its rows with `$select` honoured.
Earlier records from the same host that said "zero rows" for such fields predate the literal rules above; a
quoted literal against a typed field returns zero rows on both hosts, and that is the likelier explanation.

## What works, what is host-dependent

| Option | Status |
|---|---|
| `$filter` | works, with the literal and encoding rules above |
| `$select` | works; quote names that fail |
| `$top`, `$skip` | work |
| `$orderby` | works on both hosts; quote names you are unsure of |
| `$count` | works on both hosts; `@count`, ignores `$top` |
| POST, PATCH, DELETE | exist; see Writes |
| Script endpoint | `POST /fmi/odata/v4/{db}/Script.{scriptName}` with `{"scriptParameterValue": "..."}` |
| `$search`, lambda operators `any`/`all` | unsupported, per Claris |

## Writes

The endpoints are the standard ones:

```
POST  /fmi/odata/v4/{db}/{entitySet}                 body: { "Field": "value" }
PATCH /fmi/odata/v4/{db}/{entitySet}(<record id>)    body: { "Field": "newValue" }
```

A direct create or update is the simpler route when the change is a plain field write, and FileMaker still
runs auto-enter calculations on it. Whether an agent may write at all is your organisation's rule; this
guideline's default is reads.

## Related records

Filter on the foreign key that points at the parent, then make a second, filtered request for the related
rows you need. `$orderby` sorts on the server.

A second route is navigation: `Parent(<record id>)/<RelatedOccurrence>`, with the record id from the
parent's `@editLink`, returns the related records as the relationship graph defines them, matched by
FileMaker's own rules, which is the set a portal on that relationship shows. `$select` works on it. That
makes it the one read-only way to test a relationship's predicates from outside FileMaker: compare the
navigation count with a direct filter on the foreign key.

Observed: host B, 2026-09-30.

## Verify on your host

One request per claim. Run each against a table you know.

| Claim | Request | What confirms it |
|---|---|---|
| `$` must stay literal | `?%24top=3` then `?$top=3` | the first returns more than three rows |
| space must be `%20` | `?$filter=a+eq+1` then `?$filter=a%20eq%201` | the first answers -1002 |
| quoted date fails silently | `?$filter=D ge '2020-01-01'` then `?$filter=D ge 2020-01-01` | the first returns nothing usable |
| quote a failing name | `?$select=ID` then `?$select="ID"` | the first answers -1002, the second 200 |
| entity key is the record id | read `@editLink` from a row, then `Table(<that number>)` | 200 with the record |
| 10,000-row stop | a `$select` of one field on a table over 10,000 rows, no `$top` | 10,000 rows and `@nextLink` |
| `@nextLink` with a timestamp filter | the same, with `$filter=<timestamp field> ge <ISO timestamp with Z>`; follow `@nextLink` as given, then with `%3A` replaced by `:` | the first answers -1002 at `%3A`, the second returns the next page |
| `$count` | `?$count=true&$top=1` | `@count` in the response |
| `$orderby` | `?$orderby="F" desc&$top=1` and unquoted | 200 both ways |
| navigation follows the relationship | `Parent(<record id>)/<RelatedOccurrence>?$select=<fk>` and `/<RelatedTable>?$filter=<fk> eq '<parent key>'` | the same row count, on a relationship with the key as its only predicate |
| `~` in an occurrence name | `/<Occurrence~Name>?$top=1`, then an occurrence without `~` | the first answers -1002 at the text after `~`, the second 200 |
| dotted field name | `?$filter=A.B eq <typed literal>&$select=A.B&$top=2` | rows, with only that column |

## Evidence

| Claim | Observed | Corroboration | Claris guide |
|---|---|---|---|
| `$`-prefixed options must stay literal; `%24top` is dropped and the table returns | host A 2026-09-28 (1,633-row table) and host B 2026-09-29 (3,306-row table): `%24top` returned every row, `$top` returned the number asked | an open-source FileMaker OData client on GitHub rewrites `%24` back to `$` and `+` to `%20` after encoding | not stated |
| A space sent as `+` is refused with -1002 | host A 2026-09-28; host B 2026-09-25 | the same library | not stated |
| `%3A` inside a timestamp literal and `%2C` inside a `$select` list are refused with -1002; `%28` and `%22` are accepted | host A 2026-09-29 | a second developer's agent hit the `%3A` case independently the day before | not stated |
| A quoted date or timestamp literal returns no error and no usable data; unquoted ISO 8601 works; a timestamp needs a zone | host A 2026-09-28 and host B 2026-09-29, same three results (quoted: zero rows; `T00:00:00` alone -1002; `T00:00:00Z` rows; offsets untried); host B 2026 also recorded nulls for a quoted date | none | "Date, time, and timestamp formats conform to ISO 8601. Time zone offsets are relative to the time zone of the server." |
| A response stops at 10,000 rows; the continuation is `@nextLink` with `$skiptoken=s10000t0` | host A 2026-09-28 (22,668-row table, two pages); host B 2026-09-25 (three tables) | none | "A maximum of 10,000 records are returned at a time. If the total records in a request exceeds 10,000, the nextLink value is also returned providing the next set of records." Key name not given. |
| The server's `@nextLink` encodes the `:` of a timestamp in `$filter` as `%3A` and refuses it (-1002); decoding it to `:` works; `$top=10000` returns no `@nextLink` | host B 2026-10-05 (11,017 rows: page 1 10,000, link refused as given, 1,017 after decoding; `/$count` 11,017) | none | not stated |
| A raw `~` in a `$select` field name is refused (-1002 at the text after `~`); `%7E` and the double-quoted name work | host B 2026-10-05: `_k1_ID,<field~name>` 400, the same with `%7E` 200, with `%22...%22` 200; host B accepted it raw on 2026-09-29 | none | not stated |
| Annotations omit the `odata.` segment | host A 2026-09-28 (`@context`, `@count`, `@nextLink`, `@id`, `@editLink`); `@nextLink` also host B | none | not stated |
| `ID` fails unquoted (-1002) and works double-quoted in `$select`, `$orderby`, `$filter` | host A 2026-09-28 | none | "Enclose field names that include special characters, such as spaces or underscores, in double-quotation marks." Reserved words not mentioned. |
| The entity key is the record id from `@editLink`, not the `ID` field | host A 2026-09-28: `Table(<ID value>)` -1023, `Table('<ID value>')` 8309, `$filter="ID" eq <value>` 200 | none | not stated |
| `$count=true` works; the count ignores `$top`, the rows honour it | host A 2026-09-28 (`@count: 22668`); host B 2026-09-29 (`@count: 3306`) | none | documented, with the `$top`/`$skip` note |
| `$orderby` works, quoted and unquoted, on names with underscores | host A 2026-09-28; host B 2026-09-29 | none | quoting rule as above |
| A dotted field name works in `$filter` and `$select` when the literal matches the type | host B 2026-09-29 (`_trigger.names eq 1`, numeric) | none | not stated |
| Navigation `Parent(<record id>)/<RelatedOccurrence>` returns the related set as the relationship defines it | host B 2026-09-30: six parent records on each of two databases, the navigation count equal to a direct foreign-key filter each time (6 to 109 rows); occurrences with extra predicates returned the filtered subset | none | not checked |
| An occurrence whose name contains `~` cannot be addressed in the path: entity set raw, `%7E` or double-quoted, navigation segment raw or `%7E` | host B 2026-09-30: -1002 at the text after `~` in all five forms; the same request on an occurrence without `~` 200 | none | not checked |
| Retired 2026-09-29: `$count` 400, `$orderby` -1002, dotted names zero rows | all three were host B, 2026, before the encoding and literal rules were known; none reproduced on 2026-09-29. (`~` rejected raw was retired with them and came back on 2026-10-05, see above.) | | |

## Contributing a claim

A claim ships with an "Observed:" line (host described, never named; date) and a Claris cell. Describe a
host by its FileMaker Server version and hosting kind; never by name, hostname, table name or person. A PR
that turns a single-host row into a two-host row is the most useful one this repository can receive.

Maintained by OOGI BV.
