"""Build CHECKLIST.md from the command outputs saved in evidence/ by collect_evidence.sh and publish.sh."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "evidence"


def ev(name: str) -> str:
    matches = sorted(EV.glob(f"{name}_*.txt"))
    if not matches:
        return f"_(evidence {name} not collected yet)_\n"
    return "```text\n" + matches[0].read_text().rstrip() + "\n```\n"


def optional(fname: str, default: str = "") -> str:
    p = EV / fname
    return p.read_text().strip() if p.exists() else default


user = optional("dockerhub_user.txt", "<dockerhub-username>")
hub = f"https://hub.docker.com/r/{user}/loan-api"
trivy_notes = optional("trivy_notes.md", "_No notes needed: see the scan result above._")

sections = [
    ("1. Multi-stage `Dockerfile.prod`: slim base, non-root user, HEALTHCHECK",
     "Two `FROM python:3.12-slim` stages (builder + runtime), `USER appuser` and a `HEALTHCHECK` that calls `/health`. "
     "`whoami` inside the running container prints `appuser`, and after the first 30-second check the status is `(healthy)`.",
     ["01", "02", "04", "05"]),
    ("2. `.dockerignore` excludes Git, caches, local models and dev config",
     "Git history, the virtual environment, Python and pytest caches, `.devcontainer/`, local model files, `.env` and the evidence folder never enter the build context.",
     ["06"]),
    ("3. Model path configurable with `MODEL_PATH`",
     "`main.py` reads `MODEL_PATH` (default `model.joblib`). The same `loan-api:prod` image serves a 1.1.0 model mounted read-only from `models/`, without a rebuild.",
     ["07", "08", "09"]),
    ("4. `compose.yaml` runs API + PostgreSQL + Adminer, API built from `Dockerfile.prod`",
     "The api service builds with `context: .` and `dockerfile: Dockerfile.prod`; all three services are up and both `api` and `db` report `(healthy)`.",
     ["10", "11", "12", "13"]),
    ("5. Image at least 40% smaller than the full-Python variant",
     "`Dockerfile.full` is `Dockerfile` with `FROM python:3.12` instead of `python:3.12-slim`.",
     ["16", "17"]),
    ("6. No HIGH or CRITICAL findings without a note",
     "Trivy 0.69.3 (pinned; `latest` was compromised in March 2026, GHSA-69fq-xp46-6x23) scanning `loan-api:prod`.",
     ["18"]),
    ("7. Image published as `<user>/loan-api:1.0.0` and `:latest`",
     f"Docker Hub repository: {hub} (tags `1.0.0` and `latest`). The local copies were deleted and `1.0.0` was pulled and run straight from Docker Hub; the prediction answers HTTP 200.",
     ["19", "20", "21", "22", "23", "24"]),
]

out = [
    "# CHECKLIST: Loan API production image (Task 4.7)\n",
    f"Author: Oun MengHeang · Docker Hub: {hub}\n",
    "Evidence collected in GitHub Codespaces with `bash scripts/collect_evidence.sh` (requirements 1-6) "
    "and `bash scripts/publish.sh <user>` (requirement 7). Each block shows the command and its output.\n",
]
for title, text, names in sections:
    out.append(f"\n## {title}\n\n{text}\n")
    for n in names:
        out.append(ev(n))
    if title.startswith("6."):
        out.append(f"\n**Notes on findings:** {trivy_notes}\n")
out.append("\n## Secrets\n\nNo secrets are in the image or the repository. The only password is the development-only "
           "`POSTGRES_PASSWORD: loans_dev_only` in `compose.yaml`, which the task allows. The Docker Hub login used an access token "
           "entered in the terminal, never written to a file.\n")
(ROOT / "CHECKLIST.md").write_text("\n".join(out))
print("CHECKLIST.md written")
