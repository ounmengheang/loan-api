"""Send the same applicant to the MLflow scoring server and to FastAPI and compare the probabilities."""
import json
import urllib.request as u

A1 = {"amount_usd": 1500, "term_months": 12, "monthly_income_usd": 350.0, "previous_loans": 1, "late_payments": 0}


def post(url, body):
    req = u.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(u.urlopen(req))


mlflow_p = post("http://127.0.0.1:5001/invocations", {"dataframe_records": [A1]})["predictions"][0][1]
api = post("http://127.0.0.1:8000/api/v1/predictions", A1)
print(f"MLflow scoring server (port 5001): P(default) = {mlflow_p:.6f} -> rounded {round(mlflow_p, 3)}")
print(f"FastAPI (port 8000): default_probability = {api['default_probability']}, model_version = {api['model_version']}")
print("same probability:", round(mlflow_p, 3) == api["default_probability"])
