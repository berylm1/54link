/* 54link shared page script: hamburger menu, platform search, brochure form.
   Loaded by every page; each part no-ops when its elements are absent. */
/* ---- hamburger menu ---- */
(function () {
  const nav = document.getElementById('topnav');
  const btn = document.getElementById('burger');
  if (!nav || !btn) return;
  function setOpen(v) {
    nav.classList.toggle('open', v);
    btn.setAttribute('aria-expanded', v ? 'true' : 'false');
    btn.setAttribute('aria-label', v ? 'Close menu' : 'Open menu');
  }
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    setOpen(!nav.classList.contains('open'));
  });
  Array.prototype.forEach.call(document.querySelectorAll('#navmenu a'), function (a) {
    a.addEventListener('click', function () { setOpen(false); });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
  document.addEventListener('click', function (e) {
    if (nav.classList.contains('open') && !nav.contains(e.target)) setOpen(false);
  });
})();

/* ---- platform search ---- */
(function () {
  const input = document.getElementById('psearch');
  const grid = document.getElementById('platformgrid');
  const countEl = document.getElementById('pcount');
  const clearBtn = document.getElementById('pclear');
  const noHits = document.getElementById('pnohits');
  if (!input || !grid) return;
  const cards = Array.from(grid.querySelectorAll('.pcard'));
  const total = cards.length;
  function apply() {
    const q = input.value.trim().toLowerCase();
    const terms = q.split(/\s+/).filter(Boolean);
    let shown = 0;
    cards.forEach(function (c) {
      const hay = (c.getAttribute('data-search') || c.innerText || '').toLowerCase();
      const hit = terms.every(function (t) { return hay.indexOf(t) !== -1; });
      c.style.display = hit ? '' : 'none';
      if (hit) shown++;
    });
    if (!q) {
      countEl.textContent = total + ' platforms';
      clearBtn.style.display = 'none';
    } else {
      countEl.textContent = shown + ' of ' + total;
      clearBtn.style.display = 'block';
    }
    noHits.style.display = (q && shown === 0) ? 'block' : 'none';
  }
  input.addEventListener('input', apply);
  clearBtn.addEventListener('click', function () { input.value = ''; input.focus(); apply(); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { input.value = ''; apply(); }
    if (e.key === 'Enter') {
      const first = cards.find(function (c) { return c.style.display !== 'none'; });
      if (first) {
        first.open = true;
        const link = first.querySelector('.cardlink a');
        if (link) link.click();
      }
    }
  });
  // focus search with "/" key
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== input) { e.preventDefault(); input.focus(); }
  });
  apply();
})();

const ENDPOINT = './.herenow/data/registrations';
const regForm = document.getElementById('regform');
if (regForm) { regForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('regmsg');
  const btn = e.target.querySelector('button');
  btn.disabled = true; btn.textContent = 'Registering…';
  const record = {
    name: document.getElementById('r-name').value.trim(),
    email: document.getElementById('r-email').value.trim(),
    organisation: document.getElementById('r-org').value.trim(),
    interest: document.getElementById('r-interest').value.trim()
  };
  try {
    const res = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify(record)
    });
    if (!res.ok) throw new Error('status ' + res.status);
    msg.className = 'msg ok';
    msg.textContent = 'Registered — your brochure download is starting.';
    setTimeout(() => window.open('/brochure.pdf', '_blank'), 900);
    e.target.reset();
  } catch (err) {
    msg.className = 'msg err';
    msg.textContent = 'Registration failed — please try again or email us directly.';
  } finally {
    btn.disabled = false; btn.textContent = 'Register & download brochure';
  }
});
}
