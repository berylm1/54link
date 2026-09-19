# 54link — Africa's Platform Compiler

Source for the 54link platform portfolio site: a compiled, documented showcase of the
platforms built for African markets (Nigeria first), published at
**https://54link.54link.here.now/**

## What this repository contains

| Path | Purpose |
|---|---|
| `build_site.py` | Generates the whole static site — `site/index.html` plus one detail page per platform under `site/platforms/` |
| `publish.py` | Uploads `site/` to here.now (create → upload → finalize) |
| `update_data.py` | Refreshes the repo snapshot and adds any new platforms to `platforms.json` |
| `diff_repos.py` | Diffs the current GitHub state of the `munisp` account against the stored snapshot |
| `fetch_readmes.py` | Pulls README text for every repository |
| `platforms.json` | The curated platform catalogue — title, architecture, overview, features, problem solved, and the repositories that make up each platform |
| `repos_p1.json`, `repos_p2.json` | GitHub API snapshot of the `munisp` account that the site is built from |
| `readmes.json` | Cached README text per repository |
| `site/` | The built output (generated — see below) |

## Rebuilding the site

```bash
python3 update_data.py     # optional: refresh repo data from GitHub
python3 build_site.py      # regenerate site/index.html + site/platforms/*.html
python3 publish.py         # incremental publish to here.now
python3 publish.py --verify   # publish, then HEAD-check every file is live
```

`publish.py` is **incremental**: it sends each file's SHA-256, and here.now skips any
file whose content already matches what is live. A one-page change uploads one file
(~13 s) instead of the whole 596 MB site (~8 min).

## Demo videos

Platform demo videos are **not committed here** — they exceed GitHub's 100 MB per-file
limit. They live in `site/videos/` locally and are served from the published site:

- `healthpoint-walkthrough.mp4` — full logged-in HealthPoint walkthrough
- `healthpoint-demo.mp4` — HealthPoint platform overview
- `lanai-full-walkthrough.mp4` — full Lanai advisor portal walkthrough
- `lanai-demo.mp4` — Lanai landing page tour
- `meridian-demo.mp4` — Meridian TaxTech walkthrough

To reproduce them, record with [OpenScreen](https://github.com/getopenscreen/openscreen):

```bash
openscreen record --window "<window title>" --project demo.openscreen --json
openscreen export demo.openscreen -o demo.mp4 --auto-zoom --quality good
```

## Notes

- `site/` is generated output — edit `build_site.py`, not the HTML.
- Platform content is curated in `platforms.json`; the site build reads it directly.
- The portfolio currently covers 67 repositories across 35 platforms.
