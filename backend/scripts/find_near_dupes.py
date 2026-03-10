"""One-time script to find near-duplicate property names and check source files."""
import sys
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.config import settings

engine = create_engine(str(settings.DATABASE_URL).replace("+asyncpg", ""))


def find_dupes():
    with engine.connect() as conn:
        props = conn.execute(
            text("SELECT DISTINCT property_name FROM extracted_values ORDER BY property_name")
        ).fetchall()
        names = [p[0] for p in props]

        suspects = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ratio = SequenceMatcher(None, names[i], names[j]).ratio()
                if ratio > 0.85 and names[i] != names[j]:
                    suspects.append((names[i], names[j], ratio))

        suspects.sort(key=lambda x: -x[2])
        print(f"=== NEAR-DUPLICATE NAMES (similarity > 85%, {len(suspects)} pairs) ===")
        for a, b, r in suspects[:30]:
            print(f'  {r:.0%} | "{a}" vs "{b}"')


def check_pairs():
    pairs = [
        ("Palm  Trails", "Palm Trails"),
        ("Cordoba Apartments", "Cordova Apartments"),
        ("Soltra at SanTan Village", "Soltra SanTan Village"),
    ]
    with engine.connect() as conn:
        for a, b in pairs:
            print(f'--- "{a}" vs "{b}" ---')
            for name in (a, b):
                files = conn.execute(
                    text("SELECT DISTINCT source_file FROM extracted_values WHERE property_name = :n"),
                    {"n": name},
                ).fetchall()
                print(f'  "{name}": {len(files)} files')
                for f in files:
                    fname = Path(f[0]).name
                    print(f"    {fname}")
            print()


if __name__ == "__main__":
    if "--pairs" in sys.argv:
        check_pairs()
    else:
        find_dupes()
