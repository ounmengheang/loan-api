#!/usr/bin/env bash
# Requirement 7: publish the production image to Docker Hub, then prove it runs from the registry.
# Log in first with:  docker login
# Then run:           bash scripts/publish.sh <your-dockerhub-username>
set -u
cd "$(dirname "$0")/.."
DOCKER_USER=${1:?usage: bash scripts/publish.sh <dockerhub-username>}
mkdir -p evidence

run() {
  local name=$1; shift
  { echo "\$ $*"; bash -c "$*" 2>&1; } | tee "evidence/$name.txt"
}

echo "$DOCKER_USER" > evidence/dockerhub_user.txt
run 19_tag "docker build -q -t loan-api:prod -f Dockerfile.prod . && docker tag loan-api:prod $DOCKER_USER/loan-api:1.0.0 && docker tag loan-api:prod $DOCKER_USER/loan-api:latest && docker images $DOCKER_USER/loan-api"
run 20_push_100 "docker push $DOCKER_USER/loan-api:1.0.0"
run 21_push_latest "docker push $DOCKER_USER/loan-api:latest"

# Pull and run from the registry with no local copies
docker compose down >/dev/null 2>&1
run 22_rmi "docker rmi $DOCKER_USER/loan-api:1.0.0 $DOCKER_USER/loan-api:latest loan-api:prod"
run 23_run_from_hub "docker run -d --name fromhub -p 8000:8000 $DOCKER_USER/loan-api:1.0.0"
sleep 10
run 24_predict_from_hub "curl -s -o /dev/stdout -w '\nHTTP %{http_code}\n' -X POST http://localhost:8000/api/v1/predictions -H 'Content-Type: application/json' -d '{\"amount_usd\":1500,\"term_months\":12,\"monthly_income_usd\":350,\"previous_loans\":1,\"late_payments\":0}'"
echo "The container 'fromhub' is still running on port 8000: open /docs, send a prediction, take the screenshot,"
echo "then stop it with: docker rm -f fromhub"
