#!/usr/bin/env python3
"""Repository checks for fm-odata-skill. Standard library only.

  python3 tools/check.py                      scrub guard, consistency, claim scope, URL example
  python3 tools/check.py --eval-report r.json eval gate: the skill must have fired in every
                                              with-plugin run of the symptom cases

Exit 0 when everything passes, 1 on any failure. Every failure names the file and the line.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()
SKIP_DIRS = {".git", "results", "node_modules"}
SKIP_FILES = {"LICENSE"}

HOST_ALLOW = {
    "github.com", "help.claris.com", "claris.com", "oasis-open.org", "example.com",
    "creativecommons.org", "claude.com", "code.claude.com", "oogi.io",
}
HOST_RE = re.compile(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|dev|eu|be|nl))\b")
PATH_RES = [re.compile(p) for p in (r"/Users/", r"(?<![\w])~/", r"\.env\b", r"fetch\.py", r"\.claude/projects")]
TO_RE = re.compile(r"\b([A-Z]{2,8}(?:_[A-Za-z]{2,12})*__[A-Za-z]+)\b")
TO_ALLOW = {"INV__Invoice", "CUST_INV__Invoice__open"}
GLYPHS = {"—": "em dash", "–": "en dash", "✅": "check glyph", "❌": "cross glyph", "⚠": "warning glyph"}

# Symptom cases: the skill must fire in every with-plugin run of these.
SYMPTOM_CASES = ("zero-rows-is-not-empty", "fetch-every-row")


def files():
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.resolve() == SELF:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.name in SKIP_FILES:
            continue
        yield p


def scrub(failures):
    for p in files():
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = p.relative_to(ROOT)
        for n, line in enumerate(text.splitlines(), 1):
            for m in HOST_RE.finditer(line):
                host = m.group(1)
                if host not in HOST_ALLOW and not any(host.endswith("." + a) for a in HOST_ALLOW):
                    failures.append(f"{rel}:{n}: hostname not on the allowlist: {host}")
            for rx in PATH_RES:
                if rx.search(line):
                    failures.append(f"{rel}:{n}: machine-specific path or file reference: {rx.pattern}")
            for m in TO_RE.finditer(line):
                if m.group(1) not in TO_ALLOW:
                    failures.append(f"{rel}:{n}: table-occurrence-shaped name outside the neutral examples: {m.group(1)}")
            for ch, name in GLYPHS.items():
                if ch in line:
                    failures.append(f"{rel}:{n}: {name}")


def consistency(failures):
    skill = ROOT / "skills" / "fm-odata" / "SKILL.md"
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    fm = re.match(r"---\n(.*?)\n---", skill.read_text(), re.S)
    front = dict(re.findall(r"^(\w+):\s*(.*)$", fm.group(1), re.M)) if fm else {}
    if "name" not in front or "description" not in front:
        failures.append("skills/fm-odata/SKILL.md: frontmatter needs name and description")
    if front.get("name") != manifest.get("name"):
        failures.append(f"name drift: SKILL.md {front.get('name')!r} vs plugin.json {manifest.get('name')!r}")
    version = manifest.get("version", "")
    if f"## {version}" not in (ROOT / "CHANGELOG.md").read_text():
        failures.append(f"CHANGELOG.md has no block for plugin.json version {version}")
    for name in re.findall(r"\b([A-Z]+\.md)\b", skill.read_text()):
        if not (skill.parent / name).exists():
            failures.append(f"SKILL.md names {name}, which does not exist next to it")


def claim_scope(failures):
    text = (ROOT / "skills" / "fm-odata" / "GUIDELINE.md").read_text()
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    behaviour = [s for s in sections if not s.startswith(("Core concepts", "What works", "Writes", "Related records",
                                                          "Verify on your host", "Evidence", "Contributing"))]
    for s in behaviour:
        title = s.splitlines()[0]
        if "Observed:" not in s:
            failures.append(f"GUIDELINE.md section '{title}' has no Observed: line")


def url_example(failures):
    text = (ROOT / "skills" / "fm-odata" / "GUIDELINE.md").read_text()
    m = re.search(r"```python\n(from urllib.parse import quote.*?)```", text, re.S)
    if not m:
        failures.append("GUIDELINE.md: the odata_url example block was not found")
        return
    ns = {}
    exec(m.group(1), ns)  # noqa: S102 - our own example, checked here on purpose
    url = ns["odata_url"]("https://host.example/fmi/odata/v4/DB", "INV__Invoice",
                          filter="Name eq 'a b' and \"ID\" gt 0", select="a~b", top=3)
    checks = [
        ("$filter=" in url and "%24" not in url, "$ must stay literal"),
        ("%20" in url and "+" not in url, "spaces must be %20"),
        ("%7E" in url, "~ must be %7E"),
        ("'a%20b'" in url and '"ID"' in url, "quotes must stay literal"),
        ("%3A" not in ns["odata_url"]("https://host.example/x", "INV__Invoice", filter="D ge 2020-01-01T00:00:00Z"), ": must stay literal"),
        ("%2C" not in ns["odata_url"]("https://host.example/x", "INV__Invoice", select='"ID",Total'), ", must stay literal"),
    ]
    for ok, what in checks:
        if not ok:
            failures.append(f"URL example: {what}: {url}")


def eval_gate(path, failures):
    data = json.loads(Path(path).read_text())
    seen = {c: 0 for c in SYMPTOM_CASES}

    def walk(node, case=None, arm=None):
        if isinstance(node, dict):
            case = node.get("case") or node.get("case_name") or node.get("name") if any(
                node.get(k) in SYMPTOM_CASES for k in ("case", "case_name", "name")) else case
            arm = node.get("arm", arm)
            grader = str(node.get("grader") or node.get("name") or "")
            if "skill-fired" in grader and case in SYMPTOM_CASES and (arm in (None, "with", "with-plugin", "plugin")):
                passed = node.get("passed", node.get("pass", node.get("score")))
                if passed in (True, 1, 1.0):
                    seen[case] += 1
                else:
                    failures.append(f"eval: skill did not fire on case {case} (arm {arm})")
            for v in node.values():
                walk(v, case, arm)
        elif isinstance(node, list):
            for v in node:
                walk(v, case, arm)

    walk(data)
    for c, n in seen.items():
        if n == 0:
            failures.append(f"eval: no skill-fired result found for case {c}; read the report by hand")


def main(argv):
    failures = []
    if len(argv) >= 2 and argv[0] == "--eval-report":
        eval_gate(argv[1], failures)
    else:
        scrub(failures)
        consistency(failures)
        claim_scope(failures)
        url_example(failures)
    for f in failures:
        print("FAIL", f)
    print("ok" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
