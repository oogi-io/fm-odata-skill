# Changelog

## Unreleased

Two claims from host B, 2026-09-30. Navigation `Parent(<record id>)/<RelatedOccurrence>` returns what the
relationship graph matches, which makes it a read-only test of a relationship. A table occurrence whose
name contains `~` cannot be addressed in the URL path in any form; the earlier `~` note now says it covers
query values only. Host B's version pinned at 22.0, and the unverified "2023 or 2024" dropped.

## 1.0.1, 2026-09-30

SKILL.md now carries the comma and colon rule (`%2C` in a `$select` list and `%3A` in a timestamp are
refused with -1002). It was in the guideline's encoding table only, and an agent that loaded the skill
without opening the guideline percent-encoded a `$select` list in its own code. No claim changed.

## 1.0.0, 2026-09-29

First release. Encoding, paging, date and timestamp literals, `$count`, `$orderby` and dotted field names
observed on two FileMaker Server hosts; three earlier single-host claims retested on the second host and
retired; the `curl --data-urlencode` failure named precisely (it is the `+`).
