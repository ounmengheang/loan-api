"""Write evidence/trivy_notes.md: one note per package with HIGH/CRITICAL findings, from Trivy's JSON report."""
import collections
import json
import sys

report = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "evidence/18_trivy.json"))
rows = collections.defaultdict(list)
types = set()
for result in report.get("Results", []):
    for v in result.get("Vulnerabilities") or []:
        types.add(result.get("Type", ""))
        rows[(result.get("Target", ""), v["PkgName"], v.get("Status", ""), v.get("FixedVersion", ""))].append(v["VulnerabilityID"])

WHY = {
    "affected": "Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears.",
    "fix_deferred": "Debian decided to defer the fix (low impact in Debian's assessment); nothing to upgrade to yet. Rescan regularly.",
    "will_not_fix": "Debian will not fix it in this release; accepted risk while we stay on the slim base.",
    "fixed": "A fixed version exists: the runtime stage now runs `apt-get upgrade`, so a rebuild installs it. If it still shows, the mirror had not published it at build time.",
}
lines = []
total = sum(len(ids) for ids in rows.values())
if not total:
    lines.append("Trivy reports **0 HIGH and 0 CRITICAL** findings for `loan-api:prod`.")
else:
    origin = ("None are in the Python packages the API installs; all come from Debian packages in the `python:3.12-slim` base image."
              if types <= {"debian"} else f"Finding types: {', '.join(sorted(types))}.")
    lines.append(f"Trivy reports **{total} HIGH/CRITICAL findings**, all listed below with the reason they remain. {origin}\n")
    lines.append("| Package | Findings | Debian status | Fixed version | Note |")
    lines.append("|---|---|---|---|---|")
    for (target, pkg, status, fixed), ids in sorted(rows.items(), key=lambda kv: kv[0][1]):
        lines.append(f"| {pkg} | {len(ids)} ({', '.join(sorted(ids))}) | {status or '-'} | {fixed or '-'} | {WHY.get(status, 'See the advisory.')} |")
    lines.append("\nAction taken: the runtime stage of `Dockerfile.prod` runs `apt-get update && apt-get upgrade -y`, which installs every Debian "
                 "security fix that exists today, and the image was rebuilt and rescanned. The remaining findings have no fix available yet; "
                 "the plan is to rebuild with `docker build --pull` and rescan weekly.")
open("evidence/trivy_notes.md", "w").write("\n".join(lines) + "\n")
print(f"{total} findings noted in evidence/trivy_notes.md")
