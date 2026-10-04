#!/usr/bin/env python3
"""Download/update default IDX/KSEI shareholder CSV mirror.

The official IDX site may block server-side crawling. This helper uses the public
GitHub mirror listed in README. For official use, download CSV/PDF manually from
IDX/KSEI and replace data/kepemilikan_saham_YYYYMMDD.csv.
"""
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://raw.githubusercontent.com/aryakdaniswara/idx-stock-ownership/main/data/kepemilikan_saham_20260227.csv"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "kepemilikan_saham_20260227.csv"

req = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(req, timeout=30) as resp:
    data = resp.read()
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(data)
print(f"updated {OUT} ({len(data):,} bytes)")
