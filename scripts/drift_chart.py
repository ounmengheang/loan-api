"""Chart the daily-drift-check run with the alert thresholds, and print the daily values."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
from mlflow import MlflowClient

client = MlflowClient()
exp = client.get_experiment_by_name("loan-default-monitoring")
run = client.search_runs([exp.experiment_id], "tags.mlflow.runName = 'daily-drift-check'",
                         order_by=["attributes.start_time DESC"], max_results=1)[0]
keys = ["psi_monthly_income_usd", "psi_amount_usd", "psi_late_payments", "mean_predicted_default", "actual_default_rate"]
hist = {k: {m.step: m.value for m in client.get_metric_history(run.info.run_id, k)} for k in keys}
days = sorted(hist[keys[0]])

print("day  psi_income  psi_amount  psi_late  mean_pred_default  actual_default")
for d in days:
    print(f"{d:>3}  {hist[keys[0]][d]:10.3f}  {hist[keys[1]][d]:10.3f}  {hist[keys[2]][d]:8.3f}  "
          f"{hist[keys[3]][d]:17.3f}  {hist[keys[4]][d]:14.3f}")

over = [d for d in days if hist[keys[0]][d] > 0.2]
streak = next((d for d in days if d - 1 in days and hist[keys[0]][d] > 0.2 and hist[keys[0]][d - 1] > 0.2), None)
print(f"income PSI above 0.2 on days {over}; first 2-day streak above 0.2 ends on day {streak}")
print(f"run link: {mlflow.get_tracking_uri()}/#/experiments/{exp.experiment_id}/runs/{run.info.run_id}")

fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
for k, label in zip(keys[:3], ["monthly_income_usd", "amount_usd", "late_payments"]):
    a1.plot(days, [hist[k][d] for d in days], marker="o", label=f"PSI {label}")
a1.axhline(0.1, color="orange", linestyle="--", label="watch: 0.1")
a1.axhline(0.2, color="red", linestyle="--", label="alert: 0.2 (2 days in a row)")
a1.set_ylabel("PSI vs training data")
a1.set_title("daily-drift-check: 14 simulated days")
a1.legend(fontsize=8)
a2.plot(days, [hist[keys[3]][d] for d in days], marker="o", label="mean predicted default (champion)")
a2.plot(days, [hist[keys[4]][d] for d in days], marker="s", label="actual default rate (simulated)")
a2.set_xlabel("day")
a2.set_ylabel("rate")
a2.legend(fontsize=8)
fig.tight_layout()
fig.savefig("evidence5/drift_chart.png", dpi=130)
print("chart saved to evidence5/drift_chart.png")
