import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
items=json.loads((ROOT/"data/current/constituents/CSI300__current.json").read_text())["constituents"]
assert len(items)==297 and len({x["listing_id"] for x in items})==297
for x in items: assert x["effective_from"] is None or x["effective_from"] <= (x["effective_to"] or "9999-12-31")
for p in ROOT.glob("data/standardized/stocks/*.json"):
 x=json.loads(p.read_text()); assert x["high"]>=x["low"] and x["high"]>=x["open"] and x["high"]>=x["close"] and x["low"]<=x["open"] and x["low"]<=x["close"] and x["close"]>=0 and x["volume"]>=0
print("CSI300 VALIDATION PASS")
