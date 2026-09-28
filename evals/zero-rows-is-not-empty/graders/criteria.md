---
type: llm
---

PASS if the answer refuses to conclude the table is empty, explains that `--data-urlencode` encodes `$filter` as `%24filter` and spaces as `+` so FileMaker ignored or refused the filter, and tells the user to re-run with `$` literal and `%20` before drawing any conclusion.
FAIL if the answer confirms the table is empty, or does not mention the encoding of `$` or the space.
