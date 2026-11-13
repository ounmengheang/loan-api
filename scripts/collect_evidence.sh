#!/usr/bin/env bash
# Collect the evidence for CHECKLIST.md (requirements 1-6). Run from the repo root:
#   bash scripts/collect_evidence.sh
# Every command and its output is saved in evidence/NN_name.txt.
set -u
cd "$(dirname "$0")/.."
mkdir -p evidence

run() {  # run NAME COMMAND...  -> prints and saves "$ COMMAND" followed by its output
  local name=$1; shift
  { echo "\$ $*"; bash -c "$*" 2>&1; } | tee "evidence/$name.txt"
}

docker rm -f prod prod110 >/dev/null 2>&1
docker compose down >/dev/null 2>&1

# Requirement 1: multi-stage Dockerfile.prod, slim base, non-root user, HEALTHCHECK
run 01_dockerfile_prod "grep -nE '^(FROM|USER|HEALTHCHECK)' Dockerfile.prod"
run 02_build_prod "docker build -t loan-api:prod -f Dockerfile.prod . 2>&1 | tail -n 12"
run 03_run_prod "docker run -d --name prod -p 8000:8000 loan-api:prod"
sleep 5
run 04_whoami "docker exec prod whoami"
sleep 35
run 05_healthy "docker ps --filter name=prod --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"
docker rm -f prod >/dev/null

# Requirement 2: .dockerignore
run 06_dockerignore "cat .dockerignore"

# Requirement 3: model path configurable with MODEL_PATH (serve a 1.1.0 model without rebuilding)
run 07_train_110 "python train.py --version 1.1.0 --out models/model.joblib"
run 08_run_110 "docker run -d --name prod110 -p 8001:8000 -v \"\$(pwd)/models:/models:ro\" -e MODEL_PATH=/models/model.joblib loan-api:prod"
sleep 10
run 09_health_110 "curl -s http://localhost:8001/health; echo"
docker rm -f prod110 >/dev/null

# Requirement 4: compose.yaml runs API + PostgreSQL + Adminer, API built from Dockerfile.prod
run 10_compose_build "grep -nA3 'build:' compose.yaml"
run 11_compose_up "docker compose up -d --build 2>&1 | tail -n 8"
sleep 40
run 12_compose_ps "docker compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
run 13_compose_health "curl -s http://localhost:8000/health; echo"
docker compose down >/dev/null 2>&1

# Requirement 5: image at least 40% smaller than the full-Python variant
sed 's/^FROM python:3.12-slim/FROM python:3.12/' Dockerfile > Dockerfile.full
run 14_build_full "docker build -t loan-api:full -f Dockerfile.full . 2>&1 | tail -n 3"
run 15_build_slim "docker build -t loan-api:slim -f Dockerfile . 2>&1 | tail -n 3"
run 16_images "docker images loan-api"
run 17_size_ratio "python3 -c \"import subprocess as s; z=lambda t: int(s.check_output(['docker','image','inspect','-f','{{.Size}}','loan-api:'+t])); f,p=z('full'),z('prod'); print(f'full = {f/1e6:.0f} MB, prod = {p/1e6:.0f} MB, prod is {100*(1-p/f):.0f}% smaller than full')\""

# Requirement 6: vulnerability scan (Trivy pinned to 0.69.3, see GHSA-69fq-xp46-6x23)
run 18_trivy "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache aquasec/trivy:0.69.3 image --severity HIGH,CRITICAL --no-progress loan-api:prod"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache aquasec/trivy:0.69.3 image --severity HIGH,CRITICAL --format json --quiet loan-api:prod > evidence/18_trivy.json
python3 scripts/trivy_notes.py evidence/18_trivy.json

echo "Evidence for requirements 1-6 saved in evidence/"
