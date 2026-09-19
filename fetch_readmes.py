import json, urllib.request, concurrent.futures as cf

d = json.load(open('repos_p1.json')) + json.load(open('repos_p2.json'))

def get(name):
    for br in ['master', 'main']:
        try:
            req = urllib.request.Request(
                f"https://raw.githubusercontent.com/munisp/{name}/{br}/README.md",
                headers={'User-Agent': 'fetch'})
            with urllib.request.urlopen(req, timeout=15) as f:
                return name, f.read().decode('utf-8', 'ignore')
        except Exception:
            continue
    return name, None

readmes = {}
with cf.ThreadPoolExecutor(10) as ex:
    for name, text in ex.map(get, [r['name'] for r in d]):
        if text:
            readmes[name] = text

json.dump(readmes, open('readmes.json', 'w'))
print(len(readmes), 'readmes fetched; missing:', [r['name'] for r in d if r['name'] not in readmes])
