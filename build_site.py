#!/usr/bin/env python3
"""Build the full 54link site: index + per-platform detail pages."""
import json, html, os, shutil

BASE = '/Users/oluwajobamalomo/54link'
platforms = json.load(open(f'{BASE}/platforms.json'))
repos = json.load(open(f'{BASE}/repos_p1.json')) + json.load(open(f'{BASE}/repos_p2.json'))
repo_by_name = {r['name']: r for r in repos}

def esc(s): return html.escape(str(s))
def slugify(key): return key.lower().replace('/', '-').replace(' ', '-').replace('(', '').replace(')', '').replace('.', '')

AFRICA_LOGO = '''<img class="africa" src="/assets/54link-logo.png" alt="54link — Africa" width="512" height="512">'''

STYLE = '''
  :root {
    --bg:#0a0d12; --card:#121a24; --fg:#eef3f8; --muted:#93a0ad; --border:#22303f;
    --gold:#f0b429; --green:#22a34a; --red:#d92d20; --blue:#2f6fed; --orange:#f97316;
    --accent:var(--gold); --accent2:var(--green);
    --stripe:linear-gradient(90deg,#d92d20 0%,#f0b429 24%,#22a34a 49%,#2f6fed 74%,#f97316 100%);
  }
  * { box-sizing:border-box; margin:0; }
  html { scroll-behavior:smooth; }
  body { background:var(--bg); color:var(--fg); font:16px/1.65 -apple-system,'Segoe UI',Roboto,sans-serif; }
  body:before { content:''; position:fixed; inset:0 0 auto 0; height:4px; background:var(--stripe); z-index:100; }
  body:after { content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
    background:radial-gradient(900px 420px at 12% -8%, rgba(240,180,41,.10), transparent 60%),
               radial-gradient(760px 380px at 88% 4%, rgba(47,111,237,.10), transparent 62%),
               radial-gradient(700px 500px at 60% 100%, rgba(34,163,74,.07), transparent 65%); }
  nav, header, section, footer, .detail { position:relative; z-index:1; }
  a { color:var(--accent); }
  nav { position:sticky; top:0; z-index:50; background:rgba(10,13,18,.92); backdrop-filter:blur(8px); border-bottom:1px solid var(--border); }
  nav:after { content:''; position:absolute; left:0; right:0; bottom:-1px; height:2px; background:var(--stripe); opacity:.7; }
  nav .in { max-width:1100px; margin:0 auto; padding:12px 24px; display:flex; gap:22px; align-items:center; flex-wrap:wrap; }
  nav a { color:var(--muted); text-decoration:none; font-size:.92rem; }
  nav a:hover { color:var(--accent); }
  nav .brand { display:flex; align-items:center; gap:10px; font-weight:800; font-size:1.15rem; color:var(--fg); text-decoration:none; }
  nav .brand b { color:var(--accent); }
  .africa { width:30px; height:30px; border-radius:7px; object-fit:cover; }
  .nav-logo { width:34px; height:34px; flex-shrink:0; display:block; border-radius:8px; }
  .hero-logo { width:96px; height:96px; border-radius:16px; box-shadow:0 0 0 1px rgba(240,180,41,.35), 0 12px 34px rgba(0,0,0,.5); }
  header.hero { max-width:1100px; margin:0 auto; padding:56px 24px 40px; }
  .eyebrow { color:var(--gold); text-transform:uppercase; letter-spacing:.14em; font-size:.78rem; font-weight:700; }
  h1 { font-size:2.6rem; line-height:1.12; letter-spacing:-.02em; margin:14px 0 18px; }
  h1 b { background:linear-gradient(94deg,var(--gold),var(--orange)); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .hero p.lead { color:#c9d4e0; max-width:780px; font-size:1.08rem; }
  .stats { display:flex; gap:32px; margin-top:32px; flex-wrap:wrap; }
  .stat { border-left:3px solid var(--gold); padding-left:14px; }
  .stat b { font-size:1.7rem; display:block; }
  .stat span { color:var(--muted); font-size:.85rem; }
  .stat:nth-child(1) b { color:var(--gold); }
  .stat:nth-child(2) { border-left-color:var(--green); } .stat:nth-child(2) b { color:var(--green); }
  .stat:nth-child(3) { border-left-color:var(--red); } .stat:nth-child(3) b { color:var(--red); }
  .stat:nth-child(4) { border-left-color:var(--blue); } .stat:nth-child(4) b { color:var(--blue); }
  .stat:nth-child(5) { border-left-color:var(--orange); } .stat:nth-child(5) b { color:var(--orange); }
  section { max-width:1100px; margin:0 auto; padding:44px 24px; }
  section > h2 { position:relative; font-size:1.7rem; margin-bottom:8px; letter-spacing:-.01em; padding-left:16px; }
  section > h2:before { content:''; position:absolute; left:0; top:.16em; bottom:.16em; width:6px; border-radius:3px; background:var(--stripe); }
  section > p.sectsub { color:var(--muted); margin-bottom:28px; max-width:720px; padding-left:16px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(480px,1fr)); gap:20px; }
  @media (max-width:560px) { .grid { grid-template-columns:1fr; } }
  /* platform search */
  .searchwrap { position:relative; margin:0 0 26px; max-width:560px; }
  .searchwrap input { width:100%; background:#0c1420; border:1px solid var(--border); border-radius:12px; padding:14px 90px 14px 44px; color:var(--fg); font-size:1rem; }
  .searchwrap input:focus { outline:none; border-color:var(--gold); box-shadow:0 0 0 3px rgba(240,180,41,.14); }
  .searchwrap input::placeholder { color:#5c6b7a; }
  .searchwrap .mag { position:absolute; left:15px; top:50%; transform:translateY(-50%); color:var(--muted); pointer-events:none; }
  .searchwrap .count { position:absolute; right:48px; top:50%; transform:translateY(-50%); color:var(--muted); font-size:.82rem; }
  .searchwrap .clear { position:absolute; right:14px; top:50%; transform:translateY(-50%); background:none; border:none; color:var(--muted); cursor:pointer; font-size:1rem; display:none; padding:4px 6px; line-height:1; }
  .searchwrap .clear:hover { color:var(--accent); }
  .nohits { display:none; color:var(--muted); padding:26px 0; font-size:.95rem; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:26px; display:flex; flex-direction:column; transition:border-color .18s, transform .18s; }
  .card:hover { border-color:rgba(240,180,41,.45); transform:translateY(-2px); }
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
  .cardlink a { display:inline-block; background:linear-gradient(94deg,var(--gold),var(--orange)); color:#231704; font-weight:700; text-decoration:none; border-radius:10px; padding:10px 20px; font-size:.9rem; }
  .cardlink a:hover { filter:brightness(1.1); }
  .devbadge { margin-top:14px; font-size:.78rem; color:var(--accent2); border-top:1px dashed var(--border); padding-top:10px; }
  .videos { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:20px; }
  .video-card { background:var(--card); border:1px solid var(--border); border-radius:14px; overflow:hidden; }
  .video-card .ph { aspect-ratio:16/9; background:linear-gradient(135deg,rgba(240,180,41,.10),rgba(47,111,237,.12)),#0f1826; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:.9rem; text-align:center; padding:20px; }
  .video-card .body { padding:16px 18px; }
  .video-card h3 { font-size:1rem; margin-bottom:6px; }
  .video-card p { color:var(--muted); font-size:.88rem; }
  /* collapsible platform list — keeps the homepage compact */
  .plist { display:flex; flex-direction:column; gap:10px; }
  .pcard { background:var(--card); border:1px solid var(--border); border-radius:12px; overflow:hidden; transition:border-color .18s; }
  .pcard:hover { border-color:rgba(240,180,41,.35); }
  .pcard > summary { cursor:pointer; padding:15px 20px; display:flex; align-items:center; gap:14px; list-style:none; }
  .pcard > summary::-webkit-details-marker { display:none; }
  .pcard > summary:hover { background:rgba(240,180,41,.05); }
  .pcard .chev { color:var(--gold); font-size:.78rem; transition:transform .18s; flex-shrink:0; }
  .pcard[open] .chev { transform:rotate(90deg); }
  .pcard .pt { font-weight:700; font-size:1.03rem; flex:1 1 auto; }
  .pcard .pmeta { color:var(--muted); font-size:.79rem; white-space:nowrap; }
  .pcard .live { color:var(--green); font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; border:1px solid rgba(34,163,74,.4); border-radius:999px; padding:1px 8px; white-space:nowrap; }
  .pcard[open] > summary { border-bottom:1px solid var(--border); background:rgba(240,180,41,.05); }
  .pcard .pbody { padding:20px 22px 24px; }
  .pcard .pbody h3 { font-size:.74rem; text-transform:uppercase; letter-spacing:.09em; color:var(--gold); margin:18px 0 7px; }
  .pcard .pbody h3:first-child { margin-top:0; }
  @media (max-width:620px) { .pcard .pmeta { display:none; } }
  /* video previews */
  .videos { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:22px; }
  .vcard { background:var(--card); border:1px solid var(--border); border-radius:14px; overflow:hidden; display:flex; flex-direction:column; transition:border-color .18s, transform .18s; }
  .vcard:hover { border-color:rgba(240,180,41,.45); transform:translateY(-2px); }
  .vcard video { width:100%; aspect-ratio:16/9; display:block; background:#0e1826; object-fit:cover; }
  .vcard .vbody { padding:16px 18px 20px; flex:1; display:flex; flex-direction:column; }
  .vcard h3 { font-size:1.02rem; margin:6px 0 6px; }
  .vcard p { color:var(--muted); font-size:.87rem; }
  .vcard .vlink { margin-top:auto; padding-top:14px; }
  .vcard .vlink a { color:var(--gold); font-weight:600; text-decoration:none; font-size:.9rem; }
  .vcard .vlink a:hover { text-decoration:underline; }
  .vcard .badge { display:inline-block; font-size:.68rem; letter-spacing:.09em; text-transform:uppercase; color:var(--green); border:1px solid rgba(34,163,74,.4); border-radius:999px; padding:2px 9px; }
  /* secured platforms table */
  .secured { width:100%; border-collapse:collapse; font-size:.92rem; }
  .secured th, .secured td { text-align:left; padding:11px 14px; border-bottom:1px solid var(--border); }
  .secured th { color:var(--gold); font-size:.74rem; text-transform:uppercase; letter-spacing:.09em; }
  .secured td a { color:var(--fg); text-decoration:none; font-weight:600; }
  .secured td a:hover { color:var(--gold); }
  .secured .ok { color:var(--green); }
  /* ---------- hamburger menu ---------- */
  nav .in { justify-content:space-between; }
  .burger { display:flex; flex-direction:column; gap:5px; background:none; border:0; cursor:pointer; padding:9px 6px; }
  .burger span { display:block; width:26px; height:2px; background:var(--fg); border-radius:2px; transition:transform .22s ease, opacity .18s ease; }
  nav.open .burger span:nth-child(1) { transform:translateY(7px) rotate(45deg); }
  nav.open .burger span:nth-child(2) { opacity:0; }
  nav.open .burger span:nth-child(3) { transform:translateY(-7px) rotate(-45deg); }
  .navmenu { display:none; border-top:1px solid var(--border); background:rgba(8,11,15,.985); backdrop-filter:blur(10px); max-height:78vh; overflow:auto; }
  nav.open .navmenu { display:block; animation:menudrop .22s ease; }
  @keyframes menudrop { from { opacity:0; transform:translateY(-6px); } to { opacity:1; transform:none; } }
  .navmenu .min { max-width:1100px; margin:0 auto; padding:6px 24px 14px; }
  .navmenu a { display:flex; align-items:center; gap:12px; padding:13px 4px; border-bottom:1px solid var(--border); color:var(--fg); text-decoration:none; font-size:.98rem; }
  .navmenu a:last-child { border-bottom:0; }
  .navmenu a:hover { color:var(--gold); padding-left:10px; transition:padding .16s; }
  .navmenu a .dotmark { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
  .navmenu a:nth-child(1) .dotmark { background:var(--red); }
  .navmenu a:nth-child(2) .dotmark { background:var(--orange); }
  .navmenu a:nth-child(3) .dotmark { background:var(--gold); }
  .navmenu a:nth-child(4) .dotmark { background:var(--green); }
  .navmenu a:nth-child(5) .dotmark { background:var(--blue); }
  .navmenu a:nth-child(6) .dotmark { background:var(--gold); }
  .navmenu a:nth-child(7) .dotmark { background:var(--orange); }
  .navmenu a:nth-child(8) .dotmark { background:var(--red); }
  /* ---------- animated logo stage ---------- */
  header.hero.center { text-align:center; padding:40px 24px 34px; }
  .stage { position:relative; width:380px; height:380px; margin:6px auto 26px; }
  @media (max-width:480px) { .stage { width:290px; height:290px; } }
  .stage .ring { position:absolute; border-radius:50%; border:1px dashed rgba(240,180,41,.34); }
  .stage .r1 { inset:38px; animation:spin 52s linear infinite; }
  .stage .r2 { inset:6px; border-color:rgba(47,111,237,.30); animation:spin 78s linear infinite reverse; }
  .stage .r3 { inset:70px; border-color:rgba(34,163,74,.30); animation:spin 36s linear infinite; }
  .stage .halo { position:absolute; inset:16px; border-radius:50%; animation:spin 14s linear infinite;
      background:conic-gradient(from 0deg, transparent 0 76%, rgba(240,180,41,.20) 88%, transparent 100%); }
  .stage .glow { position:absolute; inset:34%; border-radius:50%; background:radial-gradient(circle, rgba(240,180,41,.30), transparent 68%); animation:breathe 5.5s ease-in-out infinite; }
  .stage .orbit { position:absolute; inset:0; animation:spin 26s linear infinite; }
  .stage .orbit.o2 { inset:30px; animation:spin 38s linear infinite reverse; }
  .stage .orbit i { position:absolute; left:50%; top:50%; width:11px; height:11px; margin:-5.5px 0 0 -5.5px; border-radius:50%; display:block; box-shadow:0 0 10px currentColor; }
  .stage .orbit.o1 i:nth-child(1) { background:var(--gold); color:var(--gold); transform:rotate(0deg) translateY(-152px); }
  .stage .orbit.o1 i:nth-child(2) { background:var(--green); color:var(--green); transform:rotate(120deg) translateY(-152px); }
  .stage .orbit.o1 i:nth-child(3) { background:var(--blue); color:var(--blue); transform:rotate(240deg) translateY(-152px); }
  .stage .orbit.o2 i:nth-child(1) { background:var(--red); color:var(--red); transform:rotate(60deg) translateY(-118px); }
  .stage .orbit.o2 i:nth-child(2) { background:var(--orange); color:var(--orange); transform:rotate(210deg) translateY(-118px); }
  .stage .orbit.o2 i:nth-child(3) { background:var(--green); color:var(--green); transform:rotate(300deg) translateY(-118px); }
  .stage img.stage-logo { position:absolute; left:50%; top:50%; width:152px; height:152px; margin:-76px 0 0 -76px;
      border-radius:26px; animation:breathe 5.5s ease-in-out infinite;
      box-shadow:0 0 0 1px rgba(240,180,41,.4), 0 18px 50px rgba(0,0,0,.55); }
  @keyframes spin { to { transform:rotate(360deg); } }
  @keyframes breathe { 0%,100% { transform:scale(1); } 50% { transform:scale(1.045); } }
  @media (prefers-reduced-motion: reduce) { .stage .ring, .stage .halo, .stage .orbit, .stage .glow, .stage img.stage-logo { animation:none; } }
  .chips { display:flex; justify-content:center; flex-wrap:wrap; gap:9px; margin:0 0 6px; }
  .chips span { font-size:.76rem; color:var(--muted); border:1px solid var(--border); border-radius:999px; padding:4px 12px; }
  /* ---------- africa intro / benefits ---------- */
  .bigp { font-size:1.09rem; color:#d5dee8; max-width:860px; }
  .grid3 { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:18px; margin-top:26px; }
  .bcard { background:var(--card); border:1px solid var(--border); border-radius:13px; padding:20px 22px; transition:border-color .18s, transform .18s; }
  .bcard:hover { border-color:rgba(240,180,41,.42); transform:translateY(-2px); }
  .bcard h3 { font-size:1rem; margin-bottom:7px; display:flex; align-items:center; gap:9px; }
  .bcard h3:before { content:''; width:8px; height:8px; border-radius:50%; background:var(--gold); flex-shrink:0; }
  .bcard:nth-child(3n+2) h3:before { background:var(--green); }
  .bcard:nth-child(3n) h3:before { background:var(--blue); }
  .bcard p { color:#c3cedb; font-size:.92rem; }
  .bcard .metric { display:block; margin-top:9px; font-size:.8rem; color:var(--gold); letter-spacing:.02em; }
  .sources { color:#6f7c8a; font-size:.79rem; margin-top:20px; max-width:820px; }
  /* ---------- news ---------- */
  .news { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:18px; }
  .ncard { background:var(--card); border:1px solid var(--border); border-radius:13px; padding:20px 22px; border-left:3px solid var(--gold); }
  .ncard:nth-child(3n+2) { border-left-color:var(--green); }
  .ncard:nth-child(3n) { border-left-color:var(--blue); }
  .ncard .ndate { font-size:.72rem; text-transform:uppercase; letter-spacing:.09em; color:var(--muted); }
  .ncard h3 { font-size:1rem; margin:7px 0 7px; line-height:1.35; }
  .ncard p { color:#c3cedb; font-size:.9rem; }
  .ncard .nsrc { display:block; margin-top:10px; font-size:.75rem; color:#6f7c8a; }
  .video-frame { position:relative; padding-top:56.25%; background:#0e1826; border-radius:14px; overflow:hidden; border:1px solid rgba(240,180,41,.28); }
  .video-frame iframe { position:absolute; inset:0; width:100%; height:100%; border:0; }
  .video-frame .no-video { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:.95rem; text-align:center; padding:24px; }
  .reg { background:var(--card); border:1px solid var(--border); border-radius:16px; padding:32px; max-width:640px; }
  .reg label { display:block; font-size:.85rem; color:var(--muted); margin:14px 0 6px; }
  .reg input { width:100%; background:#0c1420; border:1px solid var(--border); border-radius:10px; padding:12px 14px; color:var(--fg); font-size:1rem; }
  .reg input:focus { outline:none; border-color:var(--gold); }
  .reg button { margin-top:20px; background:linear-gradient(94deg,var(--gold),var(--orange)); color:#231704; font-weight:700; border:none; border-radius:10px; padding:13px 26px; font-size:1rem; cursor:pointer; }
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
  .detail h2 { position:relative; font-size:1.25rem; color:var(--gold); margin:26px 0 10px; letter-spacing:0; padding-left:13px; }
  .detail h2:before { content:''; position:absolute; left:0; top:.2em; bottom:.2em; width:5px; border-radius:3px; background:var(--stripe); }
  .detail p { margin:8px 0; }
  .detail ul { padding-left:22px; margin:8px 0; }
  .detail li { margin:5px 0; }
  ol.steps { counter-reset:step; list-style:none; padding:0; }
  ol.steps li { position:relative; padding:14px 0 14px 56px; border-bottom:1px dashed var(--border); }
  ol.steps li:before { counter-increment:step; content:counter(step); position:absolute; left:0; top:12px; width:36px; height:36px; border-radius:50%; background:#0c1420; border:2px solid var(--gold); color:var(--gold); display:flex; align-items:center; justify-content:center; font-weight:800; }
  ol.steps li:nth-child(2):before { border-color:var(--green); color:var(--green); }
  ol.steps li:nth-child(3):before { border-color:var(--red); color:var(--red); }
  ol.steps li:nth-child(4):before { border-color:var(--blue); color:var(--blue); }
  ol.steps li:nth-child(5):before { border-color:var(--orange); color:var(--orange); }
  ol.steps li:nth-child(6):before { border-color:var(--gold); color:var(--gold); }
  .repos-list { display:flex; flex-direction:column; gap:8px; margin-top:10px; }
  .repos-list a { display:flex; justify-content:space-between; align-items:center; background:#0c1420; border:1px solid var(--border); border-radius:10px; padding:10px 16px; text-decoration:none; color:var(--fg); font-size:.92rem; }
  .repos-list a:hover { border-color:var(--accent); }
  .repos-list .lang { color:var(--muted); font-size:.75rem; }
  .crumbs { font-size:.85rem; color:var(--muted); }
  .crumbs a { color:var(--muted); text-decoration:none; }
  .crumbs a:hover { color:var(--accent); }
  footer { border-top:3px solid transparent; border-image:var(--stripe) 1; margin-top:40px; }
  footer .in { max-width:1100px; margin:0 auto; padding:32px 24px; color:var(--muted); font-size:.85rem; }
'''

NAV = '''<nav id="topnav"><div class="in">
  <a class="brand" href="/index.html">{logo}<span><b>54</b>link</span></a>
  <button class="burger" id="burger" type="button" aria-expanded="false" aria-controls="navmenu" aria-label="Open menu">
    <span></span><span></span><span></span>
  </button>
</div>
<div class="navmenu" id="navmenu"><div class="min">
  <a href="/africa.html"><span class="dotmark"></span>Africa &amp; its economies</a>
  <a href="/news.html"><span class="dotmark"></span>Latest from Africa</a>
  <a href="/platforms.html"><span class="dotmark"></span>Platforms</a>
  <a href="/videos.html"><span class="dotmark"></span>Video Demos</a>
  <a href="/dev.html"><span class="dotmark"></span>Dev Environments</a>
  <a href="/secured.html"><span class="dotmark"></span>Secured Platforms</a>
  <a href="/brochure.pdf" target="_blank" rel="noopener"><span class="dotmark"></span>Brochure (PDF)</a>
  <a href="/contact.html"><span class="dotmark"></span>Get in Touch</a>
</div></div></nav>'''

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
    'Meridian TaxTech': ('/videos/meridian-walkthrough.mp4', 'Walkthrough of the live Meridian compliance portal at meridian.newfire.app — the Nigeria Revenue Service TaxTech compliance plane, signed in as an operator. Shows the Compliance Overview health board and each module: E-Invoicing Console (IRN + crypto stamp status), WHT Dashboard (2024 evaluation + remittance files), ETR Pillar Two Dashboard (step trace, GIR download), VASP/CARF Console (cost basis, ring-fence, gates), Retailer POS Dashboard (receipts, attribution, variance) and the Practitioner Workspace (matters, documents, deadlines).'),
    'NDSEP / NGApp': ('/videos/ndsep-demo.mp4', 'Recorded walkthrough of the live NDSEP platform at ndsep.newfire.app — the National Data Sovereignty Enforcement Platform. Captured in demo mode (no credentials required), touring the government executive dashboard and all 18 core-platform sections: Discovery Engine, Data Catalog, Compliance Engine, SIEM & Audit, Network DPI, Network Intelligence, NOC Dashboard, Threat Intelligence, SOCint CTI Hub, Maritime Intel, Wazuh SIEM, SIGINT Correlation, Estorides Graph, AI NOC Agent, BGP Routes, Arkime PCAP and Platform Intelligence.'),
    'Lanai': ('/videos/lanai-full-walkthrough.mp4', 'Full walkthrough of the deployed Lanai Lifestyle portal at lanai.newfire.app — logged in as an advisor, testing every service in the menu: dashboard, morning briefing, revenue analytics, clients, members, travel requests, the AI proposal engine, client intelligence, Virtuoso recommendations, the confirmation re-brander, suppliers, WhatsApp and unified inboxes, task templates, invoicing, NPS & feedback, member portal, CRM sync, and settings.'),
    'INEC Election Platform': ('/videos/inec-demo.mp4', 'Full walkthrough of the deployed INEC Digital Twin campaign platform at campaign-inec-servers.newfire.app — the live KPI dashboard (₦107.0M fundraising, 50% compliance, 8/13 milestones, 154-day countdown) plus the campaign tools: War Room, Compliance, Campaign Timeline, Stakeholders Hub, Volunteer Portal and Voter Registration.'),
    'TourismPay': ('/videos/tourismpay-demo.mp4', 'Walkthrough of the deployed TourismPay merchant platform at tourismpay-servers.newfire.app — signed in as a demo merchant (Serengeti Safari Experience, KYB approved and live) and touring the merchant services: Operations Dashboard with live KPI cards and open fraud alerts, Revenue Dashboard, QR Codes, Product Catalog, Channel Manager, Staff Management, Cashier Terminal, Booking Inbox, Deal and KPI Leaderboards, Availability Calendar and BIS Compliance. Multi-currency FX ticker covering KES, GHS, ZAR, NGN and GBP.'),
    'UmojaFlowOS': ('/videos/umoja-demo.mp4', 'Walkthrough of the live UmojaFlowOS public site at umoja.newfire.app — cross-border payment control for Africa-linked corridors. Covers who it serves, partner roles, protections, the Nigeria / Kenya / South Africa market corridors and how it works: real records, assigned workspaces, accountable high-impact steps, and nothing activated by default.'),
    'VPP': ('/videos/vpp-demo.mp4', 'Walkthrough of the deployed VPP Platform at vpp.newfire.app — the Virtual Power Plant control plane, signed in as an administrator. Live telemetry on the dashboard (2.53 MW current power, 1.82 GWh metered energy, 49.98 Hz grid frequency, 11147 V / 230 A electrical readings), 34 registered assets, active power trading, billing and alerts, plus the Energy & Insights, Market, Money, Grid Operations, Operations Centre, Community, Tools & Account and Administration sections.'),
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
    'Meridian TaxTech': [
        ('/videos/meridian-walkthrough.mp4', 'Full walkthrough — every compliance module, signed in as an operator'),
        ('/videos/meridian-demo.mp4', 'Overview clip — meridian.newfire.app'),
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
    def repo_chip(rn):
        """Repo chip: name, language and last push — so the hourly sync shows up here."""
        r = repo_by_name.get(rn, {})
        push = (r.get('pushed_at') or '')[:16].replace('T', ' ')
        tail = ' · '.join(x for x in (r.get('language') or '', (push + ' UTC') if push else '') if x)
        return (f'<a href="https://github.com/munisp/{esc(rn)}" target="_blank" rel="noopener">'
                f'<span>{esc(rn)}</span><span class="lang">{esc(tail)}</span></a>')

    repos_list = ''.join(repo_chip(rn) for rn in p['repos'])
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
  <p class="crumbs"><a href="/platforms.html">← Back to all platforms</a></p>
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
  <p style="margin-top:26px"><a href="/contact.html" style="background:linear-gradient(94deg,var(--gold),var(--orange));color:#231704;font-weight:700;text-decoration:none;border-radius:10px;padding:12px 24px;display:inline-block">Get the 54link brochure</a></p>
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
    feats = ''.join(f'<li>{esc(f)}</li>' for f in p['features'])
    has_video = key in VIDEOS or key in VIDEO_SETS
    badge = '<span class="live">Live demo</span>' if has_video else ''
    repos_html = ''.join(
        f'<a class="repo" href="https://github.com/munisp/{esc(rn)}" target="_blank" rel="noopener">{esc(rn)}'
        f'<span class="lang">{esc(repo_by_name.get(rn,{}).get("language") or "")}</span></a>'
        for rn in p['repos'])
    search_blob = esc((p['title'] + ' ' + p['arch'] + ' ' + p['overview'] + ' ' + p['problem'] + ' ' + ' '.join(p['features']) + ' ' + ' '.join(p['repos'])).lower())
    nrepo = len(p['repos'])
    cards.append(f'''<details class="pcard" data-search="{search_blob}">
      <summary>
        <span class="chev" aria-hidden="true">&#9654;</span>
        <span class="pt">{esc(p['title'])}</span>
        {badge}
        <span class="pmeta">{nrepo} repo{'s' if nrepo != 1 else ''}</span>
      </summary>
      <div class="pbody">
        <h3>Architecture</h3><p class="arch">{esc(p['arch'])}</p>
        <h3>Overview</h3><p class="overview">{esc(p['overview'])}</p>
        <h3>Key features</h3><ul>{feats}</ul>
        <h3>Problem it solves</h3><p class="problem">{esc(p['problem'])}</p>
        <h3>Repositories ({nrepo})</h3><div class="repos">{repos_html}</div>
        <div class="cardlink"><a href="/{esc(slug)}">Explore platform &rarr;</a></div>
      </div>
    </details>''')

auto_cards = []
for r in sorted(uncovered, key=lambda x: x['name'].lower()):
    desc = esc(r.get('description') or '')
    auto_cards.append(f'''
    <article class="card small">
      <h2><a href="https://github.com/munisp/{esc(r['name'])}" target="_blank" rel="noopener">{esc(r['name'])}</a></h2>
      <p class="arch"><strong>Language:</strong> {esc(r.get("language") or '—')} · <strong>Last push:</strong> {esc((r.get("pushed_at") or "")[:16].replace("T", " "))} UTC</p>
      {f'<p class="overview">{desc}</p>' if desc else '<p class="overview">Active repository in the 54link compiled portfolio — see the GitHub repo for details.</p>'}
    </article>''')

# ---------- secured platforms (deployed + demonstrated on video) ----------
SECURED = {
    'Healthpoint': ('healthpoint', 'healthpoint-walkthrough.mp4', 'https://healthpoint.newfire.app',
                    'NAS/IDR health dispute-resolution platform — logged in, every section.'),
    'Lanai': ('lanai', 'lanai-full-walkthrough.mp4', 'https://lanai.newfire.app',
              'Luxury travel concierge advisor portal — every service in the menu.'),
    'Meridian TaxTech': ('meridian', 'meridian-walkthrough.mp4', 'https://meridian.newfire.app',
                         'Nigeria Revenue Service TaxTech compliance plane — six modules.'),
    'NDSEP / NGApp': ('ndsep', 'ndsep-demo.mp4', 'https://ndsep.newfire.app',
                      'National Data Sovereignty Enforcement Platform — 18 sections.'),
    'INEC Election Platform': ('inec', 'inec-demo.mp4', 'https://campaign-inec-servers.newfire.app',
                               'INEC Digital Twin campaign platform — live KPI dashboard and campaign tools.'),
    'TourismPay': ('tourismpay', 'tourismpay-demo.mp4', 'https://tourismpay-servers.newfire.app',
                   'Multi-currency tourism payments — merchant services walkthrough.'),
    'UmojaFlowOS': ('umoja', 'umoja-demo.mp4', 'https://umoja.newfire.app',
                    'Cross-border payment control for Africa-linked corridors.'),
    'VPP': ('vpp', 'vpp-demo.mp4', 'https://vpp.newfire.app',
            'Virtual Power Plant control plane — live telemetry and power trading.'),
}

vcards = []
secured_rows = []
for key, (poster, vidfile, live_url, blurb) in SECURED.items():
    if key not in detail_pages:
        continue
    vcards.append(f'''<div class="vcard">
      <video src="/videos/{esc(vidfile)}" poster="/videos/posters/{esc(poster)}.png" preload="none" controls playsinline></video>
      <div class="vbody">
        <span class="badge">Live demo</span>
        <h3>{esc(key)}</h3>
        <p>{esc(blurb)}</p>
        <p class="vlink"><a href="/{esc(detail_pages[key])}">Open the platform page &rarr;</a></p>
      </div>
    </div>''')
    secured_rows.append(f'''<tr>
      <td><a href="/{esc(detail_pages[key])}">{esc(key)}</a></td>
      <td class="ok">Deployed</td>
      <td class="ok">Recorded</td>
      <td><a href="{esc(live_url)}" target="_blank" rel="noopener">{esc(live_url.replace('https://',''))}</a></td>
    </tr>''')

# ---------- Africa intro, country benefits and current news ----------
AFRICA_INTRO = (
    "Africa is not one story — it is 54 of them. One and a half billion people, the world's fastest-growing "
    "workforce, roughly 30% of the world's mineral reserves and 60% of its solar potential. It is a market "
    "estimated at $3 trillion, and its economy grew 4.4% last year even against global turbulence. Trade under "
    "the African Continental Free Trade Area is projected to reach $230 billion this year, while a single "
    "continental payment rail is starting to pull cross-border flows away from correspondent banks in London "
    "and Frankfurt. The opportunity is no longer about extracting from Africa — it is about building in it, "
    "and each country brings a different advantage to that work."
)

BENEFITS = [
    ("Nigeria", "Africa's largest market and its busiest builder",
     "The continent's biggest economy and population, with the deepest concentration of start-up capital on the "
     "continent. Growth is now running on services rather than oil.",
     "GDP +4.43% in Q2 2026 — fastest in five years · non-oil sectors = 96% of output · trade surplus doubled to $9.5bn"),
    ("Kenya", "The mobile-money economy",
     "Kenya proved what digital financial infrastructure can do at national scale, and now leads the continent in "
     "renewable electricity and start-up capital raised.",
     "91% mobile-money penetration · M-Pesa processes 21m+ transactions daily · >90% electricity from renewables"),
    ("South Africa", "Capital depth and financial services",
     "The deepest capital markets and the largest concentration of private wealth in Africa, with a sophisticated "
     "banking and insurance sector.",
     "48,200 millionaires — 38% of Africa's total · Johannesburg is the continent's wealthiest city"),
    ("Egypt", "Manufacturing and the trade gateway",
     "A dense deal pipeline and a deliberate strategy of balancing global partners to become the region's "
     "manufacturing and trade hub.",
     "100 deals in the current pipeline · fintech champions scaling across North Africa"),
    ("Ghana", "Growth driven by digital services",
     "One of West Africa's steady performers, with communications and services now carrying the economy forward.",
     "Economy expanded 6.2% in the first half of 2026"),
    ("Morocco", "Green energy and industrial ambition",
     "Positioned to export renewable electricity to Europe and home to some of Africa's fastest-growing urban wealth.",
     "Submarine green-power cable planned to Europe · Marrakech wealth +82% in a decade"),
    ("Rwanda", "Governance and logistics technology",
     "A reference market for how fast a country can digitise public service delivery and commercial logistics.",
     "Nationwide drone delivery at operational scale · a top African performer on ease of doing business"),
    ("Ethiopia", "Manufacturing and mineral processing",
     "A deliberate push into industrial parks and domestic processing so raw materials are upgraded at home.",
     "New processing capacity coming online in gold and minerals"),
    ("Mauritius", "Financial services and wealth hub",
     "Africa's fast-growing offshore financial centre and a magnet for mobile wealth.",
     "Black River wealth +120% — Africa's fastest-growing millionaire hotspot"),
]

NEWS = [
    ("Sep 2026", "Africa makes its case for a bigger role on the global stage",
     "Leaders from business, government and global institutions convened in New York alongside the 81st UN General "
     "Assembly. The UN Secretary-General called for a permanent African seat on the Security Council and for the "
     "continent's critical minerals to generate local value and jobs rather than being exported raw.",
     "GABI · Unstoppable Africa 2026"),
    ("Sep 2026", "Nigeria's economy grows 4.43% — its fastest in five years",
     "Second-quarter growth was carried by services, telecommunications, finance and agriculture, while the trade "
     "surplus doubled to $9.5bn. Non-oil sectors now account for 96% of total output.",
     "Semafor Africa · National Bureau of Statistics"),
    ("Sep 2026", "Dangote Refinery IPO set to be Africa's largest share sale",
     "Nigeria's SEC approved an offering expected to raise around $1.5–1.8bn, with plans to double the refinery's "
     "capacity to 1.4 million barrels per day — which would make it the largest single-train refinery in the world.",
     "Semafor Africa · Reuters"),
    ("Sep 2026", "AfCFTA trade projected to reach $230bn this year",
     "Intra-African trade under the Continental Free Trade Area keeps scaling, supported by continental payment "
     "rails that shift cross-border settlement away from correspondent banking.",
     "African Union Commission · GABI 2026"),
    ("Sep 2026", "Africa's solar adoption projected to rise 45% this year",
     "As energy independence becomes a strategic priority, several countries moved to expand both refining and "
     "generation capacity — with renewables adoption rising sharply across the continent.",
     "Ember · Semafor Africa"),
    ("H1 2026", "Fintech remains Africa's largest venture sector",
     "African start-ups raised $1.35bn in the first half of 2026. Fintech took $556m (41%) and logistics $472m. "
     "Nigeria, Kenya, South Africa and Egypt have absorbed roughly 80% of all capital raised since 2019.",
     "Africa: The Big Deal · Partech"),
    ("Sep 2026", "AGOA extended through December 2028",
     "Preferential duty-free access to the US market is preserved for eligible sub-Saharan exporters, giving "
     "textiles, apparel and agriculture a firmer footing for the next two years.",
     "US Government"),
    ("Sep 2026", "Kenya: 90%+ renewable electricity, and a new critical-minerals facility",
     "Kenya generates more than 90% of its electricity from renewable sources, and the US backed a critical "
     "minerals processing facility in a country holding untapped copper, graphite, lithium and nickel.",
     "Guterres / GABI 2026 · Reuters"),
    ("21 Sep 2026", "$300m Nigeria Distributed Renewable Energy Fund reaches first close",
     "Co-managed by the Nigeria Sovereign Investment Authority and Africa50, the fund will finance local clean-energy "
     "developers — solar mini-grids, home systems and storage — aligned to Mission 300's goal of connecting 300 "
     "million Africans to electricity by 2030.",
     "NSIA · Africa50 · GABI 2026"),
]

benefit_cards = ''.join(
    f'''<div class="bcard">
      <h3>{esc(name)}</h3>
      <p style="color:var(--muted);font-size:.82rem;margin:0 0 6px;text-transform:uppercase;letter-spacing:.07em">{esc(tag)}</p>
      <p>{esc(body)}</p>
      <span class="metric">{esc(metric)}</span>
    </div>''' for name, tag, body, metric in BENEFITS)

news_cards = ''.join(
    f'''<article class="ncard">
      <span class="ndate">{esc(date)}</span>
      <h3>{esc(title)}</h3>
      <p>{esc(body)}</p>
      <span class="nsrc">{esc(src)}</span>
    </article>''' for date, title, body, src in NEWS)

HERO = f'''<header class="hero center">
  <div class="stage">
    <div class="ring r2"></div>
    <div class="ring r1"></div>
    <div class="ring r3"></div>
    <div class="halo"></div>
    <div class="glow"></div>
    <div class="orbit o1"><i></i><i></i><i></i></div>
    <div class="orbit o2"><i></i><i></i><i></i></div>
    <img class="stage-logo" src="/assets/54link-logo.png" alt="54link — compiled platforms for Africa" width="512" height="512">
  </div>
  <div class="chips">
    <span>Nigeria</span><span>Kenya</span><span>South Africa</span><span>Ghana</span><span>Egypt</span>
    <span>Morocco</span><span>Rwanda</span><span>Ethiopia</span><span>Mauritius</span>
  </div>
  <p class="eyebrow" style="margin-top:24px">Work for work · Across Africa · Nigeria first</p>
  <h1><b>54link</b> compiles, deploys, and showcases Africa's operational platforms.</h1>
  <p class="lead" style="margin:0 auto">54link is a technology company that brings together a compiled portfolio of production-grade platforms — tax, trade, maritime, health, payments, energy, governance — built for African markets. Every platform is deployed in a live dev environment, documented in full, and demonstrated on video. Nigeria is the first use case; the blueprint scales across all 54.</p>
  <div class="stats" style="justify-content:center">
    <div class="stat"><b>{len(repos)}</b><span>repositories compiled</span></div>
    <div class="stat"><b>{len(platforms)}</b><span>platforms documented</span></div>
    <div class="stat"><b>{len(SECURED)}</b><span>deployed &amp; on video</span></div>
    <div class="stat"><b>1 → 54</b><span>Nigeria first, then the continent</span></div>
  </div>
</header>'''

SEC_AFRICA = f'''<section id="africa">
  <h2>Africa — the continent of the next century</h2>
  <p class="sectsub">One continent, 54 markets, and the world's youngest workforce</p>
  <p class="bigp">{esc(AFRICA_INTRO)}</p>
  <div class="grid3">{benefit_cards}</div>
  <p class="sources">Continental figures: UN Secretary-General António Guterres at GABI's <em>Unstoppable Africa 2026</em>, New York, September 2026. Country data: national statistics offices, Semafor Africa, Partech, Africa: The Big Deal, Africa Wealth Report 2026 and the African Development Bank.</p>
</section>'''

SEC_NEWS = f'''<section id="news">
  <h2>Latest from Africa</h2>
  <p class="sectsub">What is actually moving across the continent right now — capital, energy, trade and policy</p>
  <div class="news">{news_cards}</div>
</section>'''

SEC_PLATFORMS = f'''<section id="platforms">
  <h2>The compiled portfolio</h2>
  <p class="sectsub">Every platform in the 54link portfolio. Search by name, sector, technology or capability — then click any platform for its full detail page with the demo video.</p>
  <div class="searchwrap">
    <span class="mag" aria-hidden="true"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg></span>
    <input id="psearch" type="search" placeholder="Search platforms — tax, maritime, health, payments…" autocomplete="off" aria-label="Search platforms">
    <span class="count" id="pcount"></span>
    <button class="clear" id="pclear" type="button" aria-label="Clear search">✕</button>
  </div>
  <div class="plist" id="platformgrid">{''.join(cards)}</div>
  <p class="nohits" id="pnohits">No platforms match that search. Try a sector (tax, maritime, health), a technology (Go, Python, Rust), or a platform name.</p>
  <details class="pcard" style="margin-top:26px">
    <summary>
      <span class="chev" aria-hidden="true">&#9654;</span>
      <span class="pt">More repositories ({len(uncovered)})</span>
      <span class="pmeta">active repositories without a dedicated platform page</span>
    </summary>
    <div class="pbody"><div class="grid">{''.join(auto_cards)}</div></div>
  </details>
</section>'''

SEC_DEV = f'''<section id="dev">
  <h2>Dev environments</h2>
  <p class="sectsub">Each flagship platform runs in a dedicated development environment on our infrastructure (Kubernetes + hybrid GitOps), wired to real government-agency sandboxes where available — so partners can exercise real workflows, not slideware. Each platform's detail page shows its roadmap status.</p>
</section>'''

SEC_VIDEOS = f'''<section id="videos">
  <h2>Video demos</h2>
  <p class="sectsub">Every walkthrough below was recorded from a live, deployed environment. Press play to preview it here, or open the platform page for the full write-up.</p>
  <div class="videos">{''.join(vcards)}</div>
</section>'''

SEC_SECURED = f'''<section id="secured">
  <h2>Secured platforms</h2>
  <p class="sectsub">The platforms we have taken end to end — deployed in a live environment, verified working, and captured on video. These are the reference deployments we can demonstrate today.</p>
  <table class="secured">
    <thead><tr><th>Platform</th><th>Deployed</th><th>Video</th><th>Live environment</th></tr></thead>
    <tbody>{''.join(secured_rows)}</tbody>
  </table>
</section>'''

SEC_REGISTER = f'''<section id="register">
  <h2>Get in touch</h2>
  <p class="sectsub">Register to get the full brochure — platform plans, deployment roadmap and partnership models — or reach us to talk through a specific deployment.</p>
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

'''


# ---------------------------------------------------------------- page shell
EXTRA_CSS = '''
  .on { color:var(--gold) !important; }
  .hubgrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:18px; margin-top:30px; }
  .hubcard { display:block; background:var(--card); border:1px solid var(--border); border-radius:14px;
             padding:22px 24px; text-decoration:none; color:var(--fg); transition:border-color .18s, transform .18s; }
  .hubcard:hover { border-color:rgba(240,180,41,.45); transform:translateY(-3px); }
  .hubcard h3 { font-size:1.06rem; margin-bottom:7px; display:flex; align-items:center; gap:10px; color:var(--fg); }
  .hubcard h3:before { content:''; width:9px; height:9px; border-radius:50%; background:var(--gold); flex-shrink:0; }
  .hubcard:nth-child(2) h3:before { background:var(--orange); }
  .hubcard:nth-child(3) h3:before { background:var(--green); }
  .hubcard:nth-child(4) h3:before { background:var(--blue); }
  .hubcard:nth-child(5) h3:before { background:var(--red); }
  .hubcard:nth-child(6) h3:before { background:var(--gold); }
  .hubcard p { color:var(--muted); font-size:.9rem; }
  .hubcard .more { display:inline-block; margin-top:11px; font-size:.82rem; color:var(--gold); }
'''

def nav_html(slug=None):
    # the shared menu, with the current page marked
    if slug and ('href="/' + slug) in NAV:
        return NAV.replace('href="/' + slug, 'href="/' + slug + '" class="on', 1)
    return NAV

def page(title, body, slug=None):
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>' + title + '</title><style>' + STYLE + EXTRA_CSS + '</style></head>\n<body>\n'
        + nav_html(slug) + '\n' + body + '\n' + FOOTER +
        '\n<script src="/assets/site.js" defer></script>\n</body></html>'
    )

HUB = f'''<section id="hub" style="padding-top:8px">
  <h2>Explore 54link</h2>
  <p class="sectsub">Every menu item now has its own page — pick a thread below.</p>
  <div class="hubgrid">
    <a class="hubcard" href="/africa.html">
      <h3>Africa &amp; its economies</h3>
      <p>The continent in numbers, and what each of nine markets actually brings to the table.</p>
      <span class="more">Read the picture &rarr;</span>
    </a>
    <a class="hubcard" href="/news.html">
      <h3>Latest from Africa</h3>
      <p>Dated, sourced intelligence — capital, energy, trade and policy across the continent.</p>
      <span class="more">See what is moving &rarr;</span>
    </a>
    <a class="hubcard" href="/platforms.html">
      <h3>Platforms</h3>
      <p>{len(platforms)} documented platforms. Search by sector, technology or capability.</p>
      <span class="more">Browse the portfolio &rarr;</span>
    </a>
    <a class="hubcard" href="/videos.html">
      <h3>Video Demos</h3>
      <p>Walkthroughs recorded from live, deployed environments — press play and preview.</p>
      <span class="more">Watch the demos &rarr;</span>
    </a>
    <a class="hubcard" href="/secured.html">
      <h3>Secured Platforms</h3>
      <p>The platforms taken end to end: deployed, verified working and captured on video.</p>
      <span class="more">See what is secured &rarr;</span>
    </a>
    <a class="hubcard" href="/dev.html">
      <h3>Dev Environments</h3>
      <p>Where the platforms run, and how partners get access to exercise real workflows.</p>
      <span class="more">How access works &rarr;</span>
    </a>
    <a class="hubcard" href="/contact.html">
      <h3>Get in Touch</h3>
      <p>Register for the full brochure — platform plans, deployment roadmap, partnership models.</p>
      <span class="more">Register &rarr;</span>
    </a>
  </div>
</section>'''

BRIEF = f'''<section id="brief" style="padding-top:6px">
  <h2>Why Africa, why now</h2>
  <p class="sectsub">One continent, 54 markets, the world's youngest workforce</p>
  <p class="bigp">{esc(AFRICA_INTRO[:520])}&hellip;</p>
  <p style="margin-top:14px"><a href="/africa.html">The full picture, country by country &rarr;</a></p>
</section>'''

# ---------------------------------------------------------------- the pages
index = page("54link — Africa's Platform Compiler · Nigeria First", HERO + BRIEF + HUB)

PAGES = {
    'africa.html': ('Africa — the continent of the next century · 54link', SEC_AFRICA, 'africa.html'),
    'news.html': ('Latest from Africa · 54link', SEC_NEWS, 'news.html'),
    'platforms.html': ('The compiled portfolio · 54link', SEC_PLATFORMS, 'platforms.html'),
    'videos.html': ('Video demos · 54link', SEC_VIDEOS, 'videos.html'),
    'secured.html': ('Secured platforms · 54link', SEC_SECURED, 'secured.html'),
    'dev.html': ('Dev environments · 54link', SEC_DEV, 'dev.html'),
    'contact.html': ('Get in touch · 54link', SEC_REGISTER, 'contact.html'),
}

for fn, (title, body, slug) in PAGES.items():
    open(f'{BASE}/site/{fn}', 'w').write(page(title, body, slug))

open(f'{BASE}/site/index.html', 'w').write(index)
print('index + ' + str(len(PAGES)) + ' section pages written | detail pages: ' + str(len(detail_pages)) +
      ' | platform cards: ' + str(len(cards)) + ' | repos without a platform: ' + str(len(auto_cards)))
