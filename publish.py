#!/usr/bin/env python3
"""Publish the 54link site to here.now.

Incremental: every file is sent with its SHA-256 hash, so here.now skips any
file whose content already matches what is live. Only changed files upload.

Usage:
    python3 publish.py            # incremental publish
    python3 publish.py --verify   # publish, then HEAD-check every file is live
"""
import os, json, sys, hashlib, subprocess, urllib.request, urllib.error

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site')
SLUG = 'olive-echo-hra6'
ACCOUNT = '54link'
API = 'https://here.now/api/v1/publish'
KEY = open(os.path.expanduser('~/.herenow/credentials')).read().strip()

CONTENT_TYPES = {
    '.pdf': 'application/pdf',
    '.json': 'application/json',
    '.mp4': 'video/mp4',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
}

def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(chunk), b''):
            h.update(block)
    return h.hexdigest()

def collect():
    """Every file in site/, excluding local scratch that is not part of the site."""
    SKIP_NAMES = {'brochure.html', 'brochure.txt'}
    entries = []
    for root, _dirs, fns in os.walk(SITE):
        for fn in fns:
            if fn in SKIP_NAMES or fn.startswith('.'):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, SITE)
            if rel.startswith('.herenow') and not rel.endswith('data.json'):
                continue  # local state, not site content
            ext = os.path.splitext(fn)[1].lower()
            e = {'path': rel, 'size': os.path.getsize(p), 'hash': sha256(p)}
            if ext in CONTENT_TYPES:
                e['contentType'] = CONTENT_TYPES[ext]
            entries.append(e)
    entries.sort(key=lambda e: e['path'])
    return entries

def api(path, payload, method='PUT'):
    req = urllib.request.Request(
        f'{API}/{path}', data=json.dumps(payload).encode(), method=method,
        headers={'content-type': 'application/json',
                 'authorization': 'Bearer ' + KEY,
                 'X-HereNow-Account': ACCOUNT,
                 'X-HereNow-Client': 'hermes/54link-publish.py'})
    return json.load(urllib.request.urlopen(req))

def publish():
    files = collect()
    total = sum(f['size'] for f in files)
    print(f'{len(files)} files declared ({total/1e6:.1f} MB total)')

    try:
        resp = api(SLUG, {'files': files})
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print('site not found under this slug — creating it')
            resp = api('', {'files': files}, method='POST')
        else:
            raise

    up = resp['upload']
    uploads = up['uploads']
    skipped = up.get('skipped', [])
    pending_mb = sum(os.path.getsize(os.path.join(SITE, u['path'])) for u in uploads) / 1e6

    print(f'  server skipped {len(skipped)} unchanged file(s)')
    print(f'  uploading {len(uploads)} file(s) ({pending_mb:.1f} MB)')

    for u in uploads:
        hdrs = []
        for k, v in (u.get('headers') or {}).items():
            hdrs += ['-H', f'{k}: {v}']
        local = os.path.join(SITE, u['path'])
        r = subprocess.run(['curl', '-s', '-X', 'PUT', u['url'], '--data-binary', f'@{local}'] + hdrs,
                           capture_output=True)
        if r.returncode != 0:
            print(f'  !! upload failed: {u["path"]}')
            sys.exit(1)
        print(f'  uploaded {u["path"]}')

    freq = urllib.request.Request(
        up['finalizeUrl'],
        data=json.dumps({'versionId': up['versionId']}).encode(),
        headers={'content-type': 'application/json',
                 'authorization': 'Bearer ' + KEY,
                 'X-HereNow-Account': ACCOUNT})
    fin = json.load(urllib.request.urlopen(freq))

    if fin.get('unchanged'):
        print('finalize: unchanged — live version already identical, no new version created')
    else:
        print(f"finalize: live | version {fin.get('currentVersionId')}")
    print(f"site: {fin.get('siteUrl') or resp.get('siteUrl')}")
    return resp, fin

def verify():
    """Confirm every declared file is actually reachable on the live site.

    Skips reserved .herenow/* manifests: here.now processes those server-side
    and deliberately does not serve them to visitors, so a 404 is correct.
    """
    base = f'https://{ACCOUNT}.{ACCOUNT}.here.now'
    files = [f for f in collect() if not f['path'].startswith('.herenow')]
    bad = []
    for f in files:
        url = f'{base}/{f["path"]}'
        r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                            '--max-time', '30', '-I', url], capture_output=True, text=True)
        code = r.stdout.strip()
        if code != '200':
            bad.append((f['path'], code))
    print(f'\nverify: {len(files) - len(bad)}/{len(files)} files return 200')
    for path, code in bad:
        print(f'  !! {path} -> {code}')
    return not bad

if __name__ == '__main__':
    publish()
    if '--verify' in sys.argv:
        sys.exit(0 if verify() else 1)