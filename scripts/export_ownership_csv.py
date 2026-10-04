#!/usr/bin/env python3
"""Export local idx-cli ownership SQLite snapshots to CSV files for the website."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path('/data/profiles/saham-bot/home/.local/share/idx/ownership.db')
DATA = ROOT / 'data'
OUT_ALL = DATA / 'ownership_above1_all.csv'

HEADER = [
    'date','share_code','issuer_name','investor_name','investor_type','local_foreign',
    'nationality','domicile','holdings_scripless','holdings_scrip','total_holding_shares',
    'percentage','source_url','release_sha256'
]

QUERY = """
SELECT
  h.report_date AS date,
  t.code AS share_code,
  COALESCE(t.name, '') AS issuer_name,
  h.raw_investor_name AS investor_name,
  COALESCE(h.investor_type, '') AS investor_type,
  COALESCE(h.locality, '') AS local_foreign,
  COALESCE(h.nationality, '') AS nationality,
  COALESCE(h.domicile, '') AS domicile,
  h.holdings_scripless,
  h.holdings_scrip,
  h.total_shares,
  printf('%.2f', h.percentage_bps / 100.0) AS percentage,
  COALESCE(r.source_url, '') AS source_url,
  h.release_sha256
FROM ksei_holdings h
JOIN tickers t ON t.id = h.ticker_id
LEFT JOIN ownership_releases r ON r.sha256 = h.release_sha256
ORDER BY h.report_date, t.code, h.percentage_bps DESC, h.raw_investor_name
"""


def write_csv(path: Path, records: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(records)


def main() -> None:
    if not DB.exists():
        raise SystemExit(f'ownership DB not found: {DB}')
    con = sqlite3.connect(DB)
    rows = list(con.execute(QUERY))

    # Include the initial 2026-02-27 IDX/KSEI above-1% CSV if it exists from the
    # earlier PDF mirror. Keep the same output schema so the website can load a
    # single time-series file.
    legacy = DATA / 'kepemilikan_saham_20260227.csv'
    if legacy.exists():
        with legacy.open(newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                rows.append((
                    '2026-02-27',
                    r.get('share_code',''),
                    r.get('issuer_name',''),
                    r.get('investor_name',''),
                    r.get('investor_type',''),
                    r.get('local_foreign',''),
                    r.get('nationality',''),
                    r.get('domicile',''),
                    r.get('holdings_scripless','') or 0,
                    r.get('holdings_scrip','') or 0,
                    r.get('total_holding_shares','') or 0,
                    r.get('percentage','') or 0,
                    'https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202603/74cc72f7e5_29d7ff8853.pdf',
                    'legacy-2026-02-27',
                ))

    rows.sort(key=lambda x: (str(x[0]), str(x[1]), -float(x[11] or 0), str(x[3])))
    write_csv(OUT_ALL, rows)

    by_date: dict[str, list[tuple]] = {}
    for row in rows:
        by_date.setdefault(str(row[0]), []).append(row)
    for date, date_rows in by_date.items():
        ymd = date.replace('-', '')
        write_csv(DATA / f'ownership_above1_{ymd}.csv', date_rows)

    releases = list(con.execute('SELECT as_of_date, row_count, source_url, sha256 FROM ownership_releases ORDER BY as_of_date'))
    with (DATA / 'ownership_releases.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['as_of_date','row_count','source_url','sha256'])
        w.writerows(releases)

    print(f'exported {len(rows)} rows to {OUT_ALL}')
    print(f'dates: {", ".join(sorted(by_date))}')
    print(f'releases: {len(releases)}')

if __name__ == '__main__':
    main()
