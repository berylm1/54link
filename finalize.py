import json, subprocess, urllib.request

r = json.load(open('/tmp/pub7.json'))
key = open('/Users/oluwajobamalomo/.herenow/credentials').read().strip()

for u in r['upload']['uploads']:
    hdrs = []
    if isinstance(u.get('headers'), dict):
        for k, v in u['headers'].items():
            hdrs += ['-H', f"{k}: {v}"]
    local = f"/Users/oluwajobamalomo/54link/site/{u['path']}"
    subprocess.run(['curl', '-s', '-X', 'PUT', u['url'], '--data-binary', f'@{local}'] + hdrs, capture_output=True)
    print('uploaded', u['path'])

req = urllib.request.Request(r['upload']['finalizeUrl'], data=json.dumps({'versionId': r['upload']['versionId']}).encode(),
    headers={'content-type': 'application/json', 'authorization': 'Bearer ' + key, 'X-HereNow-Account': '54link'})
print(urllib.request.urlopen(req).read().decode()[:400])
