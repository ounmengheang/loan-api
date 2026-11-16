"""Print the loan-default experiment table and save a recall/precision comparison chart."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow

runs = mlflow.search_runs(experiment_names=["loan-default"], order_by=["metrics.auc DESC"])
runs = runs[runs["tags.mlflow.runName"].notna()]
tracking = mlflow.get_tracking_uri()
print(f"{'run':<44} {'auc':>6} {'recall':>7} {'precision':>9}  run link")
for _, r in runs.iterrows():
    link = f"{tracking}/#/experiments/{r.experiment_id}/runs/{r.run_id}"
    print(f"{r['tags.mlflow.runName']:<44} {r['metrics.auc']:6.3f} {r['metrics.recall']:7.3f} "
          f"{r['metrics.precision']:9.3f}  {link}")
print(f"{len(runs)} runs, model types: {sorted(runs['params.model'].unique())}")

fig, ax = plt.subplots(figsize=(8, 5))
for _, r in runs.iterrows():
    marker = "o" if r["params.model"] == "logreg" else "s"
    ax.scatter(r["metrics.precision"], r["metrics.recall"], s=80, marker=marker)
    ax.annotate(f"{r['tags.mlflow.runName']}\nAUC {r['metrics.auc']:.3f}",
                (r["metrics.precision"], r["metrics.recall"]), fontsize=7,
                xytext=(6, -4), textcoords="offset points")
ax.axvline(0.60, color="grey", linestyle=":", label="precision floor 0.60")
ax.set_xlabel("precision (share of flagged loans that default)")
ax.set_ylabel("recall (share of defaulters caught)")
ax.set_title("loan-default runs: recall vs precision (circle = logreg, square = forest)")
ax.legend(loc="lower left", fontsize=8)
fig.tight_layout()
fig.savefig("evidence5/runs_comparison.png", dpi=130)
print("chart saved to evidence5/runs_comparison.png")
