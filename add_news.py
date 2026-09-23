#!/usr/bin/env python3
"""Append verified items to the 54link Africa news feed.

Usage:
    python3 add_news.py /path/to/new_items.json

The file must hold a JSON list of objects with:
    date    ISO date, e.g. "2026-09-23"
    title   headline
    body    1-4 sentences of what actually happened
    source  who reported it, e.g. "Reuters"
    url     link to the reporting (REQUIRED — a claim with no source link is refused)

Optional: display (human dateline, defaults to the ISO date).

Guards against junk and duplicates: every item must carry a real http(s) url, and items
whose normalised title already exists in the feed are skipped. The feed is kept newest
first and capped. Nothing is written unless at least one item is genuinely new.
"""
import json
import os
import re
import sys
import time

BASE = os.path.expanduser('~/54link')
NEWS = f'{BASE}/news.json'
MAX_ITEMS = 80


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s).lower()).strip()


if len(sys.argv) < 2:
    sys.exit('usage: add_news.py <path to new items json>')

try:
    incoming = json.load(open(sys.argv[1]))
except Exception as e:
    sys.exit(f'could not read {sys.argv[1]}: {e}')
if isinstance(incoming, dict):
    incoming = [incoming]
if not isinstance(incoming, list) or not incoming:
    sys.exit('expected a non-empty JSON list of news items')

try:
    feed = json.load(open(NEWS))
except Exception:
    feed = []

seen = {norm(i.get('title')) for i in feed}
added, rejected = [], []
for it in incoming:
    missing = [f for f in ('date', 'title', 'body', 'source') if not str(it.get(f, '')).strip()]
    if missing:
        rejected.append((it.get('title', '?'), f'missing {", ".join(missing)}'))
        continue
    url = str(it.get('url', '')).strip()
    if not url.startswith(('http://', 'https://')):
        rejected.append((it.get('title', '?'), 'no source url'))
        continue
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(it['date'])):
        rejected.append((it.get('title', '?'), f'date {it["date"]!r} is not YYYY-MM-DD'))
        continue
    key = norm(it['title'])
    if key in seen:
        rejected.append((it.get('title', '?'), 'already in the feed'))
        continue
    seen.add(key)
    it.setdefault('display', it['date'])
    it['added'] = time.strftime('%Y-%m-%d')
    added.append(it)
    feed.append(it)

for title, why in rejected:
    print(f'  skipped: {str(title)[:64]}  ({why})')

if not added:
    print('nothing new — feed unchanged')
    sys.exit(0)

feed.sort(key=lambda i: (str(i.get('date', '')), str(i.get('added', ''))), reverse=True)
feed = feed[:MAX_ITEMS]
json.dump(feed, open(NEWS, 'w'), indent=1, ensure_ascii=False)
print(f'added {len(added)} item(s); feed now holds {len(feed)}')
for a in added:
    print(f'  + {a["date"]}  {a["title"][:80]}  [{a["source"]}]')
