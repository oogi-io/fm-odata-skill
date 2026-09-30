# Changelog

## 1.0.1, 2026-09-30

SKILL.md now carries the comma and colon rule (`%2C` in a `$select` list and `%3A` in a timestamp are
refused with -1002). It was in the guideline's encoding table only, and an agent that loaded the skill
without opening the guideline percent-encoded a `$select` list in its own code. No claim changed.

## 1.0.0, 2026-09-29

First release. Encoding, paging, date and timestamp literals, `$count`, `$orderby` and dotted field names
observed on two FileMaker Server hosts; three earlier single-host claims retested on the second host and
retired; the `curl --data-urlencode` failure named precisely (it is the `+`).
