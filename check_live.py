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

# the cluster's own ApisixRoute hostnames: authoritative, so a platform can never be
# missed just because its hostname is not derivable from a repository name
routes = load(f'{BASE}/routes.json', {}).get('hosts', {})
key_by_slug = {slug(k): k for k in platforms}
repo_owner = {slug(rn): k for k, p in platforms.items() for rn in p.get('repos', [])}
NS_ALIAS = {'whatsapp-commerce': 'WhatsAppCommerce'}          # namespace -> platform key
ns_platform = {}
for host, nss in routes.items():
    for ns in nss:
        s = slug(ns)
        ns_platform[ns] = NS_ALIAS.get(ns) or key_by_slug.get(s) or repo_owner.get(s)
route_stems = set()
for host in routes:
    stem = host.replace(f'.{DOMAIN}', '')
    route_stems.add(stem)
    pk = next((ns_platform[ns] for ns in routes[host] if ns_platform.get(ns)), None)
    targets.setdefault(stem, (pk, (routes[host] or [''])[0]))

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


prev_by_host = {v.get('host', '').replace(f'.{DOMAIN}', ''): k for k, v in previous.items()}
hits = {}
unmatched = []
fail_codes = {}
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for host, status, live in pool.map(probe, sorted(targets)):
        if live:
            key, repo = targets[host]
            pk = key or prev_by_host.get(host)
            if pk:
                hits[host] = (pk, repo, status)
            else:
                unmatched.append((host, status, repo))
        else:
            fail_codes[host] = status          # remember what the failed probe actually saw

print(f'live hosts found: {len(hits) + len(unmatched)}')
if unmatched:
    print('  ANSWERING BUT NOT MAPPED TO A PLATFORM PAGE:')
    for host, status, repo in sorted(unmatched):
        print(f'     {host}.{DOMAIN}  {status}  (namespace: {repo})')

# ---- fold the results into live.json ---------------------------------------
out = dict(previous)
found = {}
for host, (pk, repo, status) in sorted(hits.items()):
    found[pk] = {'url': f'https://{host}.{DOMAIN}', 'host': f'{host}.{DOMAIN}', 'repo': repo,
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
probed = set(targets)
for pk, info in list(out.items()):
    if pk in found:
        continue
    stem = str(info.get('host', '')).replace(f'.{DOMAIN}', '')
    if stem and stem not in probed:
        continue      # its host was not probed this sweep — leave the recorded state alone
    if pk not in found:
        # The route still exists (it answered before), the app just is not serving right now:
        # keep it marked deployed so a transient 503 does not erase it from the site.
        fails = int(info.get('failures', 0)) + 1
        print(f'  platform {pk!r}: {info.get("url")} did not answer '
              f'(was verified {info.get("verified")}) — deployed but not serving (fail #{fails})')
        out[pk] = dict(info, live=False, deployed=True, failures=fails,
                       status=fail_codes.get(stem, info.get('status')),
                       last_ok=info.get('last_ok') or info.get('verified'))
for pk, info in found.items():
    out[pk] = dict(info, live=True, deployed=True, failures=0)

# ---- render-check the live platforms --------------------------------------
# A 200 can mean a working app OR an app that throws on startup (or a login wall).
# Render each in headless Chrome so "live" never gets mistaken for "demonstrable".
try:
    sys.path.insert(0, BASE)
    from render_check import check as render_verdict
except Exception as e:
    print(f'  render check unavailable ({e}) — skipping')
    render_verdict = None

if render_verdict:
    tallies = {}
    for pk in sorted(found):
        url = out[pk].get('url', '')
        try:
            verdict, evidence = render_verdict(url)
        except Exception as e:
            verdict, evidence = 'unknown', f'render failed: {e}'
        tallies[verdict] = tallies.get(verdict, 0) + 1
        # Only a crash means "not demonstrable". A login wall is normal — several platforms were
        # filmed signed in — and a failed render is a limit of this check, not proof of breakage.
        out[pk] = dict(out[pk], render=verdict, render_evidence=str(evidence)[:220],
                       demonstrable=(verdict != 'crashing'))
        if verdict == 'crashing':
            print(f'  render | {pk}: CRASHING — {str(evidence)[:120]}')
        elif verdict not in ('demonstrable',):
            print(f'  render | {pk}: {verdict} (still counts as demonstrable) — {str(evidence)[:90]}')
    print('  render-checked ' + str(len(found)) + ' live platform(s): '
          + ', '.join(f'{v} {k}' for k, v in sorted(tallies.items())))

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
