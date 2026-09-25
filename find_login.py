#!/usr/bin/env python3
"""Find how to get INTO a platform, from the platform's own repositories.

When a live platform renders a login wall, the answer is usually already in the repo:
a demo-mode switch, a seeded account, a documented credential, or a Keycloak realm export.
This scans the repos (via the GitHub API — no clone needed) and reports the entry route.

Secrets are never printed: credentials found in files are reported by location and masked.
The point is to tell you WHICH door exists and WHERE it is documented.

Usage:
    python3 find_login.py "NDSEP / NGApp"       # by platform key
    python3 find_login.py --all-gated           # every gated platform
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.expanduser('~/54link')
API = 'https://api.github.com'

# ---- what we look for ------------------------------------------------------
DEMO_PATTERNS = [
    r'\bVITE_DEMO_MODE\b', r'\bDEMO_MODE\b', r'\bNEXT_PUBLIC_DEMO\b', r'\bREACT_APP_DEMO\b',
    r'\bAUTH_?BYPASS\b', r'\bBYPASS_?AUTH\b', r'\bDISABLE_?AUTH\b', r'\bSKIP_?AUTH\b',
    r'\bMOCK_?AUTH\b', r'\bDEV_?LOGIN\b', r'\bDEV_?AUTH\b', r'\bAUTO_?LOGIN\b',
    r'\bVITE_DEV_MODE\b', r'\bALLOW_?FIXTURE\b', r'demo mode', r'demo login',
]
CRED_PATTERNS = [
    (r'(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\']{4,})["\']', 'password'),
    (r'(?:username|user|login|email)\s*[:=]\s*["\']([^"\'@\s]{3,})["\']', 'username'),
    (r'\b(admin|devadmin|superadmin|demo|test)\s*[:/]\s*["\']?([^\s"\']{6,})', 'user:pass'),
]
SEED_PATTERNS = [
    r'INSERT\s+INTO\s+(?:users|"users"|accounts)\b', r'createUser\s*\(', r'seedUsers?\b',
    r'upsert\s*\(\s*users', r'defaultUsers?\b', r'admin@', r'@example\.com', r'@demo\.',
    r'\busers\s*:\s*\[', r'credentials\s*:\s*\[',
]
KEYCLOAK_PATTERNS = [r'"realm"\s*:', r'realm-export', r'keycloak.*realm', r'"sslRequired"']

INTERESTING_PATH = re.compile(
    r'(readme|\.env|seed|fixture|demo|sample|mock|keycloak|realm|auth|login|test|example|'
    r'docs?/|scripts?/|docker-compose|\.ya?ml$|\.sql$|admin)', re.I)
SKIP_PATH = re.compile(r'(node_modules|\.git/|dist/|build/|vendor/|\.lock|\.png|\.jpe?g|\.svg|'
                       r'\.woff|\.mp4|\.pdf)', re.I)
MAX_FILES = 60
MAX_BYTES = 120_000


def token():
    try:
        r = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return None


TOK = token()


def gh(path, raw=False):
    url = path if path.startswith('http') else API + path
    headers = {'User-Agent': '54link-login-scan', 'Accept': 'application/vnd.github.raw' if raw
               else 'application/vnd.github+json'}
    if TOK:
        headers['Authorization'] = 'Bearer ' + TOK
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if raw else json.load(r)


def repo_files(repo):
    """Paths worth reading in a repo (docs, env examples, seeds, keycloak, scripts)."""
    try:
        tree = gh(f'/repos/munisp/{repo}/git/trees/HEAD?recursive=1')
    except Exception as e:
        return repo, [], str(e)
    out = []
    for node in tree.get('tree', []):
        p = node.get('path', '')
        if node.get('type') != 'blob' or SKIP_PATH.search(p) or node.get('size', 0) > MAX_BYTES:
            continue
        if INTERESTING_PATH.search(p):
            out.append(p)
    return repo, out[:MAX_FILES], None


def scan_file(repo, path):
    try:
        text = gh(f'/repos/munisp/{repo}/contents/{path}', raw=True).decode('utf-8', 'ignore')
    except Exception:
        return None
    findings = {'repo': repo, 'path': path, 'demo': [], 'creds': [], 'seed': [], 'keycloak': []}
    for pat in DEMO_PATTERNS:
        if re.search(pat, text, re.I):
            findings['demo'].append(pat.strip('\\b'))
    for pat, kind in CRED_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            raw = m.group(m.lastindex or 0)
            masked = raw[:2] + '*' * max(0, len(raw) - 2)      # never print the secret
            findings['creds'].append(f'{kind} "{masked}"')
    for pat in SEED_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            frag = m.group(0)[:60]
            if '@' in frag or 'user' in frag.lower():
                findings['seed'].append(frag.strip())
    for pat in KEYCLOAK_PATTERNS:
        if re.search(pat, text, re.I):
            findings['keycloak'].append(pat)
    return findings if any(findings[k] for k in ('demo', 'creds', 'seed', 'keycloak')) else None


def scan_platform(key, platforms, max_repos=6):
    repos = (platforms.get(key) or {}).get('repos', [])[:max_repos]
    results = []
    for repo in repos:
        _repo, paths, err = repo_files(repo)
        if err or not paths:
            continue
        with ThreadPoolExecutor(max_workers=8) as pool:
            for f in pool.map(lambda p: scan_file(repo, p), paths):
                if f:
                    results.append(f)
    return results


def verdict(key, findings):
    demo = [f for f in findings if f['demo']]
    creds = [f for f in findings if f['creds']]
    seeds = [f for f in findings if f['seed']]
    realm = [f for f in findings if f['keycloak']]
    if demo:
        return 'DEMO-MODE', f"a demo/auth switch exists in {demo[0]['repo']}:{demo[0]['path']} ({', '.join(sorted(set(demo[0]['demo']))[:4])})"
    if creds:
        return 'DOCUMENTED-CREDENTIAL', f"documented credential in {creds[0]['repo']}:{creds[0]['path']} ({', '.join(sorted(set(creds[0]['creds']))[:3])}) — save it to the vault to use it"
    if seeds:
        return 'SEEDED-ACCOUNT', f"seeded account in {seeds[0]['repo']}:{seeds[0]['path']} ({', '.join(sorted(set(seeds[0]['seed']))[:3])})"
    if realm:
        return 'KEYCLOAK-REALM', f"realm export in {realm[0]['repo']}:{realm[0]['path']} — the realm defines the passable accounts"
    return 'NO-DOCUMENTED-ENTRY', 'no demo switch, seeded account or documented credential found in the scanned files'


if __name__ == '__main__':
    platforms = json.load(open(f'{BASE}/platforms.json'))
    keys = sys.argv[1:]
    if not keys or keys[0] == '--all-gated':
        live = json.load(open(f'{BASE}/live.json'))['platforms']
        keys = sorted(k for k, v in live.items()
                      if v.get('live') and v.get('render') in ('gated', None) and k in platforms)
    for k in keys:
        print(f'\n=== {k}')
        fs = scan_platform(k, platforms)
        v, why = verdict(k, fs)
        print(f'    VERDICT: {v}')
        print(f'    {why}')
        ev = {}
        for f in fs:
            for kind in ('demo', 'creds', 'seed', 'keycloak'):
                if f[kind]:
                    ev.setdefault(kind, []).append(f"{f['repo']}:{f['path']}")
        for kind, paths in ev.items():
            print(f'    {kind}: ' + '; '.join(sorted(set(paths))[:5]))
