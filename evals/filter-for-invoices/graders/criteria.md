---
type: llm
---

PASS if the answer gives a query string whose date literal is unquoted (for example `DateCreated gt 2026-03-01`), keeps `$filter` with a literal `$`, and writes spaces as `%20` or says to.
FAIL if the date literal is wrapped in single quotes, or `$` is written as `%24`, or spaces are encoded as `+`.
