import json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.v07_official import discover_official_file, sha256, audit_file, standardize, reconcile
from scripts.parse.csi_constituents_parser import parse_csi_file_detailed

def test_real_official_ingestion():
    p=discover_official_file(ROOT)
    if p is None: pytest.skip('REAL_OFFICIAL_FILE_NOT_PRESENT')
    d=parse_csi_file_detailed(p, source_origin='OFFICIAL')
    assert d['validation']['parsed_rows']>0

def test_official_source_origin():
    p=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    d=parse_csi_file_detailed(p, source_origin='OFFICIAL')
    assert {r['source_origin'] for r in d['records']}=={'OFFICIAL'}

def test_sha256_recorded(tmp_path):
    p=tmp_path/'a.xls'; p.write_bytes(b'abc')
    assert audit_file(p)['sha256']=='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

def test_official_row_count():
    p=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    d=parse_csi_file_detailed(p, source_origin='OFFICIAL')
    assert d['validation']['parsed_rows']==300

def test_official_duplicate_detection(tmp_path):
    from openpyxl import Workbook
    p=tmp_path/'dup.xlsx'; wb=Workbook(); ws=wb.active; ws.append(['说明']); ws.append(['代码','名称','权重']); ws.append(['600519','A','1']); ws.append(['600519','B','1']); wb.save(p)
    d=parse_csi_file_detailed(p, source_origin='OFFICIAL')
    assert d['validation']['duplicate_rows']==1

def test_official_code_normalization():
    p=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    d=parse_csi_file_detailed(p, source_origin='OFFICIAL')
    assert d['records'][0]['ticker'].isdigit() and len(d['records'][0]['ticker'])==6

def test_official_exchange_mapping():
    p=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    d=parse_csi_file_detailed(p, source_origin='OFFICIAL')
    by={r['ticker']:r['exchange_mic'] for r in d['records']}
    assert by['600000']=='XSHG' and by['300149']=='XSHE'

def test_official_weight_validation():
    p=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    d=parse_csi_file_detailed(p, source_origin='OFFICIAL')
    vals=[r['weight'] for r in d['records'] if r['weight'] is not None]
    assert all(v>=0 for v in vals)

def test_official_secondary_reconciliation():
    official=standardize([{'ticker':'600519','source_ticker':'600519','name':'贵州茅台','weight':6.04,'exchange_mic':'XSHG','effective_from':None,'effective_to':None}])
    p=ROOT/'data/current/constituents/CSI300__current.json'
    r=reconcile(official,p)
    assert r['both_same']+r['both_different']+r['official_only']+r['secondary_only']>=1

def test_official_current_history_guard():
    p=ROOT/'data/current/constituents/CSI300__current.json'
    d=json.loads(p.read_text())
    assert d.get('source_id','SRC-CSI300-SECONDARY') != 'SRC-CSI-OFFICIAL'

def test_official_lineage_schema():
    p=ROOT/'reports/lineage/csi300_stock_lineage.json'
    d=json.loads(p.read_text())
    assert 'records' in d and d['records']
    assert all('security_id' in r and 'listing_id' in r for r in d['records'])

def test_ingestion_receipt_schema():
    receipts=list((ROOT/'reports/ingestion').glob('*ingestion_receipt.json'))
    if not receipts:
        pytest.skip('REAL_OFFICIAL_FILE_NOT_PRESENT')
    d=json.loads(receipts[-1].read_text())
    assert 'sha256' in d and 'input_origin' in d and 'publish_gate' in d

def test_v07_data_version_separated():
    d=json.loads((ROOT/'data-version.json').read_text())
    assert d['data_version']=='DATA-2026-W39'
    assert d['software_version']=='1.3.0'

def test_fixture_never_counts_as_official():
    d=parse_csi_file_detailed(ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls', source_origin='FIXTURE')
    assert all(r['source_origin']=='FIXTURE' for r in d['records'])
