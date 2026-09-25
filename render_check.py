#!/usr/bin/env python3
"""Render-check a URL in headless Chrome and classify what a visitor actually gets.

A 200 status hides three very different things: a working app, an app that throws on
startup, and an app gated behind a login. This renders the page (JavaScript included)
and says which one it is.

Usage:
    python3 render_check.py <url> [<url> ...]     # print a verdict per URL
    from render_check import classify_dom         # use as a library
"""
import html
import re
import subprocess
import sys

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

# what a crashed / misconfigured front end looks like
CRASH_PATTERNS = [
    'an unexpected error occurred', 'something went wrong', 'unhandled',
    'must be configured', 'is not configured', 'configuration error',
    'failed to fetch', 'cannot read prop', 'is not a function', 'undefined is not',
    'internal server error', 'application error', 'vite_', 'process is not defined',
]
# what a login wall looks like
GATED_PATTERNS = [
    'sign in', 'log in', 'login', 'password', 'forgot password', 'username',
    'continue with', 'single sign-on', 'keycloak',
]


def strip_tags(dom):
    dom = re.sub(r'<(script|style|noscript)\b.*?</\1>', ' ', dom, flags=re.S | re.I)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', dom))
    return re.sub(r'\s+', ' ', text).strip()


def render(url, budget=9000, timeout=75):
    """Return the post-JavaScript DOM, or None if Chrome could not produce one."""
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
           '--no-default-browser-check', '--disable-extensions', '--mute-audio',
           f'--virtual-time-budget={budget}', '--dump-dom', url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout or None


def classify_dom(dom):
    """-> (verdict, evidence). verdict: demonstrable | crashing | gated | blank."""
    if not dom:
        return 'blank', 'no DOM produced'
    text = strip_tags(dom)
    low = text.lower()
    # a crash wins over a login form: an error page often mentions the word 'login'
    for pat in CRASH_PATTERNS:
        i = low.find(pat)
        if i != -1:
            snippet = text[max(0, i - 60):i + 120].strip()
            return 'crashing', snippet[:180]
    if len(text) < 120:
        return 'blank', f'only {len(text)} chars of text after render'
    # a real login wall has a password field; a landing page with a "Sign In" link does not
    if re.search(r'type=["\']password["\']', dom, re.I):
        return 'gated', 'login form (password field present)'
    hits = [p for p in GATED_PATTERNS if p in low]
    if hits and len(text) < 1200:
        return 'gated', 'login wall (' + ', '.join(sorted(set(hits))[:3]) + ')'
    return 'demonstrable', f'{len(text)} chars rendered' + (
        ' (has a sign-in entry point)' if hits else '')


def check(url):
    return classify_dom(render(url))


if __name__ == '__main__':
    urls = sys.argv[1:]
    if not urls:
        sys.exit('usage: render_check.py <url> [<url> ...]')
    for u in urls:
        verdict, evidence = check(u)
        print(f'{verdict:<12} {u}')
        print(f'             {evidence}')
