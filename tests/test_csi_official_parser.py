import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.parse.csi_constituents_parser import parse_csi_file, normalize_code, map_exchange, parse_weight

def test_xls_can_be_parsed():
    rows=parse_csi_file(ROOT/'tests/fixtures/xls/csi300_parser_fixture.xls')
    assert len(rows)==300

def test_300_rows_detected():
    rows=parse_csi_file(ROOT/'tests/fixtures/csi300_parser_fixture.xlsx')
    assert len(rows)==300

def test_code_normalization():
    assert normalize_code('600519.0')=='600519'
    assert normalize_code('SZSE:000333')=='000333'

def test_duplicate_code_detection(tmp_path):
    from openpyxl import Workbook
    p=tmp_path/'dup.xlsx'; wb=Workbook(); ws=wb.active; ws.append(['代码','名称','权重'])
    ws.append(['600519','A','1']); ws.append(['600519','B','1']); wb.save(p)
    import pytest
    with pytest.raises(ValueError, match='duplicate security codes'):
        parse_csi_file(p)

def test_exchange_mapping():
    assert map_exchange('600519')=='XSHG'
    assert map_exchange('000333')=='XSHE'
    assert map_exchange('600519','SZSE')=='XSHE'

def test_weight_numeric_conversion():
    assert parse_weight('6.04%')==6.04
    assert parse_weight('1,234.5')==1234.5
