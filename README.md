# fm-odata

Point your AI here and it'll be able to work with OData.

A Claude Code skill that carries what FileMaker's OData does differently from the standard, with the
evidence per claim: unquoted date literals, a query string that must keep `$` literal, a 10,000-row stop
with the continuation under `@nextLink`, field names that need double quotes, an entity key that is not
the `ID` field. FileMaker answers most of these with wrong data rather than an error, which is why an agent
that has not read them reproduces them. The guideline is [skills/fm-odata/GUIDELINE.md](skills/fm-odata/GUIDELINE.md);
the [Evidence](skills/fm-odata/GUIDELINE.md#evidence) section says where each claim was observed and what
Claris's own guide says about it.

## Install

In a Claude Code session (2.1.275 or later), one step:

```
/plugin install fm-odata --marketplace oogi-io/claude-plugins
```

From the shell:

```bash
claude plugin marketplace add oogi-io/claude-plugins
claude plugin install fm-odata@oogi
```

Later:

```bash
claude plugin update fm-odata@oogi        # this marketplace does not auto-update unless you turn it on
claude plugin uninstall fm-odata@oogi     # removing the oogi marketplace instead uninstalls every plugin from it
```

Do not clone this repository into your Claude skills folder: a checkout that carries `plugin.json` loads as
a second plugin and one of the two shows as not loaded. To work on the skill, load a checkout for one session
with `claude --plugin-dir .`.

## What it does

Once installed, the skill fires when an agent is about to write a FileMaker OData URL, `$filter`, `$select`,
`$orderby`, `$count` or paging loop, and when an OData answer looks wrong in the ways FileMaker makes it look
wrong: nulls, zero rows, -1002, 8309, or a suspiciously round row count. It fires on its description alone;
there is no hook. When it does not fire, "use the fm-odata skill" in the prompt does.

Its default is reads. Whether an agent may write through OData is your organisation's rule.

## Why 1.0.0

Every behaviour except one (the `ID` field name) was observed on two FileMaker Server hosts, and two of them
are documented by Claris. Three earlier single-host claims were retested on the second host and retired; the
Evidence table says which and why. The Verify section in the guideline shows how to test each claim on your
own server in one request; a report of what you saw is a welcome pull request.

## Contributing

A claim ships with an "Observed:" line and a Claris cell. Hosts are described (FileMaker Server version,
hosting kind), never named: no hostname, no table name, no person, no company. `tools/check.py` refuses
hostnames and table-occurrence-shaped names on every push.

## Licence

MIT, OOGI BV. Sibling of [fmsonar](https://github.com/oogi-io/fm-ddr-analyzer) and
[fmstyle](https://github.com/oogi-io/fm-code-formatter).
