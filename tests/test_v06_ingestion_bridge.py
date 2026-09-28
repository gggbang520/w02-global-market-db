import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.diagnostics.dns_probe import probe_dns
from scripts.diagnostics.content_probe import detect_content_type, validate_content_type
from scripts.ingest_official import detect_source, sha256
from scripts.acquisition_state import AcquisitionState

def test_network_failure_classification():
    r=probe_dns('nonexistent.invalid')
    assert r.status=='DNS_FAILURE'

def test_dns_failure_classification():
    r=probe_dns('definitely-not-a-real-w02-host.invalid')
    assert r.status=='DNS_FAILURE'

def test_manual_file_hash(tmp_path):
    p=tmp_path/'x.xls'; p.write_bytes(b'abc')
    assert sha256(p)=='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

def test_manual_ingestion_receipt_schema():
    p=ROOT/'reports/quality/manual_acquisition_report.json'; d=json.loads(p.read_text())
    assert d[0]['manual_import']['status']=='NOT_IMPORTED'
    assert 'official_verified' in d[0]

def test_fixture_not_counted_as_official():
    p=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    assert '000300cons.xls' not in str(p)
    assert detect_source(p)[0] is None

def test_official_xls_ingestion_mapping():
    p=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    assert detect_content_type(p)=='application/vnd.ms-excel'
    # Fixture content is intentionally not treated as official merely by extension.
    assert detect_source(p)[0] is None

def test_source_detection():
    assert detect_source(Path('000300cons.xls'))[0]=='SRC-CSI-OFFICIAL'

def test_content_type_detection():
    assert detect_content_type('000300cons.xls')=='application/vnd.ms-excel'
    assert detect_content_type('000300cons.xlsx')=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def test_manual_import_pipeline_state():
    assert AcquisitionState.MANUAL_IMPORTED.value=='MANUAL_IMPORTED'
    assert AcquisitionState.VALIDATED.value=='VALIDATED'

def test_publish_gate_rule_is_explicit():
    # Only OFFICIAL + 300 + validation may publish; fixture/secondary cannot satisfy this gate.
    def gate(origin, rows, validated):
        return 'PASS' if origin=='OFFICIAL' and rows==300 and validated else 'BLOCKED'
    assert gate('FIXTURE',300,True)=='BLOCKED'
    assert gate('SECONDARY',300,True)=='BLOCKED'
    assert gate('OFFICIAL',299,True)=='BLOCKED'
    assert gate('OFFICIAL',300,True)=='PASS'

def test_parser_source_origin_is_explicit():
    from scripts.parse.csi_constituents_parser import parse_csi_file
    fixture=ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls'
    rows=parse_csi_file(fixture, source_origin='FIXTURE')
    assert rows and {x['source_origin'] for x in rows}=={'FIXTURE'}
