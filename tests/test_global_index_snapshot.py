import json
from pathlib import Path


def test_snapshot_structure():
    path = Path("reports/index/latest_index_snapshot.json")
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "indices" in data
    assert "source_id" in data
    assert data["source_id"] == "SRC-DERIVED-INDEX-SNAPSHOT"
    for item in data["indices"]:
        assert "index_id" in item
        assert "quality_status" in item
