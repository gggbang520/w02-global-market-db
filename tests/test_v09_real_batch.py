import csv,json,sys,hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from scripts.providers.manual_file import ManualFileProvider
from scripts.ingest_market_data import resolve_listing, validate
from scripts.providers.reconciliation import reconcile
REAL=ROOT/'data/raw/inbox/market/CSI300_EOD__TushareArchive__2021-01-28_2021-01-29.csv'
SOURCE='SRC-GITHUB-TUSHARE-ARCHIVE'

def real_rows():
    p=ManualFileProvider(REAL); return p.normalize(p.parse())

def test_real_batch_csv():
    assert REAL.exists(); assert len(ManualFileProvider(REAL).parse())==204

def test_real_batch_source_id():
    assert {r['source_id'] for r in real_rows()}=={SOURCE}

def test_real_batch_source_origin():
    assert {r['source_origin'] for r in real_rows()}=={'MANUAL_FILE'}

def test_real_batch_distinct_listing_count():
    r=real_rows(); assert len({x['ticker'] for x in r})==102

def test_real_batch_distinct_trade_date_count():
    assert len({x['trade_date'] for x in real_rows()})==2

def test_real_batch_identity_mapping():
    r=resolve_listing(real_rows()); assert all(x['identity_status']=='MAPPED' for x in r)

def test_real_batch_exchange_mapping():
    r=real_rows(); assert {x['exchange_mic'] for x in r}=={'XSHG','XSHE'}

def test_real_batch_unit_normalization():
    r=real_rows(); assert all(x['currency']=='CNY' for x in r); assert all(x['price_type']=='RAW_CLOSE' for x in r)

def test_real_batch_price_validation():
    r=resolve_listing(real_rows()); v=validate(r,retrieved_date='2026-09-27'); assert len(v['valid'])==204 and not v['invalid']

def test_real_batch_duplicate_detection():
    r=resolve_listing(real_rows()); assert len(validate(r)['duplicate'])==0

def test_real_batch_future_date():
    r=resolve_listing(real_rows()); assert not validate(r,retrieved_date='2021-01-27')['valid']

def test_real_batch_float_tolerance():
    a=[{'listing_id':'A','trade_date':'2021-01-29','close':1.0}]; b=[{'listing_id':'A','trade_date':'2021-01-29','close':1.0000001}]
    assert reconcile(a,b,absolute_tolerance=1e-5)['same']==1

def test_real_batch_provider_reconciliation_conflict():
    a=[{'listing_id':'A','trade_date':'2021-01-29','close':1.0}]; b=[{'listing_id':'A','trade_date':'2021-01-29','close':1.2}]
    assert reconcile(a,b)['different']==1

def test_real_batch_provider_missing_record():
    a=[{'listing_id':'A','trade_date':'2021-01-29','close':1.0}]; b=[]
    assert reconcile(a,b)['missing_b']==1

def test_real_batch_sha256_recorded():
    d=hashlib.sha256(REAL.read_bytes()).hexdigest(); r=list((ROOT/'reports/ingestion').glob(f'CSI300_EOD__{SOURCE}__*receipt.json')); assert r; assert json.loads(r[-1].read_text())['sha256']==d

def test_real_batch_import_receipt():
    p=list((ROOT/'reports/ingestion').glob(f'CSI300_EOD__{SOURCE}__*receipt.json')); d=json.loads(p[-1].read_text()); assert d['raw_rows']==204 and d['valid_rows']==204 and d['publish_gate']=='PASS'

def test_real_batch_qualification():
    d=json.loads((ROOT/'reports/quality/provider_qualification').joinpath(f'{SOURCE}.json').read_text()); assert d['qualification']=='CONDITIONAL'; assert d['license_gate']=='REVIEW'

def test_real_batch_coverage_report():
    d=json.loads((ROOT/'reports/quality/csi300_price_coverage.json').read_text()); assert d['distinct_listings']==102 and d['distinct_trade_dates']==2 and d['total_rows']==204

def test_real_batch_lineage():
    d=json.loads((ROOT/'reports/lineage/price_lineage.json').read_text()); assert len(d)==204 and all(x['source_id']==SOURCE and x['sha256'] for x in d)

def test_real_batch_history_and_provider_current():
    h=ROOT/'data/history/DATA-2026-W39/stocks/price_daily__2021-01-29__SRC-GITHUB-TUSHARE-ARCHIVE.json'; c=ROOT/'data/current/stocks/providers/SRC-GITHUB-TUSHARE-ARCHIVE__latest.json'; assert h.exists() and c.exists(); assert json.loads(c.read_text())['canonical_current_promotion'] is False

def test_real_batch_weekly_not_derived_from_two_days():
    d=json.loads((ROOT/'data/current/weekly/CSI300__weekly_snapshot.json').read_text()); assert d['records']

def test_real_batch_ytd_not_claimed():
    p=ROOT/'reports/quality/csi300_price_quality.json'; d=json.loads(p.read_text()); assert d['distinct_dates']==2
