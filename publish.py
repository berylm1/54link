#!/usr/bin/env python3
"""Publish the whole site directory (index + platforms/) to here.now."""
import os, json, subprocess, urllib.request, sys

SITE = '/Users/oluwajobamalomo/54link/site'
key = open('/Users/oluwajobamalomo/.herenow/credentials').read().strip()
BASE_VERSION = sys.argv[1] if len(sys.argv) > 1 else '01M1ZPZR7VK13BP9CGVCAXZ8D0'

BASE_VERSION = sys.argv[1] if len(sys.argv) > 1 else None

files = []
for root, dirs, fns in os.walk(SITE):
    # skip intermediates not meant for the site
    if any(part in root for part in ['brochure.html', 'brochure.txt']):
        continue
    for fn in fns:
        if fn in ('brochure.html', 'brochure.txt'):
            continue
        p = os.path.join(root, fn)
        rel = os.path.relpath(p, SITE)
        ct = 'application/pdf' if rel.endswith('.pdf') else ('application/json' if rel.endswith('.json') else None)
        entry = {'path': rel, 'size': os.path.getsize(p)}
        if ct:
            entry['contentType'] = ct
        files.append(entry)
files.sort(key=lambda f: f['path'])
print(len(files), 'files:', [f['path'] for f in files][:6], '...')

payload = {'files': files}
if BASE_VERSION:
    payload['baseVersionId'] = BASE_VERSION
req = urllib.request.Request('https://here.now/api/v1/publish/olive-echo-hra6',
    data=json.dumps(payload).encode(),
    method='PUT',
    headers={'content-type': 'application/json', 'authorization': 'Bearer ' + key, 'X-HereNow-Account': '54link'})
resp = json.load(urllib.request.urlopen(req))
print('create:', resp.get('slug'), resp.get('status'))

for u in resp['upload']['uploads']:
    hdrs = []
    if isinstance(u.get('headers'), dict):
        for k, v in u['headers'].items():
            hdrs += ['-H', f'{k}: {v}']
    local = os.path.join(SITE, u['path'])
    subprocess.run(['curl', '-s', '-X', 'PUT', u['url'], '--data-binary', f'@{local}'] + hdrs, capture_output=True)
    print('uploaded', u['path'])

freq = urllib.request.Request(resp['upload']['finalizeUrl'],
    data=json.dumps({'versionId': resp['upload']['versionId']}).encode(),
    headers={'content-type': 'application/json', 'authorization': 'Bearer ' + key, 'X-HereNow-Account': '54link'})
fin = json.load(urllib.request.urlopen(freq))
print('finalize:', fin.get('state') if (fin := resp) else fin, '|', fin.get('currentVersionId'))
print('site:', resp.get('siteUrl'), '| accountUrl:', resp.get('accountUrl'))