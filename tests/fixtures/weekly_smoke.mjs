// Browser smoke test for docs/weekly.html (and the #stock= deep link it uses). Run from docs/ served on :8765:
//   node tests/fixtures/weekly_smoke.mjs path/to/data.json [screenshot.png]
import { chromium } from 'playwright';
import fs from 'fs';
const BASE = `http://localhost:${process.env.SMOKE_PORT || 8765}`;   // tests/run_smokes.py passes a free port
const data = fs.readFileSync(process.argv[2], 'utf8');
const chartjs = process.env.CHARTJS ? fs.readFileSync(process.env.CHARTJS, 'utf8') : null;
const b = await chromium.launch(process.env.CHROMIUM ? {executablePath: process.env.CHROMIUM} : {});
let failed = 0;
for (const scheme of ['light', 'dark']) {
  const ctx = await b.newContext({viewport:{width:390, height:844}, serviceWorkers:'block', colorScheme:scheme, deviceScaleFactor:2});
  await ctx.addInitScript(() => { try { localStorage.setItem('semiscope.tour', 'done'); } catch (e) {} });   // skip the first-visit tour
  if (chartjs) await ctx.route('**/cdnjs.cloudflare.com/**', r=>r.fulfill({body:chartjs, contentType:'application/javascript', headers:{'access-control-allow-origin':'*'}}));
  await ctx.route('**/data.json*', r=>r.fulfill({body:data, contentType:'application/json'}));
  const p = await ctx.newPage(), errs = [];
  p.on('pageerror', e=>errs.push(e.message));
  p.on('console', m=>{ if (m.type()==='error' && !/404|run_log|detail/.test(m.text())) errs.push(m.text()); });
  await p.goto(`${BASE}/weekly.html`); await p.waitForTimeout(800);
  const asof = await p.textContent('#asof');
  if (/Loading|Couldn't/.test(asof)) errs.push('page did not render: ' + asof);
  const width = await p.evaluate(()=>document.documentElement.scrollWidth);
  if (width > 390) errs.push('horizontal scroll: ' + width);
  // "This week in the rankings": shown (with text and a dashboard link) exactly when weekly.rankings_week exists
  const rw = await p.evaluate(()=>{ const c = document.getElementById('rankweek-card');
    return c ? {hidden: c.hidden, text: document.getElementById('rankweek').textContent, href: document.getElementById('rankweek-link').getAttribute('href')} : null; });
  const wantRW = !!((JSON.parse(data).weekly||{}).rankings_week);
  if (!rw) errs.push('no rankweek card');
  else if (rw.hidden === wantRW) errs.push(`rankweek hidden=${rw.hidden} but data ${wantRW ? 'has' : 'lacks'} it`);
  else if (wantRW && (!rw.text || !/^index\.html#tab=rank&card=week-card/.test(rw.href))) errs.push('rankweek empty or bad link: ' + JSON.stringify(rw));
  if (scheme === 'light' && process.argv[3]) await p.screenshot({path: process.argv[3], fullPage: true});
  // follow the first question's link (if any) into the dashboard
  const link = await p.$('#qs a');
  if (link) { await link.click(); await p.waitForTimeout(1200); }
  console.log(scheme, 'rankings week:', rw && !rw.hidden ? 'shown' : 'hidden', '| errors:', errs.length ? errs.join(' | ') : 'none', '| width', width);
  failed += errs.length;
  await ctx.close();
}
await b.close();
process.exit(failed ? 1 : 0);
