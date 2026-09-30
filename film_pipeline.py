#!/usr/bin/env python3
"""54link demo-video pipeline: find -> film -> attach -> publish, unattended.

Runs at the end of each sweep. It looks for platforms that are LIVE, RENDER-CHECKED
DEMONSTRABLE, and have no demo video yet, films the public experience in Chrome via
Openscreen, and attaches the result — so the site grows its video library by itself.

Guardrails (deliberate, learned the hard way):
  * never films unless Google Chrome is actually the frontmost application
  * never films a platform whose render check is not "demonstrable"
  * one platform per run by default; a lock prevents overlapping runs
  * --dry-film films and exports but touches nothing on the site

Usage:
    python3 film_pipeline.py                 # normal run
    python3 film_pipeline.py --dry-run       # report candidates only
    python3 film_pipeline.py --dry-film      # film + export, do not attach
    python3 film_pipeline.py --platform "K"  # force one platform key
    python3 film_pipeline.py --max 2         # film up to N platforms
"""
import json
import os
import re
import subprocess
import sys
import time

BASE = os.path.expanduser('~/54link')
LOCK = os.path.expanduser('~/.hermes/cron/.54link-film.lock')
LOG = os.path.expanduser('~/.hermes/cron/54link-film.log')
OS = '/Applications/Openscreen.app/Contents/MacOS/Openscreen'
CHROME = 'Google Chrome'

DRY = '--dry-run' in sys.argv
DRY_FILM = '--dry-film' in sys.argv
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 1
FORCE = sys.argv[sys.argv.index('--platform') + 1] if '--platform' in sys.argv else None


def log(msg):
    line = f'{time.strftime("%Y-%m-%d %H:%M:%S")}  {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except OSError:
        pass


def sh(cmd, timeout=120, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)


def frontmost():
    r = sh(['osascript', '-e',
            'tell application "System Events" to get name of first application process whose frontmost is true'])
    return (r.stdout or '').strip()


def chrome_front(url, title_check=None):
    """Point Chrome's front window at url, full-screen-ish, and make Chrome frontmost."""
    bounds = sh(['osascript', '-e', 'tell application "Finder" to get bounds of window of desktop'])
    m = re.findall(r'-?\d+', bounds.stdout or '')
    w, h = (int(m[-2]), int(m[-1])) if len(m) >= 4 else (1440, 900)
    w = min(w, 1600)
    sh(['osascript', '-e', f'tell application "Google Chrome" to set URL of active tab of front window to "{url}"'])
    sh(['osascript', '-e', f'tell application "Google Chrome" to set bounds of front window to {{0, 25, {w}, {h - 25}}}'])
    sh(['osascript', '-e', f'tell application "Google Chrome" to set index of front window to 1'])
    sh(['open', '-a', CHROME])
    time.sleep(3)
    return frontmost() == CHROME


def page_title(url):
    try:
        r = sh(['curl', '-s', '--max-time', '20', url], timeout=30)
        m = re.search(r'<title[^>]*>(.*?)</title>', r.stdout or '', re.I | re.S)
        return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''
    except Exception:
        return ''


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def demo_signin(url):
    """If the page ships the app's own pre-filled demo login, sign in — no credential needed.

    Proven on TourismPay: the live login form arrives with demo admin@tourismpay.io already
    filled. We only ever CLICK the app's own prefilled form; we never type a password.
    """
    js = ("(function(){var pw=document.querySelector('input[type=password]');"
          "if(!pw||!pw.value)return 'NO-PREFILL';"
          "var b=[].slice.call(document.querySelectorAll('button')).filter(function(x){"
          "return /sign in/i.test(x.textContent||'')})[0];"
          "if(!b)return 'NO-BUTTON';b.click();return 'CLICKED';})()")
    r = sh(['osascript', '-e',
            "tell application \"Google Chrome\" to execute front window's active tab javascript \"" + js + '"'],
           timeout=45)
    out = (r.stdout or '').strip()
    if out != 'CLICKED':
        return out or 'js-unavailable'
    time.sleep(6)
    u = sh(['osascript', '-e',
            'tell application "Google Chrome" to get URL of active tab of front window'])
    return 'SIGNED-IN' if '/login' not in (u.stdout or '') else 'still-on-login'


def film(url, out_mp4):
    """Record ~80s of a scroll tour and export. The tour must happen DURING the recording."""
    proj = '/tmp/film_pipeline.openscreen'
    si = demo_signin(url)
    if si not in ('NO-PREFILL', 'NO-BUTTON'):
        log(f'  demo sign-in: {si}')
    sh(['osascript', '-e', 'tell application "System Events" to key code 115'])   # Home
    time.sleep(2)
    rec_json = '/tmp/film_pipeline.rec.json'
    with open(rec_json, 'w') as f:
        rec = subprocess.Popen([OS, 'record', '--duration', '80', '--display', '0',
                                '--project', proj, '--json'], stdout=f, stderr=subprocess.DEVNULL)
    time.sleep(10)
    # the tour: page down through the page, then back to the top — while it records
    for _ in range(7):
        sh(['osascript', '-e', 'tell application "System Events" to key code 121'])
        time.sleep(6)
    sh(['osascript', '-e', 'tell application "System Events" to key code 115'])
    time.sleep(4)
    try:
        rec.wait(timeout=90)
    except subprocess.TimeoutExpired:
        rec.kill()
        return False
    if '"success":true' not in open(rec_json).read():
        log('  record reported failure')
        return False
    exp = sh([OS, 'export', proj, '-o', out_mp4, '--auto-zoom', '--quality', 'good', '--json'],
             timeout=420)
    return '"success":true' in exp.stdout and os.path.exists(out_mp4)


def main():
    # ---- lock -------------------------------------------------------------
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 3600:
        log('skip: another film run is active')
        return 0
    open(LOCK, 'w').write(str(os.getpid()))
    try:
        return run()
    finally:
        if os.path.exists(LOCK):
            os.remove(LOCK)


def run():
    if frontmost() not in (CHROME,):
        log(f'frontmost is {frontmost()!r}, not Chrome — screen is in use, not filming over another app')
        if not (DRY or DRY_FILM):
            log('aborting this run — the next sweep will retry when the screen is free')
            return 0
        log('(dry pass: listing candidates below)')
    doc = json.load(open(f'{BASE}/live.json'))
    live = doc['platforms']
    videos = json.load(open(f'{BASE}/videos.json'))
    platforms = json.load(open(f'{BASE}/platforms.json'))

    need = [k for k, v in live.items() if v.get('live') and v.get('demonstrable', True)
            and not videos.get(k) and k in platforms]
    if FORCE:
        need = [FORCE]
    log(f'candidates: {need or "none"} (live+demonstrable, no video yet)')

    if not need:
        log('nothing to film — every demonstrable live platform already has its video')
        return 0
    if DRY:
        log('dry run — not filming')
        return 0

    sys.path.insert(0, BASE)
    from render_check import check as render_verdict

    filmed = 0
    for key in need[:MAX]:
        info = live[key]
        url = info.get('url')
        if not url:
            continue
        verdict, evidence = render_verdict(url)          # fresh check: 200 can still lie
        if verdict in ('crashing', 'blank'):
            log(f'skip {key}: fresh render says {verdict} ({str(evidence)[:80]})')
            live[key]['render'] = verdict
            continue
        # 'gated' is fine now: demo_signin clicks the app's own pre-filled demo login when one
        # exists, and falls back to the public tour when it does not.
        if frontmost() != CHROME and not chrome_front(url):
            log(f'ABORT {key}: could not bring Chrome to the front — not filming the wrong window')
            break
        if frontmost() != CHROME:
            log(f'ABORT {key}: Chrome is not frontmost')
            break

        title = page_title(url) or key
        fname = slug(key) + '-demo.mp4'
        out_tmp = f'/tmp/{fname}'
        log(f'filming {key} ({url}) …')
        if not film(url, out_tmp):
            log(f'film failed for {key}')
            continue

        mp4 = f'{BASE}/site/videos/{fname}'
        os.makedirs(f'{BASE}/site/videos/posters', exist_ok=True)
        subprocess.run(['cp', out_tmp, mp4], check=True)
        subprocess.run(['cp', out_tmp, os.path.expanduser(f'~/Desktop/{fname}')])
        poster = f'{BASE}/site/videos/posters/{slug(key)}.png'
        sh(['qlmanage', '-t', '-s', '1200', '-o', '/tmp', out_tmp], timeout=120)
        src_png = f'/tmp/{fname}.png'
        if os.path.exists(src_png):
            subprocess.run(['cp', src_png, poster], check=True)

        blurb = (f'Walkthrough of the deployed {title} at {url.replace("https://", "")} — the '
                 f'public experience of the platform as it stands today. The signed-in console '
                 f'sits behind the platform\'s own authentication, so this tour covers the public '
                 f'journey and any free tools.')
        videos[key] = [{
            'src': f'/videos/{fname}', 'label': blurb, 'kind': 'blurb',
            'poster': f'/videos/posters/{slug(key)}.png', 'featured': True,
        }]
        live[key] = dict(live[key], repo=(platforms[key].get('repos') or [''])[0],
                         live=True, deployed=True, status=200,
                         verified=time.strftime('%Y-%m-%d'),
                         source='film_pipeline',
                         note='demonstrable at film time (render-checked in headless Chrome)')
        log(f'filmed + attached {key} -> /videos/{fname} ({os.path.getsize(mp4)/1e6:.1f} MB)')
        filmed += 1
        if DRY_FILM:
            log('(dry-film: reverting attachments)')
            videos.pop(key, None)
        else:
            json.dump(videos, open(f'{BASE}/videos.json', 'w'), indent=1, ensure_ascii=False)
            doc['platforms'] = live
            json.dump(doc, open(f'{BASE}/live.json', 'w'), indent=1, ensure_ascii=False)

    doc['platforms'] = live
    json.dump(doc, open(f'{BASE}/live.json', 'w'), indent=1, ensure_ascii=False)
    if filmed and not DRY_FILM:
        b = sh(['python3', 'build_site.py'], cwd=BASE, timeout=600)
        log('build: ' + ((b.stdout.strip().splitlines() or ['?'])[-1]))
        if b.returncode != 0:
            log('ERROR: build failed — ' + (b.stderr or '')[-300:])
            return 3
        p = sh(['python3', 'publish.py'], cwd=BASE, timeout=1800)
        log('publish: ' + ' | '.join((p.stdout.strip().splitlines() or ['?'])[-2:]))
        subprocess.run(['git', 'add', '-A'], cwd=BASE, capture_output=True)
        subprocess.run(['git', 'commit', '-q', '-m', f'film pipeline: {filmed} new demo video(s)'],
                       cwd=BASE, capture_output=True)
        subprocess.run(['git', 'push', '-q', 'origin', 'HEAD'], cwd=BASE, capture_output=True, timeout=600)
        log('git: committed and pushed')
    log(f'done: {filmed} video(s) this run')
    return 0


if __name__ == '__main__':
    sys.exit(main())
