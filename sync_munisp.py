#!/usr/bin/env python3
"""munisp -> 54link sync.

Fetches munisp's public GitHub repositories, refreshes the 54link repo snapshot,
diffs against the stored baseline, rebuilds the site and publishes it to here.now.

Designed to run unattended from cron. Safe by default:
  * if the GitHub fetch fails, nothing is overwritten
  * a lock file prevents overlapping runs
  * the site is only rebuilt/published when something actually changed

Usage:
    python3 sync_munisp.py              # fetch, diff, apply, publish
    python3 sync_munisp.py --dry-run    # fetch + diff only, change nothing
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.expanduser('~/54link')
BASELINE = os.path.expanduser('~/.hermes/cron/munisp-repo-baseline.json')
LOCK = os.path.expanduser('~/.hermes/cron/.54link-sync.lock')
STATE = os.path.expanduser('~/.hermes/cron/54link-sync-state.json')
API = 'https://api.github.com'
USER = 'munisp'
LOG = os.path.expanduser('~/.hermes/cron/54link-sync.log')

DRY = '--dry-run' in sys.argv


def log(msg):
    line = f'{time.strftime("%Y-%m-%d %H:%M:%S")}  {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except OSError:
        pass


def token():
    """Prefer an authenticated gh token (5000 req/h) over anonymous (60 req/h)."""
    try:
        r = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return None


def gh(path):
    headers = {'User-Agent': '54link-sync', 'Accept': 'application/vnd.github+json'}
    tok = token()
    if tok:
        headers['Authorization'] = 'Bearer ' + tok
    req = urllib.request.Request(API + path, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = gh(f'/users/{USER}/repos?per_page=100&page={page}&sort=pushed')
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def slim(r):
    return {
        'full_name': r.get('full_name'),
        'pushed_at': r.get('pushed_at'),
        'description': r.get('description'),
        'stars': r.get('stargazers_count', 0),
        'language': r.get('language'),
    }


def load_baseline():
    try:
        return json.load(open(BASELINE))
    except Exception:
        return {'user': {}, 'repos': {}}


def main():
    # ---- lock -------------------------------------------------------------
    if not DRY:
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        if os.path.exists(LOCK):
            age = time.time() - os.path.getmtime(LOCK)
            if age < 1800:
                log(f'skip: another sync is running (lock age {int(age)}s)')
                return 0
            log(f'stale lock removed (age {int(age)}s)')
        open(LOCK, 'w').write(str(os.getpid()))

    try:
        return run()
    finally:
        if not DRY and os.path.exists(LOCK):
            os.remove(LOCK)


def run():
    # ---- fetch ------------------------------------------------------------
    try:
        user = gh(f'/users/{USER}')
        repos = fetch_repos()
    except Exception as e:
        log(f'ERROR: GitHub fetch failed ({e}) — nothing changed')
        return 2

    if not repos:
        log('ERROR: GitHub returned an empty repo list — refusing to wipe the snapshot')
        return 2

    repos.sort(key=lambda r: r['name'].lower())
    live = {r['full_name']: slim(r) for r in repos}
    base = load_baseline()
    old = base.get('repos', {}) or {}

    # ---- diff -------------------------------------------------------------
    new_repos = sorted(set(live) - set(old))
    gone_repos = sorted(set(old) - set(live))
    pushed = sorted(f for f in live if f in old and live[f]['pushed_at'] != old[f].get('pushed_at'))
    restarred = sorted(f for f in live if f in old and live[f]['stars'] != old[f].get('stars'))
    redesc = sorted(f for f in live if f in old and live[f]['description'] != old[f].get('description'))

    changed = bool(new_repos or gone_repos or pushed or restarred or redesc)
    old_count = base.get('user', {}).get('public_repos')

    log(f'fetched {len(repos)} repos (user reports {user.get("public_repos")}); '
        f'baseline {len(old)}; changed={changed}')
    for f in new_repos:
        log(f'  NEW      {f}  [{live[f]["language"]}]')
    for f in gone_repos:
        log(f'  REMOVED  {f}')
    for f in pushed:
        log(f'  PUSHED   {f}  {live[f]["pushed_at"]}  [{live[f]["language"]}]')
    for f in restarred:
        log(f'  STARS    {f}  {old[f].get("stars")} -> {live[f]["stars"]}')
    for f in redesc:
        log(f'  DESC     {f}')
    if old_count != user.get('public_repos'):
        log(f'  REPOCOUNT {old_count} -> {user.get("public_repos")}')

    if DRY:
        log('dry run — no files written, nothing published')
        return 0

    # ---- write the snapshot ----------------------------------------------
    half = (len(repos) + 1) // 2
    json.dump(repos[:half], open(f'{BASE}/repos_p1.json', 'w'), indent=1)
    json.dump(repos[half:], open(f'{BASE}/repos_p2.json', 'w'), indent=1)

    # ---- coverage: repos with no platform entry ---------------------------
    try:
        platforms = json.load(open(f'{BASE}/platforms.json'))
    except Exception:
        platforms = {}
    covered = {rn for p in platforms.values() for rn in p.get('repos', [])}
    uncovered = sorted(r['name'] for r in repos if r['name'] not in covered)

    # ---- live-environment sweep (check_live.py rewrites live.json) --------
    def read_live():
        try:
            return open(f'{BASE}/live.json').read()
        except OSError:
            return ''

    live_before = read_live()
    try:
        lr = subprocess.run(['python3', 'check_live.py'], cwd=BASE, capture_output=True, text=True, timeout=900)
        for line in lr.stdout.splitlines():
            s = line.strip()
            if s and (line.startswith(' ') or s.split(' ')[0] in ('probing', 'live', 'platforms')):
                log('  live | ' + s)
    except Exception as e:
        log(f'  live sweep failed ({e}) — carrying on with the repo data only')
    live_changed = read_live() != live_before
    if live_changed:
        log('  live environments changed')
    changed = changed or live_changed

    # ---- rebuild + publish only when something changed --------------------
    published = False
    if changed:
        r = subprocess.run(['python3', 'build_site.py'], cwd=BASE, capture_output=True, text=True, timeout=900)
        log('build: ' + (r.stdout.strip().splitlines() or ['(no output)'])[-1])
        if r.returncode != 0:
            log('ERROR: build failed — ' + (r.stderr or '')[-500:])
            return 3
        r = subprocess.run(['python3', 'publish.py'], cwd=BASE, capture_output=True, text=True, timeout=1800)
        tail = [l for l in r.stdout.strip().splitlines() if l.strip()][-3:]
        for l in tail:
            log('publish: ' + l.strip())
        if r.returncode != 0:
            log('ERROR: publish failed — ' + (r.stderr or '')[-500:])
            return 4
        published = True

        # commit only when the repo set itself changed (not for mere pushes)
        if new_repos or gone_repos:
            subprocess.run(['git', 'add', 'repos_p1.json', 'repos_p2.json', 'platforms.json', 'site'],
                           cwd=BASE, capture_output=True, timeout=300)
            subprocess.run(['git', 'commit', '-q', '-m',
                            f'munisp sync: {len(repos)} repos (+{len(new_repos)} new, -{len(gone_repos)} removed)'],
                           cwd=BASE, capture_output=True, timeout=300)
            subprocess.run(['git', 'push', '-q', 'origin', 'HEAD'], cwd=BASE, capture_output=True, timeout=600)
            log('git: committed and pushed')
    else:
        log('no changes — site left as is (nothing republished)')

    # ---- baseline + state -------------------------------------------------
    json.dump({'user': {'public_repos': user.get('public_repos'), 'followers': user.get('followers')},
               'repos': live}, open(BASELINE, 'w'), indent=1)
    # ---- what the site now knows ------------------------------------------
    live_info = {}
    try:
        live_info = json.load(open(f'{BASE}/live.json')).get('platforms', {})
    except Exception:
        pass
    vids = {}
    try:
        vids = json.load(open(f'{BASE}/videos.json'))
    except Exception:
        pass
    live_keys = sorted(k for k, v in live_info.items() if v.get('live'))
    needs_recording = sorted(k for k in live_keys if not vids.get(k))
    attached = {v.get('src') for vs in vids.values() for v in vs}
    try:
        on_disk = sorted(f for f in os.listdir(f'{BASE}/site/videos') if f.endswith('.mp4'))
    except OSError:
        on_disk = []
    unattached = [f for f in on_disk if f'/videos/{f}' not in attached]

    json.dump({
        'last_run': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'repos': len(repos),
        'platforms': len(platforms),
        'repos_without_platform': uncovered,
        'live_platforms': live_keys,
        'live_without_video': needs_recording,
        'video_files_not_attached': unattached,
        'published': published,
        'new_repos': new_repos,
        'removed_repos': gone_repos,
        'pushed': pushed,
    }, open(STATE, 'w'), indent=1)

    log(f'done: {len(repos)} repos / {len(platforms)} platforms / '
        f'{len(live_keys)} live environments / {len(vids)} platforms with video / '
        f'{len(uncovered)} repos without a platform page / published={published}')
    if new_repos:
        log('ACTION NEEDED: new repo(s) ' + ', '.join(new_repos) +
            ' have no platform page — read the repo and author one in platforms.json, then rebuild+publish.')
    if unattached:
        log('ACTION NEEDED: video file(s) in site/videos not attached to any platform — '
            + ', '.join(unattached) + ' — attach them in videos.json, then rebuild+publish.')
    if needs_recording:
        log('NEEDS RECORDING: live platforms with no demo video yet — ' + ', '.join(needs_recording))
    return 0


if __name__ == '__main__':
    sys.exit(main())
