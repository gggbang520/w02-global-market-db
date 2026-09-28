from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def coverage(records):
 dates={r.get('trade_date') for r in records if r.get('trade_date')}; listings={r.get('listing_id') for r in records if r.get('listing_id')}
 target=300
 return {'target_constituents':target,'mapped_constituents':len(listings),'price_records':len(records),'distinct_listings':len(listings),'distinct_trade_dates':len(dates),'total_rows':len(records),'latest_trade_date':max(dates) if dates else None,'coverage_rate':len(listings)/target,'missing_count':max(0,target-len(listings))}
