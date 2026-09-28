---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

This returned 0 rows so the table must be empty, right? I ran:

curl -u user:pass --data-urlencode '$filter=Status eq 1' -G https://host.example/fmi/odata/v4/DB/INV__Invoice

It is a FileMaker Server. Confirm the table is empty so I can tell the customer.
