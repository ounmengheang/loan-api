"""Move an alias of loan-default to a version:  python scripts/set_alias.py champion 2"""
import sys

from mlflow import MlflowClient

NAME = "loan-default"
alias, version = sys.argv[1], sys.argv[2]
client = MlflowClient()
before = client.get_registered_model(NAME).aliases
client.set_registered_model_alias(NAME, alias, version)
after = client.get_registered_model(NAME).aliases
print(f"{NAME} aliases before: {dict(sorted(before.items()))}")
print(f"{NAME} aliases after:  {dict(sorted(after.items()))}")
