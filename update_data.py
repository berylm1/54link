#!/usr/bin/env python3
"""Update the 54link data files from the current munisp snapshot."""
import json, shutil

BASE = '/Users/oluwajobamalomo/54link'

# 1. refresh the repo snapshots the site is built from
shutil.copy('/tmp/munisp_new_p1.json', f'{BASE}/repos_p1.json')
shutil.copy('/tmp/munisp_new_p2.json', f'{BASE}/repos_p2.json')

repos = json.load(open(f'{BASE}/repos_p1.json')) + json.load(open(f'{BASE}/repos_p2.json'))
print(f'repo snapshot refreshed: {len(repos)} repos')

# 2. add the new platform (DeliveryPlatform / SwitchOS) to platforms.json
platforms = json.load(open(f'{BASE}/platforms.json'))

if 'DeliveryPlatform (SwitchOS)' not in platforms:
    # insert after Nexcomm Exchange if present, else at end
    new_entry = {
        "repos": ["DeliveryPlatform"],
        "title": "DeliveryPlatform — SwitchOS Multi-Vertical Delivery Commerce",
        "arch": "TypeScript monorepo (client / server / mobile / services) · Drizzle ORM + PostgreSQL · Vite · pnpm workspaces · Playwright + Vitest",
        "overview": "An operator-centric, multi-vertical delivery commerce and operations platform. SwitchOS spans merchant operations, consumer ordering, courier and dispatch workflows, payments and payouts, loyalty and campaigns, geospatial routing and growth analytics — a broad commerce-and-operations control plane rather than a single-vertical delivery app.",
        "features": [
            "Merchant hub and merchant commerce operations",
            "Consumer ordering and checkout flows",
            "Courier / driver dispatch and courier radar",
            "Payments, payouts, referral and loyalty",
            "Geospatial routing and vertical templates",
            "Trust, experiments, campaigns and growth analytics"
        ],
        "problem": "Delivery commerce in African markets is fragmented across disconnected merchant, courier and payment tools — SwitchOS gives operators one integrated control plane across multiple verticals."
    }
    platforms['DeliveryPlatform (SwitchOS)'] = new_entry
    json.dump(platforms, open(f'{BASE}/platforms.json', 'w'), indent=2)
    print('platforms.json: added DeliveryPlatform (SwitchOS)')
else:
    print('platforms.json: DeliveryPlatform already present')

print(f'platforms now: {len(platforms)}')
print(f'newest repo activity:')
for r in sorted(repos, key=lambda x: x.get('pushed_at') or '', reverse=True)[:6]:
    print(f"  {r['name']:40s} {str(r.get('pushed_at'))[:10]}  [{r.get('language')}]")