#!/usr/bin/env python3
"""Finalize the pending version of the 54link site."""
import json, subprocess, urllib.request

key = open('/Users/oluwajobamalomo/.herenow/credentials').read().strip()
out = subprocess.run(['curl', '-s', 'https://here.now/api/v1/publish/olive-echo-hra6',
                      '-H', 'authorization: Bearer ' + key, '-H', 'X-HereNow-Account: 54link'],
                     capture_output=True, text=True).stdout
d = json.loads(out)
print('pendingVersionId:', d.get('pendingVersionId'))
print('currentVersionId:', d.get('currentVersionId'))

# The publish script saved the finalize URL? Re-derive: refresh uploads for pending version.
vid = d.get('pendingVersionId')
if not vid:
    print('Nothing pending — site already live.')
    raise SystemExit(0)

req = urllib.request.Request(
    f'https://here.now/api/v1/publish/olive-echo-hra6/uploads/refresh',
    data=json.dumps({'versionId': vid}).encode(), method='POST',
    headers={'content-type': 'application/json', 'authorization': 'Bearer ' + key, 'X-HereNow-Account': '54link'})
r = json.load(urllib.request.urlopen(req))
print('refresh keys:', list(r.keys()))

freq = urllib.request.Request(r['finalizeUrl'],
    data=json.dumps({'versionId': vid}).encode(),
    headers={'content-type': 'application/json', 'authorization': 'Bearer ' + key, 'X-HereNow-Account': '54link'})
fin = json.load(urllib.request.urlopen(freq))
print('finalize:', json.dumps(fin)[:400])