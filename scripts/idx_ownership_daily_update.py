#!/usr/bin/env python3
"""Daily IDX/KSEI ownership updater for SahamBot.

Runs idx-cli ownership sync, exports the local SQLite snapshot to the website CSV,
and prints a Telegram-friendly status summary.
"""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT = Path('/data/idx-shareholder-visualizer')
EXPORT_SCRIPT = PROJECT / 'scripts' / 'export_ownership_csv.py'
DATA_DIR = PROJECT / 'data'
STATE_PATH = DATA_DIR / 'ownership_monitor_state.json'
NPX = '/usr/local/bin/npx'


def run(cmd: list[str], timeout: int = 600) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def read_releases() -> list[dict[str, str]]:
    path = DATA_DIR / 'ownership_releases.csv'
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def csv_stats() -> dict[str, object]:
    path = DATA_DIR / 'ownership_above1_all.csv'
    if not path.exists():
        return {'rows': 0, 'tickers': 0, 'dates': []}
    rows = 0
    tickers: set[str] = set()
    dates: set[str] = set()
    with path.open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows += 1
            if r.get('share_code'):
                tickers.add(r['share_code'])
            if r.get('date'):
                dates.add(r['date'])
    return {'rows': rows, 'tickers': len(tickers), 'dates': sorted(dates)}


def main() -> int:
    now_utc = datetime.now(timezone.utc)
    now_wib = now_utc.astimezone(timezone(timedelta(hours=7)))
    previous = load_json(STATE_PATH, {})
    prev_hashes = set(previous.get('release_hashes', []))

    sync_code, sync_out = run([NPX, '--yes', 'idx-cli', '-o', 'json', 'ownership', 'sync'])
    sync_json = None
    try:
        sync_json = json.loads(sync_out)
    except Exception:
        sync_json = None

    export_code, export_out = run(['python', str(EXPORT_SCRIPT)])
    releases = read_releases()
    stats = csv_stats()
    hashes = {r.get('sha256', '') for r in releases if r.get('sha256')}
    new_releases = [r for r in releases if r.get('sha256') and r.get('sha256') not in prev_hashes]

    state = {
        'checked_at_utc': now_utc.isoformat(),
        'release_hashes': sorted(hashes),
        'latest_date': max(stats['dates']) if stats['dates'] else None,
        'rows': stats['rows'],
        'tickers': stats['tickers'],
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

    latest = state['latest_date'] or '-'
    sync_action = sync_json.get('action') if isinstance(sync_json, dict) else 'unknown'
    sync_msg = sync_json.get('reason') if isinstance(sync_json, dict) else sync_out[:300]

    if sync_code != 0 or export_code != 0:
        print('⚠️ Update data kepemilikan IDX/KSEI GAGAL sebagian.')
        print(f'Waktu cek: {now_wib:%Y-%m-%d %H:%M} WIB')
        print(f'`idx ownership sync` exit: {sync_code}')
        print(f'Export CSV exit: {export_code}')
        print('Output sync:')
        print(sync_out[-1200:])
        print('Output export:')
        print(export_out[-1200:])
        return 0

    if new_releases:
        print('✅ DATA BARU kepemilikan saham IDX/KSEI terdeteksi dan website sudah diperbarui.')
        print(f'Waktu cek: {now_wib:%Y-%m-%d %H:%M} WIB')
        print('Snapshot baru:')
        for r in new_releases:
            print(f"- {r.get('as_of_date')} — {r.get('row_count')} baris")
    else:
        print('✅ Cek harian data kepemilikan IDX/KSEI selesai. Belum ada snapshot baru dibanding cek terakhir.')
        print(f'Waktu cek: {now_wib:%Y-%m-%d %H:%M} WIB')

    print(f'Latest snapshot di website: {latest}')
    print(f'Total tanggal tersedia: {len(stats["dates"])}')
    print(f'Total baris CSV website: {stats["rows"]:,}'.replace(',', '.'))
    print(f'Total ticker: {stats["tickers"]}')
    print(f'Sync action: {sync_action}')
    if sync_msg:
        print(f'Catatan sync: {sync_msg}')
    print('File website: /data/idx-shareholder-visualizer/data/ownership_above1_all.csv')

    # If the website directory has a GitHub remote, publish data/site changes.
    git_status_code, git_status = run(['git', 'status', '--porcelain'], timeout=60)
    remote_code, remote_url = run(['git', 'remote', 'get-url', 'origin'], timeout=60)
    if git_status_code == 0 and remote_code == 0 and remote_url.strip():
        if git_status.strip():
            run(['git', 'add', 'index.html', 'styles.css', 'app.js', 'README.md', 'data', 'scripts/export_ownership_csv.py'], timeout=60)
            commit_msg = f'Update ownership data {latest}'
            commit_code, commit_out = run(['git', 'commit', '-m', commit_msg], timeout=120)
            import os
            token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
            if token:
                push_url = f'https://x-access-token:{token}@github.com/wahyudanang066-debug/hermes-idx2.git'
                push_code, push_out = run(['git', 'push', push_url, 'main'], timeout=300)
            else:
                push_code, push_out = run(['git', 'push', 'origin', 'main'], timeout=300)
            if push_code == 0:
                print('GitHub publish: berhasil push perubahan ke origin/main.')
            else:
                print('GitHub publish: GAGAL push ke origin/main.')
                print(push_out[-1000:])
        else:
            print('GitHub publish: tidak ada perubahan untuk di-push.')
    else:
        print('GitHub publish: belum aktif karena remote origin belum diset.')

    print('Buka dashboard sementara: https://fresh-rice-remain.loca.lt/?v=auto')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
