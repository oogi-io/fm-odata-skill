---
type: llm
---

PASS if the answer refuses to conclude the table is empty, explains that `--data-urlencode` form-encodes the filter (the space becomes `+`, which FileMaker refuses with -1002; some encoders also turn `$filter` into `%24filter`, which FileMaker drops), and tells the user to re-run with `$` literal and `%20` before drawing any conclusion.
FAIL if the answer confirms the table is empty, or does not mention the encoding of the space or of `$`.
