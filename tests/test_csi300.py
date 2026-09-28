import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_csi300_constituent_count():
 d=json.loads((ROOT/"data/current/constituents/CSI300__current.json").read_text()); assert d["constituent_count"]==297
def test_company_security_listing_relationship():
 c=json.loads((ROOT/"data/standardized/company_master.json").read_text()); s=json.loads((ROOT/"data/standardized/security_master.json").read_text()); l=json.loads((ROOT/"data/standardized/listing_master.json").read_text());
 assert len(c)==len(s)==len(l)==297
 assert {x["company_id"] for x in c}=={x["company_id"] for x in c}
def test_duplicate_listing():
 l=json.loads((ROOT/"data/standardized/listing_master.json").read_text()); assert len({x["listing_id"] for x in l})==297
def test_price_validation():
 for p in (ROOT/"data/standardized/stocks").glob("*.json"):
  x=json.loads(p.read_text()); assert x["high"]>=x["low"] and x["close"]>=0 and x["volume"]>=0
def test_constituent_effective_dates():
 for x in json.loads((ROOT/"data/current/constituents/CSI300__current.json").read_text())["constituents"]: assert x["effective_from"] is None or x["effective_from"]<="9999-12-31"
def test_lineage_exists():
 d=json.loads((ROOT/"reports/lineage/csi300_stock_lineage.json").read_text()); assert d["count"]==297
def test_current_history_consistency():
 a=json.loads((ROOT/"data/current/constituents/CSI300__current.json").read_text())["constituents"]; b=json.loads((ROOT/"data/history/DATA-2026-W39/constituents/CSI300__current.json").read_text())["constituents"]; assert a==b
