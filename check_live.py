#!/usr/bin/env python3
"""Probe which 54link platforms have a live environment.

Walks every platform's GitHub repositories, derives the hostnames they could be
deployed under, and HTTP-probes each one. Rewrites live.json with what is actually
answering, and reports platforms that are live but still have no demo video.

Usage:
    python3 check_live.py             # probe, write live.json, report
    python3 check_live.py --dry-run   # probe and report, change nothing
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.expanduser('~/54link')
LIVE = f'{BASE}/live.json'
DOMAIN = 'newfire.app'
DRY = '--dry-run' in sys.argv
TIMEOUT = 8
WORKERS = 16
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE      # we only care whether the host answers


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


repos = load(f'{BASE}/repos_p1.json', []) + load(f'{BASE}/repos_p2.json', [])
platforms = load(f'{BASE}/platforms.json', {})
videos = load(f'{BASE}/videos.json', {})
previous = load(LIVE, {}).get('platforms', {})

repo_names = {r['name'] for r in repos}


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def camel_split(s):
    """whatsappCommerce -> whatsapp-commerce (repo names are camelCase, hosts are not)."""
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '-', s).lower()


def variants(*names):
    """Hostname candidates for a name: plain, hyphenated, camel-split and common suffixes."""
    out = []
    for n in names:
        if not n:
            continue
        base = slug(n)
        for v in dict.fromkeys((base, base.replace('-', ''), slug(camel_split(n)),
                                camel_split(n).replace('-', ''))):
            for suffix in ('', '-servers', '-server', '-app', '-portal', '-dev', '-ui', '-web'):
                cand = v + suffix
                if cand and len(cand) < 60:
                    out.append(cand)
    return out


# ---- build the candidate set ------------------------------------------------
targets = {}          # host -> (platform key or None, repo name)
for key, p in platforms.items():
    cands = []
    for rn in p.get('repos', []):
        cands += variants(rn)
    cands += variants(key, key.replace(' platform', ''))
    if 'inec' in key.lower() or any('inec' in r.lower() for r in p.get('repos', [])):
        cands += ['campaign-inec-servers', 'inec-servers', 'campaign-inec']
    for c in dict.fromkeys(cands):
        targets.setdefault(c, (key, (p.get('repos') or [''])[0]))
# repos with no platform entry still get a look
covered = {rn for p in platforms.values() for rn in p.get('repos', [])}
for rn in sorted(repo_names - covered):
    for c in variants(rn):
        targets.setdefault(c, (None, rn))
# always re-verify hosts we already know about
for key, info in previous.items():
    h = (info.get('host') or '').replace(f'.{DOMAIN}', '')
    if h:
        targets.setdefault(h, (key, info.get('repo', '')))

print(f'probing {len(targets)} candidate host(s) across {len(platforms)} platforms '
      f'and {len(repo_names)} repositories…')


def probe(host):
    url = f'https://{host}.{DOMAIN}/'
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': '54link-live-check'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
            return host, r.status, True
    except urllib.error.HTTPError as e:
        # a gated host (401/403) or a redirect is still a deployed host
        if e.code in (401, 403):
            return host, e.code, True
        if 300 <= e.code < 400:
            return host, e.code, True
        return host, e.code, False
    except Exception:
        return host, None, False


hits = {}
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for host, status, live in pool.map(probe, sorted(targets)):
        if live:
            key, repo = targets[host]
            hits[host] = (key, repo, status)

print(f'live hosts found: {len(hits)}')

# ---- fold the results into live.json ---------------------------------------
out = dict(previous)
by_host = {v.get('host', '').replace(f'.{DOMAIN}', ''): k for k, v in previous.items()}
found = {}
for host, (key, repo, status) in sorted(hits.items()):
    url = f'https://{host}.{DOMAIN}'
    pk = key or by_host.get(host)
    if not pk:
        continue                      # live host for a repo with no platform page yet
    found[pk] = {'url': url, 'host': f'{host}.{DOMAIN}', 'repo': repo,
                 'status': status, 'verified': time.strftime('%Y-%m-%d'),
                 'source': 'probe'}

# if a platform already had a working URL and it is still answering, keep that canonical one
# rather than flipping to an alternate host that happens to answer too
for pk, info in list(found.items()):
    prev = previous.get(pk) or {}
    prev_host = str(prev.get('host', '')).replace(f'.{DOMAIN}', '')
    if prev_host and prev_host in hits:
        found[pk] = dict(info, url=f'https://{prev_host}.{DOMAIN}',
                         host=f'{prev_host}.{DOMAIN}', status=hits[prev_host][2])

for pk, info in found.items():
    if pk in out and out[pk].get('url') != info['url']:
        print(f'  platform {pk!r}: live URL changed {out[pk]["url"]} -> {info["url"]}')
    out[pk] = info
for pk, info in list(out.items()):
    if pk not in found:
        print(f'  platform {pk!r}: {info.get("url")} did not answer '
              f'(was verified {info.get("verified")}) — keeping it, flagged live=false')
        out[pk] = dict(info, live=False)
for pk, info in found.items():
    out[pk] = dict(info, live=True)

newly = [k for k in found if k not in previous or not previous[k].get('live')]
if newly:
    print('  newly live: ' + ', '.join(newly))

live_no_video = sorted(k for k, v in out.items() if v.get('live') and not videos.get(k))
video_no_live = sorted(k for k in videos if k not in out or not out[k].get('live'))

print(f'\nplatforms live: {sum(1 for v in out.values() if v.get("live"))}')
print(f'platforms with video: {len(videos)}')
if live_no_video:
    print(f'live but no demo video yet ({len(live_no_video)}) — needs recording:')
    for k in live_no_video:
        print(f'   {k:<28} {out[k]["url"]}')
if video_no_live:
    print(f'has a video but no verified live host ({len(video_no_live)}): {", ".join(video_no_live)}')

if DRY:
    print('\ndry run — live.json not written')
    sys.exit(0)

json.dump({'_note': 'Live environments per platform. Rewritten by check_live.py each sweep.',
           'platforms': out}, open(LIVE, 'w'), indent=1)
print(f'\nwrote {LIVE}')
