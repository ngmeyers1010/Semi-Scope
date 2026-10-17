// Browser smoke test: load the dashboard with a sparse "first live run" data.json and
// open every tab. Any JS error fails. Run from docs/ served on :8765:
//   node tests/fixtures/sparse_smoke.mjs path/to/sparse_data.json
import { chromium } from 'playwright';
import fs from 'fs';
const BASE = `http://localhost:${process.env.SMOKE_PORT || 8765}`;   // tests/run_smokes.py passes a free port
const data = fs.readFileSync(process.argv[2] || 'tests/fixtures/sparse_data.json', 'utf8');
const chartjs = process.env.CHARTJS ? fs.readFileSync(process.env.CHARTJS, 'utf8') : null;
const b = await chromium.launch(process.env.CHROMIUM ? {executablePath: process.env.CHROMIUM} : {});
let failed = 0;
for (const scheme of ['light', 'dark']) {
  const ctx = await b.newContext({viewport:{width:390, height:844}, serviceWorkers:'block', colorScheme:scheme});
  await ctx.addInitScript(() => { try { localStorage.setItem('semiscope.tour', 'done'); } catch (e) {} });   // skip the first-visit tour
  if (chartjs) await ctx.route('**/cdnjs.cloudflare.com/**', r=>r.fulfill({body:chartjs, contentType:'application/javascript', headers:{'access-control-allow-origin':'*'}}));
  await ctx.route('**/data.json*', r=>r.fulfill({body:data, contentType:'application/json'}));
  const p = await ctx.newPage(), errs = [];
  p.on('pageerror', e=>errs.push(e.message));
  p.on('console', m=>{ if (m.type()==='error' && !/404|run_log/.test(m.text())) errs.push(m.text()); });
  await p.goto(`${BASE}/index.html`); await p.waitForTimeout(1000);
  for (const tab of await p.$$eval('nav button', bs=>bs.map(b=>b.dataset.tab))) {
    await p.click(`nav button[data-tab="${tab}"]`); await p.waitForTimeout(400);
    if (tab === 'mine') for (const row of await p.$$('#mine-table tr[data-t]')) { await row.click().catch(()=>{}); await p.waitForTimeout(80); await p.click('nav button[data-tab="mine"]'); }
    if (tab === 'rank') { await p.evaluate(()=>{ CMP=['ASML','AMZN']; renderCompare(); showDetail('ASML'); }); await p.waitForTimeout(300); }
  }
  // jump chips: on the Backtest tab, tapping the last chip brings that card to the top of the screen
  await p.click('nav button[data-tab="bt"]'); await p.waitForTimeout(300);
  const chips = await p.$$('#tab-bt > .jump button[data-card]');
  let jump = 'no chips';
  if (chips.length) {
    const target = await chips[chips.length - 1].getAttribute('data-card');
    await chips[chips.length - 1].click(); await p.waitForTimeout(900);
    const top = await p.evaluate(id => document.getElementById(id).getBoundingClientRect().top, target);
    jump = `${chips.length} chips, #${target} top=${Math.round(top)}`;
    if (top < -5 || top > 200) { errs.push(`jump chip didn't scroll to #${target} (top ${top})`); }
  }
  const w = await p.evaluate(()=>document.documentElement.scrollWidth);
  console.log(scheme, 'jump:', jump);
  console.log(scheme, 'errors:', errs.length ? errs : 'none', '| width', w);
  if (errs.length || w > 390) failed = 1;
  await ctx.close();
}
await b.close();
process.exit(failed);
