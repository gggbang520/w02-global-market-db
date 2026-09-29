from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    ROOT / "reports/dashboard/global_market_overview.json": ROOT / "frontend/public/data/global_market_overview.json",
}


def main():
    for source, target in SOURCES.items():
        if not source.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


if __name__ == "__main__":
    main()
