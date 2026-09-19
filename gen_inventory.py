#!/usr/bin/env python3
"""Generate the 54link platform inventory as plain text for pasting into AppFlowy."""
import json

BASE = '/Users/oluwajobamalomo/54link'
platforms = json.load(open(f'{BASE}/platforms.json'))
repos = json.load(open(f'{BASE}/repos_p1.json')) + json.load(open(f'{BASE}/repos_p2.json'))
by_name = {r['name']: r for r in repos}

covered = set()
for p in platforms.values():
    covered.update(p['repos'])
uncovered = [r for r in repos if r['name'] not in covered]

L = []
L.append('54link Platform Inventory')
L.append('')
L.append(f'{len(repos)} repositories · {len(platforms)} platforms · compiled for African markets, Nigeria first')
L.append('')
L.append('Every platform below is part of the 54link compiled portfolio. Source repositories are public on the munisp GitHub account.')
L.append('')
L.append('=' * 60)
L.append('')

for i, (key, p) in enumerate(platforms.items(), 1):
    L.append(f'{i}. {p["title"]}')
    L.append('')
    L.append(f'Architecture: {p["arch"]}')
    L.append('')
    L.append(f'Overview: {p["overview"]}')
    L.append('')
    L.append('Key features:')
    for f in p['features']:
        L.append(f'  - {f}')
    L.append('')
    L.append(f'Problem it solves: {p["problem"]}')
    L.append('')
    L.append(f'Repositories ({len(p["repos"])}): {", ".join(p["repos"])}')
    L.append('')
    L.append('-' * 60)
    L.append('')

if uncovered:
    L.append(f'Additional repositories ({len(uncovered)})')
    L.append('')
    for r in sorted(uncovered, key=lambda x: x['name'].lower()):
        desc = r.get('description') or 'Active repository in the 54link compiled portfolio.'
        L.append(f'  - {r["name"]} [{r.get("language") or "—"}] — {desc}')
    L.append('')

L.append('=' * 60)
L.append('')
L.append('Maintained at https://54link.54link.here.now/')
L.append('Source: https://github.com/berylm1/54link')

text = '\n'.join(L)
open('/tmp/54link_inventory.txt', 'w').write(text)
print(f'generated {len(text)} chars, {len(L)} lines')
print(f'platforms: {len(platforms)} | repos: {len(repos)} | uncovered: {len(uncovered)}')
print('--- first 12 lines ---')
print('\n'.join(L[:12]))