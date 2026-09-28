import json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from scripts.providers.base import MarketDataProvider
from scripts.providers.manual_file import ManualFileProvider
from scripts.providers.price_quality import coverage
from scripts.providers.reconciliation import reconcile
from scripts.providers.market_schema import validate_schema, SCHEMA_VERSION
from scripts.ingest_market_data import validate, sha256, resolve_listing

FIX=ROOT/'tests/fixtures/market'

def test_csv_ingestion():
 p=FIX/'sample.csv'; rows=ManualFileProvider(p).parse(); assert len(rows)==2

def test_xlsx_ingestion():
 p=FIX/'sample.xlsx'; rows=ManualFileProvider(p).parse(); assert len(rows)==2

def test_json_ingestion():
 p=FIX/'sample.json'; rows=ManualFileProvider(p).parse(); assert len(rows)==2

def test_xls_ingestion():
 p=FIX/'sample.xls'
 if not p.exists(): pytest.skip('XLS_FIXTURE_REQUIRES_XLRD')
 assert len(ManualFileProvider(p).parse())==2

def test_batch_distinct_listing_count():
 rows=ManualFileProvider(FIX/'sample.csv').normalize(ManualFileProvider(FIX/'sample.csv').parse()); assert len({(r['ticker'],r['exchange_mic']) for r in rows})==2

def test_listing_mapping():
 from scripts.ingest_market_data import resolve_listing
 rows=ManualFileProvider(FIX/'sample.csv').normalize(ManualFileProvider(FIX/'sample.csv').parse()); out=resolve_listing(rows); assert all(r['identity_status']=='MAPPED' for r in out)

def test_trade_date_validation():
 r=ManualFileProvider(FIX/'sample.csv').normalize(ManualFileProvider(FIX/'sample.csv').parse()); assert validate(r,retrieved_date='2026-09-27')['invalid']==[]

def test_future_trade_date_review():
 r=resolve_listing(ManualFileProvider(FIX/'future.csv').normalize(ManualFileProvider(FIX/'future.csv').parse())); assert validate(r,retrieved_date='2026-09-27')['review'][0]['validation_errors']==['FUTURE_TRADE_DATE']

def test_ohlc_validation():
 r=resolve_listing(ManualFileProvider(FIX/'bad_ohlc.csv').normalize(ManualFileProvider(FIX/'bad_ohlc.csv').parse())); assert validate(r)['invalid'][0]['validation_errors']==['OHLC_INVALID']

def test_volume_validation():
 r=resolve_listing(ManualFileProvider(FIX/'bad_volume.csv').normalize(ManualFileProvider(FIX/'bad_volume.csv').parse())); assert 'VOLUME_INVALID' in validate(r)['invalid'][0]['validation_errors']

def test_duplicate_price_records():
 r=ManualFileProvider(FIX/'duplicate.csv').normalize(ManualFileProvider(FIX/'duplicate.csv').parse()); assert len(validate(r)['duplicate'])==1

def test_price_source_origin():
 p=ManualFileProvider(FIX/'sample.csv'); assert all(x['source_origin']=='MANUAL_FILE' for x in p.normalize(p.parse()))

def test_provider_capability_schema():
 d=json.loads((ROOT/'reports/quality/provider_capability_matrix.json').read_text()); assert all({'source_id','dataset','market','delivery_model','batch','historical','daily','access_status','license_gate','publication_scope'}<=set(x) for x in d)

def test_provider_reconciliation():
 a=[{'listing_id':'LST-CN-1','trade_date':'2026-09-24','open':1,'high':2,'low':1,'close':2,'volume':3,'turnover':4}]; b=[{**a[0],'close':2.1}]; r=reconcile(a,b); assert r['different']==1

def test_license_gate():
 d=json.loads((ROOT/'reports/quality/price_license_gate.json').read_text()); assert d['license_gate'] in {'PASS','REVIEW','UNKNOWN','BLOCKED'}

def test_price_lineage():
 d=json.loads((ROOT/'reports/lineage/price_lineage.json').read_text()); assert isinstance(d,list) and all({'listing_id','trade_date','source_id','source_origin','input_file','parser_version','schema_version','data_version','software_version'}<=set(r) for r in d)

def test_price_coverage_report():
 d=json.loads((ROOT/'reports/quality/csi300_price_coverage.json').read_text()); assert d['target_constituents']==300 and d['distinct_listings']>=4

def test_import_receipt():
 d=json.loads((ROOT/'reports/ingestion/STOCK_DAILY__V08__manual_import_status.json').read_text()); assert d['status'] in {'SUCCESS','NOT_IMPORTED'}

def test_weekly_snapshot_derivation_untouched():
 d=json.loads((ROOT/'data/current/weekly/CSI300__weekly_snapshot.json').read_text()); assert all(r.get('calculation_method')=='derived' for r in d['records'])

def test_batch_not_row_count_coverage():
 rows=[{'listing_id':'A','trade_date':'2026-09-24'},{'listing_id':'A','trade_date':'2026-09-23'},{'listing_id':'B','trade_date':'2026-09-24'}]; c=coverage(rows); assert c['distinct_listings']==2 and c['total_rows']==3

def test_schema_version(): assert SCHEMA_VERSION=='stock_daily_v1'
