#!/usr/bin/env python3
"""Diff current munisp GitHub state against the stored snapshot the site was built from."""
import json

BASE = '/Users/oluwajobamalomo/54link'
old = json.load(open(f'{BASE}/repos_p1.json')) + json.load(open(f'{BASE}/repos_p2.json'))
new = json.load(open('/tmp/munisp_new_p1.json')) + json.load(open('/tmp/munisp_new_p2.json'))

old_by = {r['name']: r for r in old}
new_by = {r['name']: r for r in new}

added   = sorted(set(new_by) - set(old_by))
removed = sorted(set(old_by) - set(new_by))

changed = []
for name in sorted(set(old_by) & set(new_by)):
    o, n = old_by[name], new_by[name]
    diffs = []
    if o.get('pushed_at') != n.get('pushed_at'):
        diffs.append(f"pushed {str(o.get('pushed_at'))[:10]} -> {str(n.get('pushed_at'))[:10]}")
    if (o.get('description') or '') != (n.get('description') or ''):
        diffs.append("description changed")
    if (o.get('language') or '') != (n.get('language') or ''):
        diffs.append(f"language {o.get('language')} -> {n.get('language')}")
    if o.get('stargazers_count') != n.get('stargazers_count'):
        diffs.append(f"stars {o.get('stargazers_count')} -> {n.get('stargazers_count')}")
    if o.get('archived') != n.get('archived'):
        diffs.append(f"archived {o.get('archived')} -> {n.get('archived')}")
    if diffs:
        changed.append((name, diffs))

print(f"OLD total: {len(old)}   NEW total: {len(new)}")
print(f"\n=== ADDED ({len(added)}) ===")
for a in added:
    r = new_by[a]
    print(f"  + {a}  [{r.get('language')}]  {str(r.get('pushed_at'))[:10]}")
    if r.get('description'):
        print(f"      {r['description'][:100]}")

print(f"\n=== REMOVED ({len(removed)}) ===")
for r in removed:
    print(f"  - {r}")

print(f"\n=== CHANGED ({len(changed)}) ===")
for name, diffs in changed:
    print(f"  ~ {name}: {'; '.join(diffs)}")

# save the new snapshot
json.dump(new, open('/tmp/munisp_current.json', 'w'))
print(f"\ncurrent snapshot saved to /tmp/munisp_current.json")