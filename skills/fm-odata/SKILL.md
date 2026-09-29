---
name: fm-odata
description: FileMaker OData behaviours that return wrong data instead of errors. Read before writing any FileMaker OData URL, $filter, $select, $orderby, $count or paging loop, and whenever a FileMaker OData call answers with nulls, zero rows, -1002 "syntax error in URL", 8309, or a suspiciously round number of rows such as 10000. Also for a curl --data-urlencode or URLSearchParams line aimed at /fmi/odata/, and for any task that reads live data out of FileMaker Server through OData.
---

FileMaker's OData is close enough to the standard to look familiar and far enough from it to hand back
nulls, zero rows or a truncated table without an error. Read GUIDELINE.md next to this file before composing
a URL; it carries the evidence for every line below.

## Five behaviours

1. **Date and timestamp literals are unquoted.** `Date eq 2026-03-02` works. `Date eq '2026-03-02'` returns
   no error and no usable data: zero rows, on both hosts observed. A timestamp needs the full ISO form with a
   zone, `2026-03-02T00:00:00Z`; without the zone the server answers -1002.
2. **Never build the query string with a form encoder.** `URLSearchParams` turns `$filter` into `%24filter`,
   which the server drops before returning the whole table, and every form encoder, `curl --data-urlencode`
   included, turns a space into `+`, which the server refuses with -1002. Keep `$` literal, write spaces as
   `%20`, concatenate by hand.
3. **A response stops at 10,000 rows.** The continuation is under `@nextLink`, not `@odata.nextLink`. Loop on
   the key and accept both spellings, or a large table reads as complete at exactly 10,000.
4. **A field name that fails unquoted works double-quoted.** `$select=ID` answers -1002; `$select="ID"`,
   `$orderby="ID"` and `$filter="ID" gt 0` work. Quote any name you are unsure of. The entity key in
   `Table(key)` is FileMaker's record id, the number in `@editLink`, not the table's `ID` field.
5. **Annotations omit the `odata.` segment.** `@context`, `@count`, `@nextLink`, `@id`, `@editLink`. Code that
   looks for `@odata.count` finds nothing.

## Before concluding there is no data

A zero-row answer from FileMaker OData is more often an encoding mistake than an empty table. Unquote the
date, quote the field name, replace `+` with `%20`, drop `$select`, and re-run. Only then is an absence a
finding.

## Writes

POST, PATCH, DELETE and a script endpoint exist. The rule here is reads; a write happens only on an
instruction that names the record and the change, and an organisation's own rule wins over that.

## Entity sets

An entity set is a table occurrence, not a layout and not a base table. GUIDELINE.md explains the naming
and how to pick the one you need.

## The limit of this skill

It fires on its description alone; there is no hook. When it does not fire, "use the fm-odata skill" in the
prompt does.
