import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_data_and_software_versions_are_separate():
 d=json.loads((ROOT/'data-version.json').read_text())
 assert d['data_version']=='DATA-2026-W39'
 assert d['software_version']=='1.3.0'
 assert '-V0.5' not in d['data_version']

def test_access_report_is_structured():
 d=json.loads((ROOT/'reports/quality/csi300_constituent_access_report.json').read_text())
 assert d['target']==300
 assert d['access_status'] in {'AVAILABLE','NETWORK_ERROR','HTTP_ERROR','ACCESS_BLOCKED','CONTENT_TYPE_UNEXPECTED','EMPTY_RESPONSE'}

def test_official_capability_matrix():
 d=json.loads((ROOT/'reports/quality/source_capability_matrix.json').read_text())
 ids={x['source_id'] for x in d}
 assert {'SRC-CSI-OFFICIAL','SRC-SSE-OFFICIAL','SRC-SZSE-OFFICIAL'} <= ids

def test_listing_exchange_and_normalized_ticker():
 d=json.loads((ROOT/'data/standardized/listing_master.json').read_text())
 for x in d:
  assert x['exchange_mic'] in {'XSHG','XSHE'}
  assert x['normalized_ticker']==f"CN-{x['exchange_mic']}-{x['ticker']}"

def test_raw_metadata_and_manifest():
 m=json.loads((ROOT/'MANIFEST.sha256.json').read_text())
 assert m['data_version']=='DATA-2026-W39'
 assert all(len(x['sha256'])==64 for x in m['files'])
 assert any('SRC-CSI300-SECONDARY' in x['file'] for x in m['files'])
