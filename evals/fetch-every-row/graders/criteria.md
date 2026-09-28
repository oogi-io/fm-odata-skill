---
type: llm
---

PASS if the code follows a continuation link across pages and reads the `@nextLink` key (accepting `@odata.nextLink` as well is fine), and the answer states that a single response stops at 10,000 rows.
FAIL if the code reads one response and counts its rows, or only looks for `@odata.nextLink`, or does not mention the 10,000-row limit.
