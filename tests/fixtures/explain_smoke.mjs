// Browser check of the "?" explanations on KPI tiles, phone size, light and dark (docs/ served on :8765):
//   node tests/fixtures/explain_smoke.mjs path/to/data.json
// Risk card (Paper tab), Backtest headline, edge and steady tiles: each "?" opens its explanation by click (aria-expanded flips, text has a number),
// opening one closes the others, Esc closes and puts focus back on the button, Enter/Space work
// from the keyboard, and the page never scrolls sideways.
import { chromium } from 'playwright';
import fs from 'fs';
const BASE = `http://localhost:${process.env.SMOKE_PORT || 8765}`;   // tests/run_smokes.py passes a free port
const data = fs.readFileSync(process.argv[2] || 'docs/data.json', 'utf8');
const chartjs = process.env.CHARTJS ? fs.readFileSync(process.env.CHARTJS, 'utf8') : null;
const b = await chromium.launch(process.env.CHROMIUM ? {executablePath: process.env.CHROMIUM} : {});
let failed = 0;
for (const scheme of ['light', 'dark']) {
  const ctx = await b.newContext({viewport:{width:390, height:844}, serviceWorkers:'block', colorScheme:scheme});
  await ctx.addInitScript(() => { try { localStorage.setItem('semiscope.tour', 'done'); } catch (e) {} });
  if (chartjs) await ctx.route('**/cdnjs.cloudflare.com/**', r=>r.fulfill({body:chartjs, contentType:'application/javascript', headers:{'access-control-allow-origin':'*'}}));
  await ctx.route('**/data.json*', r=>r.fulfill({body:data, contentType:'application/json'}));
  const p = await ctx.newPage(), errs = [];
  p.on('pageerror', e=>errs.push(e.message));
  let total = 0, practiced = 0;
  for (const [tab, sel, need] of [['paper', '#risk-tiles', 4], ['bt', '#bt-tiles', 4], ['bt', '#edge-body', 0], ['bt', '#steady-tiles', 0]]) {
    await p.goto(`${BASE}/index.html#tab=${tab}`); await p.reload(); await p.waitForTimeout(1300);   // a hash change alone does not reload
    const btns = await p.$$(`${sel} .tip-btn`);
    const visible = await p.evaluate(sel=>{ const e = document.querySelector(sel); return !!e && !e.closest('[hidden]'); }, sel);
    if (!visible || !btns.length) { if (need) errs.push(`${sel}: ${btns.length} ? buttons (want ${need}+)`); continue; }
    if (btns.length < need) errs.push(`${sel}: only ${btns.length} ? buttons`);
    total += btns.length;
    for (let i = 0; i < btns.length; i++) {
      await btns[i].scrollIntoViewIfNeeded(); await btns[i].click(); await p.waitForTimeout(50);
      const st = await p.evaluate(([sel, i])=>{ const bs = [...document.querySelectorAll(sel + ' .tip-btn')];
        const t = document.getElementById(bs[i].getAttribute('aria-controls'));
        return {exp: bs[i].getAttribute('aria-expanded'), shown: !t.hidden, text: t.textContent,
                practice: t.textContent.includes('Practice it') ? !!t.querySelector('a[href^="practice.html#ex-"]') : null,
                others: [...document.querySelectorAll('.tip-btn')].filter(b=>b!==bs[i] && b.getAttribute('aria-expanded')==='true').length,
                w: document.documentElement.scrollWidth}; }, [sel, i]);
      if (st.exp !== 'true' || !st.shown) errs.push(`${sel} button ${i} did not open`);
      if (!/\d/.test(st.text) || st.text.length < 40) errs.push(`${sel} button ${i}: weak text "${st.text}"`);
      if (st.practice === false) errs.push(`${sel} button ${i}: "Practice it" without a link`);
      if (st.practice) practiced++;
      if (st.others) errs.push(`${sel} button ${i}: ${st.others} other tips still open`);
      if (st.w > 390) errs.push(`page ${st.w}px wide with ${sel} tip ${i} open`);
    }
  }
  const btns = {length: total};
  if (!practiced) errs.push('no "Practice it" line in any explanation');
  // Learn tab: the same line under terms that have an exercise, each linking to practice.html#ex-N
  await p.goto(`${BASE}/index.html#tab=learn`); await p.reload(); await p.waitForTimeout(800);
  const lp = await p.evaluate(()=>[...document.querySelectorAll('#terms dd.practice-it a')].map(a=>a.getAttribute('href')));
  if (lp.length < 15 || lp.some(h=>!/^practice\.html#ex-\d+$/.test(h))) errs.push(`Learn practice links: ${lp.length}`);
  // keyboard checks on a fresh page: open the first Risk "?" by click, then Esc / Enter / Space
  await p.goto(`${BASE}/index.html#tab=paper`); await p.reload(); await p.waitForTimeout(1300);
  const first = await p.$('#risk-tiles .tip-btn, #bt-tiles .tip-btn');
  if (first) { await first.scrollIntoViewIfNeeded(); await first.click(); await p.waitForTimeout(50); }
  await p.keyboard.press('Escape'); await p.waitForTimeout(50);
  const esc = await p.evaluate(()=>({open: document.querySelectorAll('.tip-btn[aria-expanded="true"]').length,
    focus: document.activeElement && document.activeElement.classList.contains('tip-btn')}));
  if (esc.open) errs.push('Esc did not close'); if (!esc.focus) errs.push('focus did not return to the button');
  await p.keyboard.press('Enter'); await p.waitForTimeout(50);
  if (!await p.evaluate(()=>document.activeElement.getAttribute('aria-expanded')==='true')) errs.push('Enter did not open');
  await p.keyboard.press(' '); await p.waitForTimeout(50);
  if (await p.evaluate(()=>document.activeElement.getAttribute('aria-expanded')==='true')) errs.push('Space did not close');
  console.log(`${scheme} explain: ${btns.length} buttons, ${practiced} with practice links, ${lp.length} on Learn | errors: ${errs.join('; ') || 'none'}`);
  failed += errs.length; await ctx.close();
}
await b.close();
process.exit(failed ? 1 : 0);
