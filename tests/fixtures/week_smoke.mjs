// Browser check of "What changed this week" (Rankings tab) at phone size, light and dark:
//   node tests/fixtures/week_smoke.mjs path/to/data.json     (docs/ served on :8765)
// The card shows when week_ranks exists (hidden otherwise), has 3 columns, every ticker is a link
// that opens the stock's detail, and the page never scrolls sideways. With rank_history, top rows
// carry an "N wk in top 5" streak pill (only rows inside the top N).
import { chromium } from 'playwright';
import fs from 'fs';
const BASE = `http://localhost:${process.env.SMOKE_PORT || 8765}`;   // tests/run_smokes.py passes a free port
const data = fs.readFileSync(process.argv[2] || 'docs/data.json', 'utf8');
const want = !!JSON.parse(data).week_ranks, wantPills = !!JSON.parse(data).rank_history;
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
  await p.goto(`${BASE}/index.html#tab=rank&card=week-card`); await p.waitForTimeout(1300);
  const st = await p.evaluate(()=>{ const c = document.getElementById('week-card');
    return {hidden: c.hidden, cols: c.querySelectorAll('#week-body > div').length, links: [...c.querySelectorAll('a')].map(a=>a.textContent),
            w: document.documentElement.scrollWidth, text: c.innerText.slice(0, 200),
            pills: [...document.querySelectorAll('#rank-table .pill.streak')].map(p=>({t:p.textContent, top:p.closest('tr').classList.contains('top')}))}; });
  if (wantPills && !st.pills.length) errs.push('no streak pills');
  if (!wantPills && st.pills.length) errs.push('streak pills without rank_history');
  if (st.pills.some(p=>!p.top || !/^\d+\+? wk in top \d+$/.test(p.t))) errs.push('bad streak pill: ' + JSON.stringify(st.pills));
  if (st.hidden === want) errs.push(`card hidden=${st.hidden} but week_ranks ${want ? 'exists' : 'is missing'}`);
  if (want) {
    if (st.cols !== 3) errs.push(`${st.cols} columns, expected 3`);
    if (!st.links.length) errs.push('no ticker links');
    else {
      await p.click('#week-card a'); await p.waitForTimeout(500);
      const shown = await p.evaluate(()=>{ const d = document.getElementById('detail'); return d && !d.hidden ? d.innerText.slice(0, 80) : ''; });
      if (!shown.includes(st.links[0])) errs.push(`clicking ${st.links[0]} didn't open its detail`);
    }
  }
  if (st.w > 390) errs.push(`page ${st.w}px wide`);
  console.log(`${scheme} ${want ? `links: ${st.links.join(', ')}` : 'hidden (no week_ranks)'} | pills: ${st.pills.map(p=>p.t).join(', ') || 'none'} | errors: ${errs.join('; ') || 'none'}`);
  failed += errs.length; await ctx.close();
}
await b.close();
process.exit(failed ? 1 : 0);
