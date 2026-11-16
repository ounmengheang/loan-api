"""Pick champion and challenger from the tracked runs, register both under loan-default and set aliases.

Decision rule (the lender's priorities): missing a defaulter costs far more than double-checking a good
borrower, so the champion is the run with the highest recall among runs with precision >= 0.60 and
AUC >= 0.90 (ties broken by AUC). The challenger is the best remaining run by AUC.
"""
import json
from pathlib import Path

import mlflow
from mlflow import MlflowClient

NAME = "loan-default"
runs = json.loads(Path("evidence5/runs.json").read_text())

eligible = [r for r in runs if r["precision"] >= 0.60 and r["auc"] >= 0.90]
champion = max(eligible, key=lambda r: (r["recall"], r["auc"]))
challenger = max((r for r in runs if r["run_id"] != champion["run_id"]), key=lambda r: (r["auc"], r["recall"]))

client = MlflowClient()
registered = {}
for role, run in (("champion", champion), ("challenger", challenger)):
    mv = mlflow.register_model(run["model_uri"], NAME)
    description = (f"{run['run_name']}: AUC {run['auc']}, recall {run['recall']}, precision {run['precision']}. "
                   + ("Champion: highest recall with precision >= 0.60 (catches the most defaulters)."
                      if role == "champion" else "Challenger: highest AUC of the other runs (best overall ranking)."))
    client.update_model_version(NAME, mv.version, description=description)
    client.set_registered_model_alias(NAME, role, mv.version)
    registered[role] = {"version": mv.version, **run}
    print(f"{role:<10} -> {NAME} version {mv.version}: {run['run_name']} "
          f"(auc={run['auc']}, recall={run['recall']}, precision={run['precision']})")

Path("evidence5/registry.json").write_text(json.dumps(registered, indent=2))
model = client.get_registered_model(NAME)
print("aliases:", dict(sorted(model.aliases.items())))
for v in client.search_model_versions(f"name='{NAME}'"):
    print(f"version {v.version}: run {v.run_id[:8]}..., description: {v.description}")
