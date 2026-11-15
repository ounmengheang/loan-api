# CHECKLIST: Loan API production image (Task 4.7)

Author: Oun MengHeang · Docker Hub: https://hub.docker.com/r/ounmengheang/loan-api

Evidence collected in GitHub Codespaces with `bash scripts/collect_evidence.sh` (requirements 1-6) and `bash scripts/publish.sh <user>` (requirement 7). Each block shows the command and its output.


## 1. Multi-stage `Dockerfile.prod`: slim base, non-root user, HEALTHCHECK

Two `FROM python:3.12-slim` stages (builder + runtime), `USER appuser` and a `HEALTHCHECK` that calls `/health`. `whoami` inside the running container prints `appuser`, and after the first 30-second check the status is `(healthy)`.

```text
$ grep -nE '^(FROM|USER|HEALTHCHECK)' Dockerfile.prod
2:FROM python:3.12-slim AS builder
12:FROM python:3.12-slim
21:USER appuser
23:HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
```

```text
$ docker build -t loan-api:prod -f Dockerfile.prod . 2>&1 | tail -n 12

#19 exporting to image
#19 exporting layers
#19 exporting layers 10.3s done
#19 exporting manifest sha256:f0e45005bce1fc8ad8c92fd22f7fa86ad6b93f79c337b7dad5ad3fa9ce5ad1ff 0.0s done
#19 exporting config sha256:ec484dddc7b5c468ecb67f25ff31ae5e2a4d15f452639b706f326425f6066440 0.0s done
#19 exporting attestation manifest sha256:f5b70cfddf2ed31753cce60e5f90b39030b66ec98a0e1415cf352661d1da0321 0.0s done
#19 exporting manifest list sha256:6ab98a66ff5eb968dd56306d75ec5a781465af50763ffa0b1816cadf7b6f905c 0.0s done
#19 naming to docker.io/library/loan-api:prod 0.0s done
#19 unpacking to docker.io/library/loan-api:prod
#19 unpacking to docker.io/library/loan-api:prod 8.0s done
#19 DONE 18.4s
```

```text
$ docker exec prod whoami
appuser
```

```text
$ docker ps --filter name=prod --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
NAMES     IMAGE           STATUS
prod      loan-api:prod   Up 40 seconds (healthy)
```


## 2. `.dockerignore` excludes Git, caches, local models and dev config

Git history, the virtual environment, Python and pytest caches, `.devcontainer/`, local model files, `.env` and the evidence folder never enter the build context.

```text
$ cat .dockerignore
.git
.venv
__pycache__/
*.pyc
.pytest_cache/
.devcontainer/
model.joblib
models/
.env
evidence/
```


## 3. Model path configurable with `MODEL_PATH`

`main.py` reads `MODEL_PATH` (default `model.joblib`). The same `loan-api:prod` image serves a 1.1.0 model mounted read-only from `models/`, without a rebuild.

```text
$ python train.py --version 1.1.0 --out models/model.joblib
Saved model 1.1.0 to models/model.joblib (test AUC 0.923)
```

```text
$ docker run -d --name prod110 -p 8001:8000 -v "$(pwd)/models:/models:ro" -e MODEL_PATH=/models/model.joblib loan-api:prod
32d8cc02ddd16bac075818d78c4b5acb92d7dad0450a16ec25a883704864ad22
```

```text
$ curl -s http://localhost:8001/health; echo
{"status":"ok","model_version":"1.1.0"}
```


## 4. `compose.yaml` runs API + PostgreSQL + Adminer, API built from `Dockerfile.prod`

The api service builds with `context: .` and `dockerfile: Dockerfile.prod`; all three services are up and both `api` and `db` report `(healthy)`.

```text
$ grep -nA3 'build:' compose.yaml
3:    build:
4-      context: .
5-      dockerfile: Dockerfile.prod
6-    ports:
```

```text
$ docker compose up -d --build 2>&1 | tail -n 8
 Container loan-api-db-1 Starting 
 Container loan-api-db-1 Started 
 Container loan-api-adminer-1 Starting 
 Container loan-api-db-1 Waiting 
 Container loan-api-adminer-1 Started 
 Container loan-api-db-1 Healthy 
 Container loan-api-api-1 Starting 
 Container loan-api-api-1 Started
```

```text
$ docker compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
SERVICE   IMAGE           STATUS                    PORTS
adminer   adminer:4.8.1   Up 45 seconds             0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
api       loan-api-api    Up 40 seconds (healthy)   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
db        postgres:17     Up 45 seconds (healthy)   5432/tcp
```

```text
$ curl -s http://localhost:8000/health; echo
{"status":"ok","model_version":"1.0.0"}
```


## 5. Image at least 40% smaller than the full-Python variant

`Dockerfile.full` is `Dockerfile` with `FROM python:3.12` instead of `python:3.12-slim`.

```text
$ docker images loan-api
IMAGE           ID             DISK USAGE   CONTENT SIZE   EXTRA
loan-api:full   08904cfab642       2.19GB          542MB        
loan-api:prod   6ab98a66ff5e        778MB          178MB        
loan-api:slim   35c19e85bb73        760MB          174MB
```

```text
$ python3 -c "import subprocess as s; z=lambda t: int(s.check_output(['docker','image','inspect','-f','{{.Size}}','loan-api:'+t])); f,p=z('full'),z('prod'); print(f'full = {f/1e6:.0f} MB, prod = {p/1e6:.0f} MB, prod is {100*(1-p/f):.0f}% smaller than full')"
full = 2185 MB, prod = 778 MB, prod is 64% smaller than full
```


## 6. No HIGH or CRITICAL findings without a note

Trivy 0.69.3 (pinned; `latest` was compromised in March 2026, GHSA-69fq-xp46-6x23) scanning `loan-api:prod`.

```text
$ docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache aquasec/trivy:0.69.3 image --severity HIGH,CRITICAL --no-progress loan-api:prod
2026-11-13T15:49:46Z	INFO	[vulndb] Need to update DB
2026-11-13T15:49:46Z	INFO	[vulndb] Downloading vulnerability DB...
2026-11-13T15:49:46Z	INFO	[vulndb] Downloading artifact...	repo="mirror.gcr.io/aquasec/trivy-db:2"
2026-11-13T15:50:07Z	INFO	[vulndb] Artifact successfully downloaded	repo="mirror.gcr.io/aquasec/trivy-db:2"
2026-11-13T15:50:07Z	INFO	[vuln] Vulnerability scanning is enabled
2026-11-13T15:50:07Z	INFO	[secret] Secret scanning is enabled
2026-11-13T15:50:07Z	INFO	[secret] If your scanning is slow, please try '--scanners vuln' to disable secret scanning
2026-11-13T15:50:07Z	INFO	[secret] Please see https://trivy.dev/docs/v0.69/guide/scanner/secret#recommendation for faster secret detection
2026-11-13T15:50:37Z	INFO	[python] Licenses acquired from one or more METADATA files may be subject to additional terms. Use `--debug` flag to see all affected packages.
2026-11-13T15:50:57Z	INFO	Detected OS	family="debian" version="13.7"
2026-11-13T15:50:57Z	INFO	[debian] Detecting vulnerabilities...	os_version="13" pkg_num=87
2026-11-13T15:50:57Z	INFO	Number of language-specific files	num=1
2026-11-13T15:50:57Z	INFO	[python-pkg] Detecting vulnerabilities...
2026-11-13T15:50:57Z	WARN	Using severities from other vendors for some vulnerabilities. Read https://trivy.dev/docs/v0.69/guide/scanner/vulnerability#severity-selection for details.

Report Summary

┌──────────────────────────────────────────────────────────────────────────────────┬────────────┬─────────────────┬─────────┐
│                                      Target                                      │    Type    │ Vulnerabilities │ Secrets │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ loan-api:prod (debian 13.7)                                                      │   debian   │       47        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/agent_detector-2.0.0.dist-info/METADATA    │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/annotated_doc-0.0.6.dist-info/METADATA     │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/annotated_types-0.8.0.dist-info/METADATA   │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/anyio-4.16.0.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/certifi-2026.10.23.dist-info/METADATA      │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/charset_normalizer-3.5.2.dist-info/METADA- │ python-pkg │        0        │    -    │
│ TA                                                                               │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/click-8.5.1.dist-info/METADATA             │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/cloudpickle-3.1.2.dist-info/METADATA       │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/detect_installer-0.2.1.dist-info/METADATA  │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/dnspython-2.9.2.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/email_validator-2.3.0.dist-info/METADATA   │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/fastapi-0.150.0.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/fastapi_cli-0.0.33.dist-info/METADATA      │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/fastapi_cloud_cli-0.28.0.dist-info/METADA- │ python-pkg │        0        │    -    │
│ TA                                                                               │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/fastar-0.12.0.dist-info/METADATA           │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/googleapis_common_protos-1.76.0.dist-info- │ python-pkg │        0        │    -    │
│ /METADATA                                                                        │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/h11-0.16.0.dist-info/METADATA              │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/httpcore-1.0.9.dist-info/METADATA          │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/httpcore2-2.16.0.dist-info/METADATA        │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/httptools-0.9.0.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/httpx-0.28.1.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/httpx2-2.16.0.dist-info/METADATA           │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/idna-3.20.dist-info/METADATA               │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/jinja2-3.1.6.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/joblib-1.6.0.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/markdown_it_py-4.3.0.dist-info/METADATA    │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/markupsafe-3.0.4.dist-info/METADATA        │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/mdurl-0.1.2.dist-info/METADATA             │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/narwhals-2.28.0.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/numpy-2.5.4.dist-info/METADATA             │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_api-1.45.2.dist-info/METADA- │ python-pkg │        0        │    -    │
│ TA                                                                               │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_exporter_http_transport-0.6- │ python-pkg │        0        │    -    │
│ 6b2.dist-info/METADATA                                                           │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_exporter_otlp_common-0.66b2- │ python-pkg │        0        │    -    │
│ .dist-info/METADATA                                                              │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_exporter_otlp_proto_common-- │ python-pkg │        0        │    -    │
│ 1.45.2.dist-info/METADATA                                                        │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_exporter_otlp_proto_http-1.- │ python-pkg │        0        │    -    │
│ 45.2.dist-info/METADATA                                                          │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_proto-1.45.2.dist-info/META- │ python-pkg │        0        │    -    │
│ DATA                                                                             │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_sdk-1.45.2.dist-info/METADA- │ python-pkg │        0        │    -    │
│ TA                                                                               │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/opentelemetry_semantic_conventions-0.66b2- │ python-pkg │        0        │    -    │
│ .dist-info/METADATA                                                              │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pandas-3.0.6.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pip-25.0.1.dist-info/METADATA              │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/protobuf-7.36.2.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pydantic-2.14.3.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pydantic_core-2.50.4.dist-info/METADATA    │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pydantic_extra_types-2.11.1.dist-info/MET- │ python-pkg │        0        │    -    │
│ ADATA                                                                            │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pydantic_settings-2.16.3.dist-info/METADA- │ python-pkg │        0        │    -    │
│ TA                                                                               │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pygments-2.21.0.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/python_dateutil-4.0.0.dist-info/METADATA   │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/python_dotenv-1.2.4.dist-info/METADATA     │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/python_multipart-0.0.33.dist-info/METADATA │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/pyyaml-6.0.3.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/requests-2.34.2.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/rich-15.0.0.dist-info/METADATA             │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/rich_toolkit-0.20.6.dist-info/METADATA     │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/rignore-0.8.1.dist-info/METADATA           │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/scikit_learn-1.9.1.dist-info/METADATA      │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/scipy-1.18.1.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/sentry_sdk-2.75.0.dist-info/METADATA       │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/shellingham-1.5.4.dist-info/METADATA       │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/starlette-1.10.0.dist-info/METADATA        │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/threadpoolctl-3.8.0.dist-info/METADATA     │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/truststore-0.10.5.dist-info/METADATA       │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/typer-0.29.1.dist-info/METADATA            │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/typing_extensions-4.16.0.dist-info/METADA- │ python-pkg │        0        │    -    │
│ TA                                                                               │            │                 │         │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/typing_inspection-0.4.5.dist-info/METADATA │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/tzdata-2026.6.dist-info/METADATA           │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/urllib3-2.8.0.dist-info/METADATA           │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/uvicorn-0.54.0.dist-info/METADATA          │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/uvloop-0.23.0.dist-info/METADATA           │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/watchfiles-1.3.0.dist-info/METADATA        │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ opt/venv/lib/python3.12/site-packages/websockets-17.4.dist-info/METADATA         │ python-pkg │        0        │    -    │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┼─────────┤
│ usr/local/lib/python3.12/site-packages/pip-25.0.1.dist-info/METADATA             │ python-pkg │        0        │    -    │
└──────────────────────────────────────────────────────────────────────────────────┴────────────┴─────────────────┴─────────┘
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)


loan-api:prod (debian 13.7)
===========================
Total: 47 (HIGH: 47, CRITICAL: 0)

┌───────────────┬─────────────────┬──────────┬──────────────┬───────────────────────────────────┬───────────────┬──────────────────────────────────────────────────────────────┐
│    Library    │  Vulnerability  │ Severity │    Status    │         Installed Version         │ Fixed Version │                            Title                             │
├───────────────┼─────────────────┼──────────┼──────────────┼───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ bsdutils      │ CVE-2026-76642  │ HIGH     │ affected     │ 1:2.41.5-0+deb13u1                │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libacl1       │ CVE-2026-54369  │          │              │ 2.3.2-2+b1                        │               │ acl: Symlink traversal privilege escalation via libacl       │
│               │                 │          │              │                                   │               │ functions                                                    │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-54369                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libblkid1     │ CVE-2026-76642  │          │              │ 2.41.5-0+deb13u1                  │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│ liblastlog2-2 │ CVE-2026-76642  │          │              │                                   │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│ libmount1     │ CVE-2026-76642  │          │              │                                   │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libncursesw6  │ CVE-2025-69720  │          │              │ 6.5+20250216-2                    │               │ ncurses: ncurses: Buffer overflow vulnerability may lead to  │
│               │                 │          │              │                                   │               │ arbitrary code execution.                                    │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2025-69720                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libsmartcols1 │ CVE-2026-76642  │          │              │ 2.41.5-0+deb13u1                  │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libsqlite3-0  │ CVE-2026-119373 │          │              │ 3.46.1-7+deb13u2                  │               │ sqlite: sqlite: Denial of service via heap-based buffer      │
│               │                 │          │              │                                   │               │ overflow in FTS5                                             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-119373                  │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-119374 │          │              │                                   │               │ sqlite: sqlite: Arbitrary code execution via corrupted FTS5  │
│               │                 │          │              │                                   │               │ index                                                        │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-119374                  │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-119379 │          │              │                                   │               │ sqlite: sqlite: Arbitrary code execution via crafted session │
│               │                 │          │              │                                   │               │ changesets                                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-119379                  │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libsystemd0   │ CVE-2026-16742  │          │              │ 257.13-1~deb13u1                  │               │ systemd: systemd-homed: Local privilege escalation via       │
│               │                 │          │              │                                   │               │ missing home-record signature verification                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-16742                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libtinfo6     │ CVE-2025-69720  │          │              │ 6.5+20250216-2                    │               │ ncurses: ncurses: Buffer overflow vulnerability may lead to  │
│               │                 │          │              │                                   │               │ arbitrary code execution.                                    │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2025-69720                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libudev1      │ CVE-2026-16742  │          │              │ 257.13-1~deb13u1                  │               │ systemd: systemd-homed: Local privilege escalation via       │
│               │                 │          │              │                                   │               │ missing home-record signature verification                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-16742                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ libuuid1      │ CVE-2026-76642  │          │              │ 2.41.5-0+deb13u1                  │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ login         │ CVE-2026-76642  │          │              │ 1:4.16.0-2+really2.41.5-0+deb13u1 │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ mount         │ CVE-2026-76642  │          │              │ 2.41.5-0+deb13u1                  │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
├───────────────┼─────────────────┤          │              ├───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ ncurses-base  │ CVE-2025-69720  │          │              │ 6.5+20250216-2                    │               │ ncurses: ncurses: Buffer overflow vulnerability may lead to  │
│               │                 │          │              │                                   │               │ arbitrary code execution.                                    │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2025-69720                   │
├───────────────┤                 │          │              │                                   ├───────────────┤                                                              │
│ ncurses-bin   │                 │          │              │                                   │               │                                                              │
│               │                 │          │              │                                   │               │                                                              │
│               │                 │          │              │                                   │               │                                                              │
├───────────────┼─────────────────┤          ├──────────────┼───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ perl-base     │ CVE-2026-9538   │          │ fix_deferred │ 5.40.1-6+deb13u1                  │               │ perl-Archive-Tar: perl-Archive-Tar: Denial of Service via    │
│               │                 │          │              │                                   │               │ crafted tar header with large entry...                       │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-9538                    │
├───────────────┼─────────────────┤          ├──────────────┼───────────────────────────────────┼───────────────┼──────────────────────────────────────────────────────────────┤
│ util-linux    │ CVE-2026-76642  │          │ affected     │ 2.41.5-0+deb13u1                  │               │ util-linux: util-linux: failed external mount helper still   │
│               │                 │          │              │                                   │               │ runs privileged X-mount post-hooks                           │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408  │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root     │
│               │                 │          │              │                                   │               │ cgroup migration authority                                   │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78409  │          │              │                                   │               │ util-linux: util-linux: X-mount.subdir detached-tree         │
│               │                 │          │              │                                   │               │ resolution can escape via intermediate symlinks              │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78409                   │
│               ├─────────────────┤          │              │                                   ├───────────────┼──────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78410  │          │              │                                   │               │ util-linux: util-linux: restricted bind mounts do not pin    │
│               │                 │          │              │                                   │               │ the source, allowing X-mount.owner/group/mode...             │
│               │                 │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78410                   │
└───────────────┴─────────────────┴──────────┴──────────────┴───────────────────────────────────┴───────────────┴──────────────────────────────────────────────────────────────┘

📣 [34mNotices:[0m
  - Version 0.76.2 of Trivy is now available, current version is 0.69.3

To suppress version checks, run Trivy scans with the --skip-version-check flag
```


**Notes on findings:** Trivy reports **47 HIGH/CRITICAL findings**, all listed below with the reason they remain. None are in the Python packages the API installs; all come from Debian packages in the `python:3.12-slim` base image.

| Package | Findings | Debian status | Fixed version | Note |
|---|---|---|---|---|
| bsdutils | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libacl1 | 1 (CVE-2026-54369) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libblkid1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| liblastlog2-2 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libmount1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libncursesw6 | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libsmartcols1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libsqlite3-0 | 3 (CVE-2026-119373, CVE-2026-119374, CVE-2026-119379) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libsystemd0 | 1 (CVE-2026-16742) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libtinfo6 | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libudev1 | 1 (CVE-2026-16742) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| libuuid1 | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| login | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| mount | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| ncurses-base | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| ncurses-bin | 1 (CVE-2025-69720) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |
| perl-base | 1 (CVE-2026-9538) | fix_deferred | - | Debian decided to defer the fix (low impact in Debian's assessment); nothing to upgrade to yet. Rescan regularly. |
| util-linux | 4 (CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410) | affected | - | Debian has not released a fixed package yet; nothing to upgrade to. Rebuild with `docker build --pull` and rescan when a fix appears. |

Action taken: the runtime stage of `Dockerfile.prod` runs `apt-get update && apt-get upgrade -y`, which installs every Debian security fix that exists today, and the image was rebuilt and rescanned. The remaining findings have no fix available yet; the plan is to rebuild with `docker build --pull` and rescan weekly.


## 7. Image published as `<user>/loan-api:1.0.0` and `:latest`

Docker Hub repository: https://hub.docker.com/r/ounmengheang/loan-api (tags `1.0.0` and `latest`). The local copies were deleted and `1.0.0` was pulled and run straight from Docker Hub; the prediction answers HTTP 200.

```text
$ docker build -q -t loan-api:prod -f Dockerfile.prod . && docker tag loan-api:prod ounmengheang/loan-api:1.0.0 && docker tag loan-api:prod ounmengheang/loan-api:latest && docker images ounmengheang/loan-api
sha256:404f5e28d2341469cbfb1ee221aba7b7ef0cf1a70c3c190d740a3caa87583c57
IMAGE                          ID             DISK USAGE   CONTENT SIZE   EXTRA
ounmengheang/loan-api:1.0.0    404f5e28d234        778MB          178MB        
ounmengheang/loan-api:latest   404f5e28d234        778MB          178MB
```

```text
$ docker push ounmengheang/loan-api:1.0.0
The push refers to repository [docker.io/ounmengheang/loan-api]
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
44136fa355b3: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Mounted from library/postgres
2dc99d2d0a39: Waiting
2dc99d2d0a39: Waiting
44136fa355b3: Pushed
05e0eee5572e: Waiting
2dc99d2d0a39: Waiting
af47a5177b3e: Pushed
9178e1754d57: Waiting
05e0eee5572e: Waiting
2dc99d2d0a39: Waiting
ce6880a286ef: Waiting
9178e1754d57: Waiting
05e0eee5572e: Waiting
2dc99d2d0a39: Waiting
ce6880a286ef: Waiting
9178e1754d57: Waiting
05e0eee5572e: Waiting
ce6880a286ef: Waiting
ce6880a286ef: Waiting
9178e1754d57: Waiting
05e0eee5572e: Waiting
9178e1754d57: Waiting
05e0eee5572e: Waiting
ce6880a286ef: Waiting
ce6880a286ef: Waiting
9fc40e2bd146: Waiting
68bced9e0afa: Pushed
783ce558e5cf: Waiting
05e0eee5572e: Pushed
9fc40e2bd146: Waiting
783ce558e5cf: Waiting
ce6880a286ef: Pushed
9fc40e2bd146: Waiting
8e36e79ddbf9: Waiting
783ce558e5cf: Waiting
783ce558e5cf: Waiting
9fc40e2bd146: Waiting
8e36e79ddbf9: Waiting
8e36e79ddbf9: Waiting
783ce558e5cf: Waiting
9fc40e2bd146: Waiting
8e36e79ddbf9: Waiting
783ce558e5cf: Waiting
9fc40e2bd146: Waiting
8e36e79ddbf9: Waiting
8e36e79ddbf9: Waiting
9178e1754d57: Pushed
045bc75b48e9: Waiting
045bc75b48e9: Waiting
045bc75b48e9: Waiting
045bc75b48e9: Waiting
045bc75b48e9: Waiting
783ce558e5cf: Pushed
045bc75b48e9: Waiting
8e36e79ddbf9: Pushed
2dc99d2d0a39: Pushed
045bc75b48e9: Pushed
9fc40e2bd146: Pushed
1.0.0: digest: sha256:404f5e28d2341469cbfb1ee221aba7b7ef0cf1a70c3c190d740a3caa87583c57 size: 856
```

```text
$ docker push ounmengheang/loan-api:latest
The push refers to repository [docker.io/ounmengheang/loan-api]
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
68bced9e0afa: Waiting
44136fa355b3: Waiting
af47a5177b3e: Waiting
37fb86c2a767: Waiting
37fb86c2a767: Waiting
2dc99d2d0a39: Waiting
05e0eee5572e: Waiting
68bced9e0afa: Waiting
44136fa355b3: Already exists
af47a5177b3e: Already exists
37fb86c2a767: Waiting
2dc99d2d0a39: Waiting
05e0eee5572e: Waiting
68bced9e0afa: Waiting
68bced9e0afa: Waiting
9178e1754d57: Waiting
ce6880a286ef: Waiting
37fb86c2a767: Layer already exists
2dc99d2d0a39: Waiting
05e0eee5572e: Waiting
ce6880a286ef: Waiting
2dc99d2d0a39: Waiting
05e0eee5572e: Waiting
68bced9e0afa: Waiting
9178e1754d57: Waiting
045bc75b48e9: Waiting
ce6880a286ef: Layer already exists
05e0eee5572e: Layer already exists
9fc40e2bd146: Waiting
8e36e79ddbf9: Waiting
68bced9e0afa: Layer already exists
9178e1754d57: Layer already exists
783ce558e5cf: Waiting
2dc99d2d0a39: Layer already exists
783ce558e5cf: Waiting
045bc75b48e9: Waiting
9fc40e2bd146: Waiting
8e36e79ddbf9: Waiting
9fc40e2bd146: Layer already exists
8e36e79ddbf9: Layer already exists
783ce558e5cf: Layer already exists
045bc75b48e9: Layer already exists
latest: digest: sha256:404f5e28d2341469cbfb1ee221aba7b7ef0cf1a70c3c190d740a3caa87583c57 size: 856
```

```text
$ docker rmi ounmengheang/loan-api:1.0.0; docker images ounmengheang/loan-api
Untagged: ounmengheang/loan-api:1.0.0
Deleted: sha256:404f5e28d2341469cbfb1ee221aba7b7ef0cf1a70c3c190d740a3caa87583c57
IMAGE   ID             DISK USAGE   CONTENT SIZE   EXTRA
```

```text
$ docker run -d --name fromhub -p 8000:8000 ounmengheang/loan-api:1.0.0
Unable to find image 'ounmengheang/loan-api:1.0.0' locally
1.0.0: Pulling from ounmengheang/loan-api
045bc75b48e9: Pulling fs layer
37fb86c2a767: Pulling fs layer
68bced9e0afa: Pulling fs layer
2dc99d2d0a39: Pulling fs layer
05e0eee5572e: Pulling fs layer
9178e1754d57: Pulling fs layer
ce6880a286ef: Pulling fs layer
783ce558e5cf: Pulling fs layer
9fc40e2bd146: Pulling fs layer
8e36e79ddbf9: Pulling fs layer
8e36e79ddbf9: Already exists
68bced9e0afa: Already exists
2dc99d2d0a39: Already exists
783ce558e5cf: Already exists
9fc40e2bd146: Already exists
045bc75b48e9: Already exists
37fb86c2a767: Already exists
05e0eee5572e: Already exists
9178e1754d57: Already exists
ce6880a286ef: Already exists
44136fa355b3: Already exists
af47a5177b3e: Download complete
Digest: sha256:404f5e28d2341469cbfb1ee221aba7b7ef0cf1a70c3c190d740a3caa87583c57
Status: Downloaded newer image for ounmengheang/loan-api:1.0.0
6f096256d0252cf0228151469cee20cfae65ab6406ac821be336ca117f6b666e
```

```text
$ curl -s -w '\nHTTP %{http_code}\n' -X POST http://localhost:8000/api/v1/predictions -H 'Content-Type: application/json' -d '{"amount_usd":1500,"term_months":12,"monthly_income_usd":350,"previous_loans":1,"late_payments":0}'
{"default_probability":0.095,"risk_band":"low","model_version":"1.0.0"}
HTTP 200
```


## Secrets

No secrets are in the image or the repository. The only password is the development-only `POSTGRES_PASSWORD: loans_dev_only` in `compose.yaml`, which the task allows. The Docker Hub login used an access token entered in the terminal, never written to a file.
