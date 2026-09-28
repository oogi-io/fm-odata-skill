---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Fetch every row of INV__Invoice from our FileMaker server over OData and count them. Write me the Python that does it against https://host.example/fmi/odata/v4/DB with basic auth. The table has about 40,000 rows.
