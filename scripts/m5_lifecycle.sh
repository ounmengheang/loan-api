#!/usr/bin/env bash
# Module 5 project: run the whole model lifecycle and save every command with its output in evidence5/.
#   bash scripts/m5_lifecycle.sh
# Leaves three programs running: tracking server :5000, MLflow scoring server :5001, FastAPI :8000.
set -u
cd "$(dirname "$0")/.."
mkdir -p evidence5 logs
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000

run() {  # run NAME COMMAND...  -> prints and saves "$ COMMAND" followed by its output
  local name=$1; shift
  { echo "\$ $*"; bash -c "$*" 2>&1; } | tee "evidence5/$name.txt"
}
wait_for() {  # wait_for URL
  for _ in $(seq 1 90); do curl -sf "$1" >/dev/null && return 0; sleep 2; done
  echo "timed out waiting for $1"; return 1
}
start_api() {  # (re)start FastAPI so it loads whatever @champion points to now
  pkill -f "fastapi run main.py" 2>/dev/null; sleep 2
  nohup fastapi run main.py --port 8000 > logs/api.log 2>&1 &
  wait_for http://127.0.0.1:8000/health
}
A1='{"amount_usd": 1500, "term_months": 12, "monthly_income_usd": 350.0, "previous_loans": 1, "late_payments": 0}'
A2='{"amount_usd": 4800, "term_months": 6, "monthly_income_usd": 250.0, "previous_loans": 0, "late_payments": 3}'

pkill -f "mlflow models serve" 2>/dev/null; pkill -f "fastapi run main.py" 2>/dev/null; pkill -f "mlflow server" 2>/dev/null; sleep 2

# Terminal 1: tracking server (Lesson 5.1)
nohup mlflow server --host 127.0.0.1 --port 5000 \
  --backend-store-uri sqlite:///mlflow.db \
  --artifacts-destination ./mlartifacts \
  --allowed-hosts "localhost:*,127.0.0.1:*,*.app.github.dev" \
  --cors-allowed-origins "https://*.app.github.dev" > logs/mlflow_server.log 2>&1 &
wait_for http://127.0.0.1:5000/health

# Step 1: experiment (six runs, two model types)
run 01_train "python train_tracked.py 2>&1 | grep -vE 'Warning|warn|^ *$'"
run 02_runs_table "python scripts/runs_table.py"

# Step 2: register the two best candidates, set champion/challenger and descriptions
run 03_register "python register.py"
run 04_load_alias "python load_alias.py"

# Step 4a: MLflow scoring server for @champion (terminal 2)
nohup mlflow models serve -m "models:/loan-default@champion" -p 5001 --env-manager local > logs/serve.log 2>&1 &
wait_for http://127.0.0.1:5001/ping
run 05_serve_two_applicants "curl -s http://127.0.0.1:5001/invocations -H 'Content-Type: application/json' -d '{\"dataframe_records\": [$A1, $A2]}'; echo"
run 06_serve_missing_column "curl -s http://127.0.0.1:5001/invocations -H 'Content-Type: application/json' -d '{\"dataframe_records\": [{\"amount_usd\": 1500, \"term_months\": 12, \"monthly_income_usd\": 350.0, \"previous_loans\": 1, \"late_payment\": 0}]}'; echo"
run 07_serve_text_number "curl -s http://127.0.0.1:5001/invocations -H 'Content-Type: application/json' -d '{\"dataframe_records\": [{\"amount_usd\": \"1500\", \"term_months\": 12, \"monthly_income_usd\": 350.0, \"previous_loans\": 1, \"late_payments\": 0}]}'; echo"
run 08_serve_bad_text "curl -s http://127.0.0.1:5001/invocations -H 'Content-Type: application/json' -d '{\"dataframe_records\": [{\"amount_usd\": \"fifteen hundred\", \"term_months\": 12, \"monthly_income_usd\": 350.0, \"previous_loans\": 1, \"late_payments\": 0}]}'; echo"

# Step 4b: FastAPI loan service loading models:/loan-default@champion (terminal 3)
start_api
run 09_api_health "curl -s http://127.0.0.1:8000/health; echo"
run 10_api_predict "curl -s -X POST http://127.0.0.1:8000/api/v1/predictions -H 'Content-Type: application/json' -d '$A1'; echo"
run 11_compare "python scripts/compare.py"

# Step 5: monitor 14 days of drift
run 12_psi_demo "python psi.py"
run 13_monitor "python monitor.py"
run 14_drift_table "python scripts/drift_chart.py"

# Step 6: roll back drill: move champion to the other version, restart FastAPI, check; then move it back
CHAMP=$(python3 -c "import json; print(json.load(open('evidence5/registry.json'))['champion']['version'])")
CHALL=$(python3 -c "import json; print(json.load(open('evidence5/registry.json'))['challenger']['version'])")
run 15_health_before "curl -s http://127.0.0.1:8000/health; echo; curl -s -X POST http://127.0.0.1:8000/api/v1/predictions -H 'Content-Type: application/json' -d '$A1'; echo"
run 16_move_champion "python scripts/set_alias.py champion $CHALL"
start_api
run 17_health_after_move "curl -s http://127.0.0.1:8000/health; echo; curl -s -X POST http://127.0.0.1:8000/api/v1/predictions -H 'Content-Type: application/json' -d '$A1'; echo"
run 18_move_back "python scripts/set_alias.py champion $CHAMP"
start_api
run 19_health_after_rollback "curl -s http://127.0.0.1:8000/health; echo; curl -s -X POST http://127.0.0.1:8000/api/v1/predictions -H 'Content-Type: application/json' -d '$A1'; echo"

echo "Done. Evidence in evidence5/. Running: tracking :5000, scoring :5001, FastAPI :8000"
