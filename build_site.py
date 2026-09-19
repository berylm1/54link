#!/usr/bin/env python3
"""Build the full 54link site: index + per-platform detail pages."""
import json, html, os, shutil

BASE = '/Users/oluwajobamalomo/54link'
platforms = json.load(open(f'{BASE}/platforms.json'))
repos = json.load(open(f'{BASE}/repos_p1.json')) + json.load(open(f'{BASE}/repos_p2.json'))
repo_by_name = {r['name']: r for r in repos}

def esc(s): return html.escape(str(s))
def slugify(key): return key.lower().replace('/', '-').replace(' ', '-').replace('(', '').replace(')', '').replace('.', '')

AFRICA_LOGO = '''<svg viewBox="0 0 200 200" class="africa" role="img" aria-label="Africa">
  <circle cx="100" cy="100" r="94" fill="none" stroke="#2dd4a7" stroke-width="4"/>
  <g transform="translate(100,100) scale(0.66) translate(-102,-100)">
    <path fill="#2dd4a7" d="M58 42C68 35 80 32 92 32C106 32 120 35 130 41C135 44 137 47 138 51C140 58 141 66 142 74C152 70 162 70 168 74C172 77 172 82 168 86C162 91 154 94 148 97C143 100 140 106 138 113C135 122 133 130 130 138C127 146 123 153 117 159C112 164 106 167 102 164C98 161 96 155 94 149C91 141 88 134 84 128C80 121 76 116 72 113C70 111 69 109 70 107C74 105 80 106 84 105C86 105 87 104 86 102C78 100 68 99 58 98C50 97 44 95 40 91C35 86 33 79 34 72C35 66 38 61 42 55C46 49 52 45 58 42Z"/>
    <path fill="#2dd4a7" d="M146 120C150 116 154 120 152 130C150 140 146 146 144 142C142 136 143 124 146 120Z"/>
  </g>
</svg>'''

STYLE = '''
  :root { --bg:#0a0e14; --card:#111826; --fg:#e8eef5; --muted:#8b98a5; --accent:#2dd4a7; --accent2:#f5b942; --border:#1e2937; }
  * { box-sizing:border-box; margin:0; }
  html { scroll-behavior:smooth; }
  body { background:var(--bg); color:var(--fg); font:16px/1.65 -apple-system,'Segoe UI',Roboto,sans-serif; }
  a { color:var(--accent); }
  nav { position:sticky; top:0; z-index:50; background:rgba(10,14,20,.92); backdrop-filter:blur(8px); border-bottom:1px solid var(--border); }
  nav .in { max-width:1100px; margin:0 auto; padding:12px 24px; display:flex; gap:22px; align-items:center; flex-wrap:wrap; }
  nav a { color:var(--muted); text-decoration:none; font-size:.92rem; }
  nav a:hover { color:var(--accent); }
  nav .brand { display:flex; align-items:center; gap:10px; font-weight:800; font-size:1.15rem; color:var(--fg); text-decoration:none; }
  nav .brand b { color:var(--accent); }
  .africa { width:30px; height:30px; }
  .nav-logo { width:26px; height:26px; flex-shrink:0; display:block; }
  .hero-logo { width:64px; height:64px; }
  header.hero { max-width:1100px; margin:0 auto; padding:56px 24px 40px; }
  .eyebrow { color:var(--accent2); text-transform:uppercase; letter-spacing:.14em; font-size:.78rem; font-weight:700; }
  h1 { font-size:2.6rem; line-height:1.12; letter-spacing:-.02em; margin:14px 0 18px; }
  h1 b { color:var(--accent); }
  .hero p.lead { color:#c3cedb; max-width:780px; font-size:1.08rem; }
  .stats { display:flex; gap:32px; margin-top:32px; flex-wrap:wrap; }
  .stat { border-left:3px solid var(--accent); padding-left:14px; }
  .stat b { font-size:1.7rem; display:block; }
  .stat span { color:var(--muted); font-size:.85rem; }
  section { max-width:1100px; margin:0 auto; padding:44px 24px; }
  section > h2 { font-size:1.7rem; margin-bottom:8px; letter-spacing:-.01em; }
  section > p.sectsub { color:var(--muted); margin-bottom:28px; max-width:720px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(480px,1fr)); gap:20px; }
  @media (max-width:560px) { .grid { grid-template-columns:1fr; } }
  /* platform search */
  .searchwrap { position:relative; margin:0 0 26px; max-width:560px; }
  .searchwrap input { width:100%; background:#0c1420; border:1px solid var(--border); border-radius:12px; padding:14px 90px 14px 44px; color:var(--fg); font-size:1rem; }
  .searchwrap input:focus { outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(45,212,167,.12); }
  .searchwrap input::placeholder { color:#5c6b7a; }
  .searchwrap .mag { position:absolute; left:15px; top:50%; transform:translateY(-50%); color:var(--muted); pointer-events:none; }
  .searchwrap .count { position:absolute; right:48px; top:50%; transform:translateY(-50%); color:var(--muted); font-size:.82rem; }
  .searchwrap .clear { position:absolute; right:14px; top:50%; transform:translateY(-50%); background:none; border:none; color:var(--muted); cursor:pointer; font-size:1rem; display:none; padding:4px 6px; line-height:1; }
  .searchwrap .clear:hover { color:var(--accent); }
  .nohits { display:none; color:var(--muted); padding:26px 0; font-size:.95rem; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:26px; display:flex; flex-direction:column; }
  .card.small { padding:20px; }
  .card h2 { font-size:1.22rem; margin-bottom:10px; letter-spacing:-.01em; }
  .card h2 a { color:var(--fg); text-decoration:none; }
  .card h2 a:hover { color:var(--accent); }
  .card h3 { font-size:.75rem; text-transform:uppercase; letter-spacing:.09em; color:var(--accent); margin:18px 0 8px; }
  .arch { color:var(--muted); font-size:.9rem; }
  .overview { margin-top:10px; }
  .problem { color:#c8d3dd; }
  .card ul { padding-left:20px; color:#c8d3dd; }
  .card li { margin:3px 0; }
  .repos { margin-top:14px; display:flex; flex-wrap:wrap; gap:8px; }
  .repos h3 { width:100%; margin:0 0 2px; }
  .repo { display:inline-flex; gap:6px; align-items:center; background:#0c1420; border:1px solid var(--border); border-radius:999px; padding:4px 12px; font-size:.8rem; color:var(--fg); text-decoration:none; }
  .repo:hover { border-color:var(--accent); }
  .repo .lang { color:var(--muted); font-size:.7rem; }
  .cardlink { margin-top:auto; padding-top:18px; }
  .cardlink a { display:inline-block; background:var(--accent); color:#06251c; font-weight:700; text-decoration:none; border-radius:10px; padding:10px 20px; font-size:.9rem; }
  .cardlink a:hover { filter:brightness(1.1); }
  .devbadge { margin-top:14px; font-size:.78rem; color:var(--accent2); border-top:1px dashed var(--border); padding-top:10px; }
  .videos { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:20px; }
  .video-card { background:var(--card); border:1px solid var(--border); border-radius:14px; overflow:hidden; }
  .video-card .ph { aspect-ratio:16/9; background:linear-gradient(135deg,#0e1826,#13202f); display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:.9rem; text-align:center; padding:20px; }
  .video-card .body { padding:16px 18px; }
  .video-card h3 { font-size:1rem; margin-bottom:6px; }
  .video-card p { color:var(--muted); font-size:.88rem; }
  .video-frame { position:relative; padding-top:56.25%; background:#0e1826; border-radius:14px; overflow:hidden; border:1px solid var(--border); }
  .video-frame iframe { position:absolute; inset:0; width:100%; height:100%; border:0; }
  .video-frame .no-video { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:.95rem; text-align:center; padding:24px; }
  .reg { background:var(--card); border:1px solid var(--border); border-radius:16px; padding:32px; max-width:640px; }
  .reg label { display:block; font-size:.85rem; color:var(--muted); margin:14px 0 6px; }
  .reg input { width:100%; background:#0c1420; border:1px solid var(--border); border-radius:10px; padding:12px 14px; color:var(--fg); font-size:1rem; }
  .reg input:focus { outline:none; border-color:var(--accent); }
  .reg button { margin-top:20px; background:var(--accent); color:#06251c; font-weight:700; border:none; border-radius:10px; padding:13px 26px; font-size:1rem; cursor:pointer; }
  .reg button:hover { filter:brightness(1.1); }
  .reg .msg { margin-top:14px; font-size:.92rem; min-height:1.4em; }
  .reg .msg.ok { color:var(--accent); }
  .reg .msg.err { color:#f87171; }
  .dl-note { color:var(--muted); font-size:.85rem; margin-top:10px; }
  /* detail page */
  .detail { max-width:900px; margin:0 auto; padding:40px 24px 60px; }
  .detail h1 { font-size:2.2rem; margin:10px 0 16px; }
  .detail .meta { color:var(--muted); font-size:.92rem; margin-bottom:24px; }
  .detail section { padding:20px 0; max-width:none; }
  .detail h2 { font-size:1.25rem; color:var(--accent); margin:26px 0 10px; letter-spacing:0; }
  .detail p { margin:8px 0; }
  .detail ul { padding-left:22px; margin:8px 0; }
  .detail li { margin:5px 0; }
  ol.steps { counter-reset:step; list-style:none; padding:0; }
  ol.steps li { position:relative; padding:14px 0 14px 56px; border-bottom:1px dashed var(--border); }
  ol.steps li:before { counter-increment:step; content:counter(step); position:absolute; left:0; top:12px; width:36px; height:36px; border-radius:50%; background:#0c1420; border:2px solid var(--accent); color:var(--accent); display:flex; align-items:center; justify-content:center; font-weight:800; }
  .repos-list { display:flex; flex-direction:column; gap:8px; margin-top:10px; }
  .repos-list a { display:flex; justify-content:space-between; align-items:center; background:#0c1420; border:1px solid var(--border); border-radius:10px; padding:10px 16px; text-decoration:none; color:var(--fg); font-size:.92rem; }
  .repos-list a:hover { border-color:var(--accent); }
  .repos-list .lang { color:var(--muted); font-size:.75rem; }
  .crumbs { font-size:.85rem; color:var(--muted); }
  .crumbs a { color:var(--muted); text-decoration:none; }
  .crumbs a:hover { color:var(--accent); }
  footer { border-top:1px solid var(--border); margin-top:40px; }
  footer .in { max-width:1100px; margin:0 auto; padding:32px 24px; color:var(--muted); font-size:.85rem; }
'''

NAV = '''<nav><div class="in">
  <a class="brand" href="/index.html">{logo}<span><b>54</b>link</span></a>
  <a href="/index.html#platforms">Platforms</a>
  <a href="/index.html#dev">Dev Environments</a>
  <a href="/index.html#videos">Video Demos</a>
  <a href="/index.html#register">Get the Brochure</a>
</div></nav>'''

# substitute the logo mark into the nav (previously left as a literal placeholder)
NAV = NAV.replace('{logo}', AFRICA_LOGO.replace('class="africa"', 'class="africa nav-logo"'))

FOOTER = '''<footer><div class="in">
  <strong>54link</strong> · Africa's platform compiler · Nigeria first, then all 54.<br>
  {nr} repositories · {np} platforms · source on <a href="https://github.com/munisp?tab=repositories">GitHub</a>
</div></footer>'''

SCRIPT_REG = open(f'{BASE}/reg_script.txt').read() if os.path.exists(f'{BASE}/reg_script.txt') else ''

covered = set()
for p in platforms.values():
    covered.update(p['repos'])
uncovered = [r for r in repos if r['name'] not in covered]

# per-platform demo videos (recorded via OpenScreen, hosted in /videos/)
VIDEOS = {
    'Meridian TaxTech': ('/videos/meridian-demo.mp4', 'A recorded walkthrough of this platform\'s detail page and the live 54link site.'),
    'NDSEP / NGApp': ('/videos/ndsep-demo.mp4', 'Recorded walkthrough of the live NDSEP platform at ndsep.newfire.app — the National Data Sovereignty Enforcement Platform. Captured in demo mode (no credentials required), touring the government executive dashboard and all 18 core-platform sections: Discovery Engine, Data Catalog, Compliance Engine, SIEM & Audit, Network DPI, Network Intelligence, NOC Dashboard, Threat Intelligence, SOCint CTI Hub, Maritime Intel, Wazuh SIEM, SIGINT Correlation, Estorides Graph, AI NOC Agent, BGP Routes, Arkime PCAP and Platform Intelligence.'),
    'Lanai': ('/videos/lanai-full-walkthrough.mp4', 'Full walkthrough of the deployed Lanai Lifestyle portal at lanai.newfire.app — logged in as an advisor, testing every service in the menu: dashboard, morning briefing, revenue analytics, clients, members, travel requests, the AI proposal engine, client intelligence, Virtuoso recommendations, the confirmation re-brander, suppliers, WhatsApp and unified inboxes, task templates, invoicing, NPS & feedback, member portal, CRM sync, and settings.'),
}

# multiple videos per platform: featured video + archive
VIDEO_SETS = {
    'Healthpoint': [
        ('/videos/healthpoint-walkthrough.mp4', 'Full walkthrough — logged in, every section of the platform'),
        ('/videos/healthpoint-demo.mp4', 'Platform overview — healthpoint.newfire.app'),
    ],
    'Lanai': [
        ('/videos/lanai-full-walkthrough.mp4', 'Full walkthrough — every service in the menu'),
        ('/videos/lanai-demo.mp4', 'Landing page tour — lanai.newfire.app'),
    ],
}

def video_frame(src):
    return f'<div class="video-frame"><video controls preload="metadata" style="position:absolute;inset:0;width:100%;height:100%;">\n    <source src="{esc(src)}" type="video/mp4">\n    Your browser does not support embedded video.\n  </video></div>'

def video_block(key):
    # multiple videos: render each with its own label
    if key in VIDEO_SETS:
        parts = []
        for src, label in VIDEO_SETS[key]:
            parts.append(f'<h3 style="margin-top:22px">{esc(label)}</h3>\n  {video_frame(src)}')
        return '\n  '.join(parts)
    if key in VIDEOS:
        src, blurb = VIDEOS[key]
        return f'<p style="color:var(--muted)">{esc(blurb)}</p>\n  {video_frame(src)}'
    return '<p style="color:var(--muted)">A recorded walkthrough of this platform\'s dev environment will appear here — so you can see the application in action before engaging. Recorded and embedded once the deployment ships.</p>\n  <div class="video-frame"><div class="no-video">Demo video coming — recorded from the live dev environment once this platform\'s deployment completes.</div></div>'

os.makedirs(f'{BASE}/site/platforms', exist_ok=True)

# ---------- detail pages ----------
detail_pages = {}
for key, p in platforms.items():
    slug = slugify(key) if False else key.lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '').replace('--', '-')
    slug = slug.replace(' ', '-')
    repos_list = ''.join(
        f'<a href="https://github.com/munisp/{esc(rn)}" target="_blank" rel="noopener"><span>{esc(rn)}</span><span class="lang">{esc(repo_by_name.get(rn,{}).get("language") or "")}</span></a>'
        for rn in p['repos'])
    steps = f'''
    <h2>Roadmap — the steps we're taking</h2>
    <ol class="steps">
      <li><strong>Dev environment deployment.</strong> This platform is staged on 54link infrastructure (Kubernetes, hybrid GitOps) and wired to the relevant government-agency sandboxes where available.</li>
      <li><strong>Demo video walkthrough.</strong> A recorded end-to-end walkthrough of the deployed environment, published on this page (Openscreen pipeline — see the site plan).</li>
      <li><strong>Partner review.</strong> Nigerian agency and enterprise partners exercise real workflows in the dev environment with our team.</li>
      <li><strong>Staging → production.</strong> Hardened deployment for the first Nigerian use case, with data-sovereignty and compliance controls in place.</li>
      <li><strong>Continental rollout.</strong> The blueprint is replicated to additional African markets, localized per country.</li>
    </ol>'''
    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(p['title'])} · 54link</title><style>{STYLE}</style></head>
<body>
{NAV}
<div class="detail">
  <p class="crumbs"><a href="/index.html">← Back to all platforms</a></p>
  <h1>{AFRICA_LOGO.replace('class="africa"','class="africa hero-logo"')}{esc(p['title'])}</h1>
  <p class="meta">{len(p['repos'])} repositories · part of the 54link compiled portfolio · Nigeria first use case</p>
  <h2>What it is</h2>
  <p>{esc(p['overview'])}</p>
  <h2>The problem we're solving</h2>
  <p>{esc(p['problem'])}</p>
  <h2>Architecture</h2>
  <p>{esc(p['arch'])}</p>
  <h2>Key capabilities</h2>
  <ul>{''.join(f'<li>{esc(f)}</li>' for f in p['features'])}</ul>
  {steps}
  <h2>Demo video</h2>
  {video_block(key)}
  <h2>Source repositories ({len(p['repos'])})</h2>
  <div class="repos-list">{repos_list}</div>
  <p style="margin-top:26px"><a href="/index.html#register" style="background:var(--accent);color:#06251c;font-weight:700;text-decoration:none;border-radius:10px;padding:12px 24px;display:inline-block">Get the 54link brochure</a></p>
</div>
{FOOTER.format(nr=len(repos), np=len(platforms))}
</body></html>'''
    os.makedirs(f'{BASE}/site/platforms', exist_ok=True)
    open(f'{BASE}/site/platforms/{slug}.html', 'w').write(doc)
    detail_pages[key] = f'platforms/{slug}.html'

# ---------- index ----------
cards = []
for key, p in platforms.items():
    slug = detail_pages[key]
    feats = ''.join(f'<li>{esc(f)}</li>' for f in p['features'][:4])
    more = f'<li>…and {len(p["features"])-4} more — see the platform page</li>' if len(p['features']) > 4 else ''
    cards.append(f'''
    <article class="card" data-search="{esc((p['title'] + ' ' + p['arch'] + ' ' + p['overview'] + ' ' + p['problem'] + ' ' + ' '.join(p['features']) + ' ' + ' '.join(p['repos'])).lower())}">
      <h2><a href="/{esc(detail_pages[key])}">{esc(p['title'])}</a></h2>
      <p class="arch"><strong>Architecture:</strong> {esc(p['arch'])}</p>
      <p class="overview">{esc(p['overview'])}</p>
      <h3>Key features</h3><ul>{feats}{more}</ul>
      <h3>Problem it solves</h3><p class="problem">{esc(p['problem'])}</p>
      <div class="repos"><h3>Repositories ({len(p['repos'])})</h3>{''.join(f'<a class="repo" href="https://github.com/munisp/{esc(rn)}" target="_blank" rel="noopener">{esc(rn)}<span class="lang">{esc(repo_by_name.get(rn,{}).get("language") or "")}</span></a>' for rn in p['repos'][:6])}</div>
      <div class="cardlink"><a href="/{esc(detail_pages[key])}">Explore platform →</a></div>
    </article>''')

auto_cards = []
for r in sorted(uncovered, key=lambda x: x['name'].lower()):
    desc = esc(r.get('description') or '')
    auto_cards.append(f'''
    <article class="card small">
      <h2><a href="https://github.com/munisp/{esc(r['name'])}" target="_blank" rel="noopener">{esc(r['name'])}</a></h2>
      <p class="arch"><strong>Language:</strong> {esc(r.get("language") or '—')} · <strong>Last push:</strong> {(r.get("pushed_at") or "")[:10]}</p>
      {f'<p class="overview">{desc}</p>' if desc else '<p class="overview">Active repository in the 54link compiled portfolio — see the GitHub repo for details.</p>'}
    </article>''')

index = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>54link — Africa's Platform Compiler · Nigeria First</title><style>{STYLE}</style></head>
<body>
{NAV}
<header class="hero">
  {AFRICA_LOGO.replace('class="africa"','class="africa hero-logo"')}
  <p class="eyebrow" style="margin-top:18px">Work for work · Across Africa · Nigeria first</p>
  <h1><b>54link</b> compiles, deploys, and showcases Africa's operational platforms.</h1>
  <p class="lead">54link is a technology company that brings together a compiled portfolio of production-grade platforms — tax, trade, maritime, health, payments, energy, governance — built for African markets. Every platform is deployed in a live dev environment, documented in full, and demonstrated on video. Nigeria is the first use case; the blueprint scales across all 54.</p>
  <div class="stats">
    <div class="stat"><b>{len(repos)}</b><span>repositories compiled</span></div>
    <div class="stat"><b>{len(platforms)}</b><span>platforms documented</span></div>
    <div class="stat"><b>1 → 54</b><span>Nigeria first, then the continent</span></div>
  </div>
</header>

<section id="platforms">
  <h2>The compiled portfolio</h2>
  <p class="sectsub">Every platform in the 54link portfolio. Search by name, sector, technology or capability — then click any platform for its full detail page with the demo video.</p>
  <div class="searchwrap">
    <span class="mag" aria-hidden="true"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg></span>
    <input id="psearch" type="search" placeholder="Search platforms — tax, maritime, health, payments…" autocomplete="off" aria-label="Search platforms">
    <span class="count" id="pcount"></span>
    <button class="clear" id="pclear" type="button" aria-label="Clear search">✕</button>
  </div>
  <div class="grid" id="platformgrid">{''.join(cards)}</div>
  <p class="nohits" id="pnohits">No platforms match that search. Try a sector (tax, maritime, health), a technology (Go, Python, Rust), or a platform name.</p>
  <h2 style="margin:56px 0 20px;font-size:1.4rem">More repositories ({len(uncovered)})</h2>
  <div class="grid">{''.join(auto_cards)}</div>
</section>

<section id="dev">
  <h2>Dev environments</h2>
  <p class="sectsub">Each flagship platform runs in a dedicated development environment on our infrastructure (Kubernetes + hybrid GitOps), wired to real government-agency sandboxes where available — so partners can exercise real workflows, not slideware. Each platform's detail page shows its roadmap status.</p>
</section>

<section id="videos">
  <h2>Video demos</h2>
  <p class="sectsub">Walkthroughs of the deployed platforms — recorded from the live dev environments. Each video also sits on its platform's detail page.</p>
  <div class="videos">
    <div class="video-card"><div class="ph">HealthPoint — full walkthrough</div><div class="body"><h3>HealthPoint</h3><p>NSA/IDR dispute resolution platform, logged in as Platform Admin.</p><p><a href="/{detail_pages['Healthpoint']}">Open the platform page →</a></p></div></div>
    <div class="video-card"><div class="ph">NDSEP — demo-mode walkthrough</div><div class="body"><h3>NDSEP</h3><p>National Data Sovereignty Enforcement Platform — 18 operational sections.</p><p><a href="/{detail_pages['NDSEP / NGApp']}">Open the platform page →</a></p></div></div>
    <div class="video-card"><div class="ph">Lanai — advisor portal walkthrough</div><div class="body"><h3>Lanai</h3><p>Luxury travel concierge advisor portal, every service in the menu.</p><p><a href="/{detail_pages['Lanai']}">Open the platform page →</a></p></div></div>
    <div class="video-card"><div class="ph">Meridian TaxTech — walkthrough</div><div class="body"><h3>Meridian TaxTech</h3><p>Nigerian NRS unified tax platform.</p><p><a href="/{detail_pages['Meridian TaxTech']}">Open the platform page →</a></p></div></div>
  </div>
</section>

<section id="register">
  <h2>Get the 54link brochure</h2>
  <p class="sectsub">Register to download the full brochure: platform plans, deployment roadmap, and partnership models.</p>
  <div class="reg">
    <form id="regform">
      <label for="r-name">Full name</label>
      <input id="r-name" required autocomplete="name" placeholder="Ada Obi">
      <label for="r-email">Work email</label>
      <input id="r-email" type="email" required autocomplete="email" placeholder="ada@agency.gov.ng">
      <label for="r-org">Organisation</label>
      <input id="r-org" autocomplete="organization" placeholder="Federal Ministry / agency / company">
      <label for="r-interest">Primary interest</label>
      <input id="r-interest" placeholder="e.g. Tax modernisation, maritime, payments">
      <button type="submit">Register &amp; download brochure</button>
      <p class="msg" id="regmsg"></p>
      <p class="dl-note">Registration gives you the current brochure (PDF) and notifications as dev environments and videos go live.</p>
    </form>
  </div>
</section>

{FOOTER}
<script>
/* ---- platform search ---- */
(function () {{
  const input = document.getElementById('psearch');
  const grid = document.getElementById('platformgrid');
  const countEl = document.getElementById('pcount');
  const clearBtn = document.getElementById('pclear');
  const noHits = document.getElementById('pnohits');
  if (!input || !grid) return;
  const cards = Array.from(grid.querySelectorAll('.card'));
  const total = cards.length;
  function apply() {{
    const q = input.value.trim().toLowerCase();
    const terms = q.split(/\s+/).filter(Boolean);
    let shown = 0;
    cards.forEach(function (c) {{
      const hay = (c.getAttribute('data-search') || c.innerText || '').toLowerCase();
      const hit = terms.every(function (t) {{ return hay.indexOf(t) !== -1; }});
      c.style.display = hit ? '' : 'none';
      if (hit) shown++;
    }});
    if (!q) {{
      countEl.textContent = total + ' platforms';
      clearBtn.style.display = 'none';
    }} else {{
      countEl.textContent = shown + ' of ' + total;
      clearBtn.style.display = 'block';
    }}
    noHits.style.display = (q && shown === 0) ? 'block' : 'none';
  }}
  input.addEventListener('input', apply);
  clearBtn.addEventListener('click', function () {{ input.value = ''; input.focus(); apply(); }});
  input.addEventListener('keydown', function (e) {{
    if (e.key === 'Escape') {{ input.value = ''; apply(); }}
    if (e.key === 'Enter') {{
      const first = cards.find(function (c) {{ return c.style.display !== 'none'; }});
      const link = first && first.querySelector('h2 a');
      if (link) link.click();
    }}
  }});
  // focus search with "/" key
  document.addEventListener('keydown', function (e) {{
    if (e.key === '/' && document.activeElement !== input) {{ e.preventDefault(); input.focus(); }}
  }});
  apply();
}})();

const ENDPOINT = './.herenow/data/registrations';
document.getElementById('regform').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const msg = document.getElementById('regmsg');
  const btn = e.target.querySelector('button');
  btn.disabled = true; btn.textContent = 'Registering…';
  const record = {{
    name: document.getElementById('r-name').value.trim(),
    email: document.getElementById('r-email').value.trim(),
    organisation: document.getElementById('r-org').value.trim(),
    interest: document.getElementById('r-interest').value.trim()
  }};
  try {{
    const res = await fetch(ENDPOINT, {{
      method: 'POST',
      headers: {{ 'content-type': 'application/json', 'Idempotency-Key': crypto.randomUUID() }},
      body: JSON.stringify(record)
    }});
    if (!res.ok) throw new Error('status ' + res.status);
    msg.className = 'msg ok';
    msg.textContent = 'Registered — your brochure download is starting.';
    setTimeout(() => window.open('/brochure.pdf', '_blank'), 900);
    e.target.reset();
  }} catch (err) {{
    msg.className = 'msg err';
    msg.textContent = 'Registration failed — please try again or email us directly.';
  }} finally {{
    btn.disabled = false; btn.textContent = 'Register & download brochure';
  }}
}});
</script>
</body></html>'''

open(f'{BASE}/site/index.html', 'w').write(index)
print(f'index written | detail pages: {len(detail_pages)} | cards: {len(cards)} | auto: {len(auto_cards)}')