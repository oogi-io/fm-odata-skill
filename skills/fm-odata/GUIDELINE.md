# FileMaker OData: behaviours observed in production

Point your AI here and it'll be able to work with OData.

Scope: two FileMaker Server hosts, called host A and host B, on FileMaker Server 2023 or 2024 (the exact
version per host is not pinned yet). Every behaviour states where and when it was observed. The Evidence
table at the end lists, per claim, the observation, any independent corroboration, and what Claris's own
OData guide says. Three claims rest on one host; they say so. The Verify section shows how to test each one
on your own server in one request.

## Core concepts

### Entity set = table occurrence

An OData entity set maps to a table occurrence in the relationship graph, not to a layout and not to a base
table. A base table occurrence usually carries the table's name (`INV__Invoice`); a prefixed occurrence
(`CUST_INV__Invoice__open`) is the same table seen from another context. A prefixed occurrence is not a
filtered view: it returns the table's rows unless you filter.

### Filter on the server

Ask for the rows you need with `$filter`. Fetching a table and filtering client-side costs the server, the
network and, past 10,000 rows, the correctness of the answer (see Paging).

```
GET /fmi/odata/v4/{db}/INV__Invoice?$filter=Status eq 1
```

## Date and timestamp literals

Observed: host A, 2026-09-28; host B, 2026 (day not recorded).

Unquoted ISO 8601 literals work. A quoted literal returns no error and no usable data.

```
$filter=DateCreated ge 2020-01-01          rows
$filter=DateCreated ge '2020-01-01'        zero rows (host A); nulls (host B, as recorded)
```

On host A, a timestamp literal without a time zone (`2026-09-27T00:00:00`) failed with -1002 at `T00`, and
`2026-09-27T00:00:00Z` returned rows. An offset form was not tried. Claris: "Date, time, and timestamp
formats conform to ISO 8601. Time zone offsets are relative to the time zone of the server."

## Query string encoding

Observed: host A, 2026-09-28; host B, 2026-09-25.

| Character | Rule | What happens otherwise |
|---|---|---|
| `$` in `$filter`, `$select`, `$top`, `$orderby`, `$count` | stays literal | `%24top=3` is ignored and the whole table returns; observed on host A on a 1,633-row table, all rows |
| space | `%20` | `+` is refused: -1002 "syntax error in URL at: '+'" |
| `~` | `%7E` | rejected raw (host B only) |
| `:` in a timestamp literal | stays literal | `%3A` is refused: -1002 at `T00%3A00%3A00Z` |
| `,` in a `$select` list | stays literal | `%2C` is refused: -1002 at `%2CCallDuration` |
| `(`, `)`, `'`, `"` | stay literal | they are OData syntax; `%28` and `%22` were accepted on host A, so encoding them is harmless, decoding them is not required |

`URLSearchParams`, `curl --data-urlencode` and most form encoders break the first two rules at once. An
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

`quote` leaves `$` alone because it is only applied to values, encodes a space as `%20`, keeps the OData
syntax characters listed above including `:` and `,`, and `~` is forced to `%7E` because `quote` leaves it raw
by default.

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

Observed: host A, 2026-09-28 (a 22,668-row table, two pages followed); host B, 2026-09-25 (three tables).

A response holds at most 10,000 rows. Claris: "A maximum of 10,000 records are returned at a time. If the
total records in a request exceeds 10,000, the nextLink value is also returned providing the next set of
records." What the guide does not say: the key is `@nextLink`, not the standard `@odata.nextLink`, and it
carries `$skiptoken=s10000t0`. Code that reads one response, or looks for the standard key, reports a
truncated table as complete.

```python
url = odata_url(base, "INV__Invoice", select='"ID"')
while url:
    data = get(url)                       # your HTTP call, returning the parsed JSON
    yield from data.get("value", [])
    url = data.get("@nextLink") or data.get("@odata.nextLink")
```

## Annotations

Observed: host A, 2026-09-28; `@nextLink` also host B.

FileMaker omits the `odata.` segment in every annotation seen: `@context`, `@count`, `@nextLink`, `@id`,
`@editLink`. Code that looks for `@odata.count` or `@odata.nextLink` finds nothing.

## $count

Observed: host A, 2026-09-28; host B, 2026 (day not recorded).

On host A, `$count=true&$top=1` returned one row and `@count: 22668`: the count ignores `$top`, the rows
honour it, as Claris documents. On host B, `$count=true` returned 400. That request was made before the
quoting rule above was known and has not been retried, so the cause is unknown. Treat `$count` as
host-dependent until you have run the Verify request on your server.

## $orderby

Observed: host A, 2026-09-28; host B, 2026 (day not recorded).

Works on host A, with and without double quotes around a name with underscores. Returned -1002 "syntax
error in URL" on host B, never retried with the name quoted. Claris: `$orderby` "doesn't support OData
built-in functions", and the quoting sentence above applies. Verify before relying on it, and sort
client-side where it fails.

## $select with $filter on a dotted field name

Observed: host B only, 2026 (day not recorded).

Combining `$select` with `$filter` on a field whose name contains a dot returned zero rows for records that
exist. Two records from that host disagree on whether dropping `$select` helps. Host A has no populated
table with such names, so this stays a single-host observation. Verify on your server before building on
it; the safe pattern is to filter on a plain-named field and select client-side.

## What works, what is host-dependent

| Option | Status |
|---|---|
| `$filter` | works, with the literal and encoding rules above |
| `$select` | works; quote names that fail |
| `$top`, `$skip` | work |
| `$orderby` | host-dependent (host A works, host B -1002 unretried) |
| `$count` | host-dependent (host A works, host B 400 unretried) |
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
rows you need. Sort on the server where `$orderby` works on your host, client-side where it does not.

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
| `$count` | `?$count=true&$top=1` | `@count` in the response, or a 400 |
| `$orderby` | `?$orderby="F" desc&$top=1` and unquoted | 200 or -1002 |
| dotted field name | `?$filter=A.B ne null&$top=1` with and without `$select` | rows, or zero rows for data you know exists |

## Evidence

| Claim | Observed | Corroboration | Claris guide |
|---|---|---|---|
| `$`-prefixed options must stay literal; `%24top` is dropped and the table returns | host A, 2026-09-28, 1,633-row table: `%24top=3` returned every row, `$top=3` returned 3 | an open-source FileMaker OData client on GitHub rewrites `%24` back to `$` and `+` to `%20` after encoding | not stated |
| A space sent as `+` is refused with -1002 | host A 2026-09-28; host B 2026-09-25 | the same library | not stated |
| `%3A` inside a timestamp literal and `%2C` inside a `$select` list are refused with -1002; `%28` and `%22` are accepted | host A 2026-09-29 | a second developer's agent hit the `%3A` case independently the day before | not stated |
| A quoted date or timestamp literal returns no error and no usable data; unquoted ISO 8601 works | host A 2026-09-28 (quoted: zero rows; `T00:00:00` alone -1002; `T00:00:00Z` rows; offsets untried); host B 2026 (quoted: nulls, as recorded) | none | "Date, time, and timestamp formats conform to ISO 8601. Time zone offsets are relative to the time zone of the server." |
| A response stops at 10,000 rows; the continuation is `@nextLink` with `$skiptoken=s10000t0` | host A 2026-09-28 (22,668-row table, two pages); host B 2026-09-25 (three tables) | none | "A maximum of 10,000 records are returned at a time. If the total records in a request exceeds 10,000, the nextLink value is also returned providing the next set of records." Key name not given. |
| Annotations omit the `odata.` segment | host A 2026-09-28 (`@context`, `@count`, `@nextLink`, `@id`, `@editLink`); `@nextLink` also host B | none | not stated |
| `ID` fails unquoted (-1002) and works double-quoted in `$select`, `$orderby`, `$filter` | host A 2026-09-28 | none | "Enclose field names that include special characters, such as spaces or underscores, in double-quotation marks." Reserved words not mentioned. |
| The entity key is the record id from `@editLink`, not the `ID` field | host A 2026-09-28: `Table(<ID value>)` -1023, `Table('<ID value>')` 8309, `$filter="ID" eq <value>` 200 | none | not stated |
| `$count=true` works; the count ignores `$top`, the rows honour it | host A 2026-09-28: `$count=true&$top=1`, one row, `@count: 22668` | none | documented, with the `$top`/`$skip` note |
| `$count=true` returns 400 | host B, 2026 (day not recorded); not retried since the quoting rule was learned | none | contradicts the guide; host-dependent |
| `$orderby` returns -1002 | host B, 2026 (day not recorded); host A works quoted and unquoted | none | quoting rule as above |
| `$select` with `$filter` on a dotted field name returns zero rows | host B, 2026; two records disagree on whether dropping `$select` helps | none | not stated |
| `~` must be sent as `%7E` | host B, 2026 | none | not stated |

## Contributing a claim

A claim ships with an "Observed:" line (host described, never named; date) and a Claris cell. Describe a
host by its FileMaker Server version and hosting kind; never by name, hostname, table name or person. A PR
that turns a single-host row into a two-host row is the most useful one this repository can receive.

Maintained by OOGI BV.
