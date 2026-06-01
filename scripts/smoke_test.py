import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

for f in ["customer_profiles.csv", "merchant_risk.csv", "fds_rules.csv"]:
    path = os.path.join(DATA, f)
    if not os.path.exists(path):
        print("[warn]", f, "없음 -> drive에서 data/ 로 복사")

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

from services.investigate import sample_transaction
from src.api_interface import investigate_transaction
from src.schemas import TransactionInput

tx = sample_transaction()
print("run:", tx["trans_num"])

try:
    res = investigate_transaction(TransactionInput.model_validate(tx)).model_dump()
except Exception as e:
    print("fail:", e)
    sys.exit(1)

print("risk_level:", res.get("risk_level"))
print("action:", res.get("action_decision"))
print("rule_score:", res.get("rule_score"))
print("rule_hits:", res.get("rule_hits"))
print("ml_score:", res.get("ml_score"))
rpt = res.get("report") or ""
print("report:", rpt[:150] + "..." if len(rpt) > 150 else rpt)
print("ok")
