// Browser check of the first-visit tour at phone size, light and dark:
//   node tests/fixtures/tour_smoke.mjs path/to/data.json     (docs/ served on :8765)
// first load shows it; Next walks every step with no sideways overflow; Skip closes it for good;
// #tour brings it back.
import { chromium } from 'playwright';
import fs from 'fs';
const BASE = `http://localhost:${process.env.SMOKE_PORT || 8765}`;   // tests/run_smokes.py passes a free port
const data = fs.readFileSync(process.argv[2] || 'docs/data.json', 'utf8');
const chartjs = process.env.CHARTJS ? fs.readFileSync(process.env.CHARTJS, 'utf8') : null;
const b = await chromium.launch(process.env.CHROMIUM ? {executablePath: process.env.CHROMIUM} : {});
let failed = 0;
for (const scheme of ['light', 'dark']) {
  const ctx = await b.newContext({viewport:{width:390, height:844}, serviceWorkers:'block', colorScheme:scheme});
  if (chartjs) await ctx.route('**/cdnjs.cloudflare.com/**', r=>r.fulfill({body:chartjs, contentType:'application/javascript', headers:{'access-control-allow-origin':'*'}}));
  await ctx.route('**/data.json*', r=>r.fulfill({body:data, contentType:'application/json'}));
  const p = await ctx.newPage(), errs = [], log = [];
  p.on('pageerror', e=>errs.push(e.message));
  await p.goto(`${BASE}/index.html`); await p.waitForTimeout(1300);
  if (!await p.$('#tour')) errs.push('tour did not appear on first visit');
  else {
    const n = Number((await p.textContent('#tour .count')).split(' of ')[1]);
    for (let i = 1; i <= n; i++) {
      const st = await p.evaluate(()=>({count: document.querySelector('#tour .count').textContent,
        hl: document.querySelectorAll('.tour-hl').length, w: document.documentElement.scrollWidth,
        focus: document.activeElement && document.activeElement.closest('#tour') ? 'in' : 'out'}));
      log.push(st.count);
      if (st.hl !== 1) errs.push(`step ${i}: ${st.hl} highlighted elements`);
      if (st.w > 390) errs.push(`step ${i}: page ${st.w}px wide`);
      if (st.focus !== 'in') errs.push(`step ${i}: focus left the tour`);
      await p.keyboard.press('Tab'); await p.keyboard.press('Tab'); await p.keyboard.press('Tab'); await p.keyboard.press('Tab');
      if (!await p.evaluate(()=>!!document.activeElement.closest('#tour'))) errs.push(`step ${i}: Tab escaped the tour`);
      if (i < n) { await p.click('#tour button:has-text("Next")'); await p.waitForTimeout(250); }
    }
    await p.click('#tour button:has-text("Done")'); await p.waitForTimeout(200);
    if (await p.$('#tour') || await p.$('.tour-hl')) errs.push('Done did not close the tour');
  }
  await p.reload(); await p.waitForTimeout(1300);
  if (await p.$('#tour')) errs.push('tour came back after it was finished');
  await p.goto(`${BASE}/index.html#tour`); await p.reload(); await p.waitForTimeout(1300);
  if (!await p.$('#tour')) errs.push('#tour did not reopen it');
  else { await p.keyboard.press('Escape'); await p.waitForTimeout(200); if (await p.$('#tour')) errs.push('Esc did not close it'); }
  await p.goto(`${BASE}/index.html`); await p.waitForTimeout(800);
  await p.click('nav button[data-tab="how"]'); await p.click('#tour-again'); await p.waitForTimeout(300);
  if (!await p.$('#tour')) errs.push('"Take the tour" did not start it');
  else { await p.click('#tour button:has-text("Skip")'); await p.waitForTimeout(200);
    const tab = await p.evaluate(()=>document.querySelector('nav button[aria-selected="true"]').dataset.tab);
    if (tab !== 'how') errs.push(`after Skip the tab was ${tab}, not how`); }
  console.log(scheme, 'steps:', log.join(', ') || '—', '| errors:', errs.length ? errs : 'none');
  if (errs.length) failed = 1;
  await ctx.close();
}
await b.close();
process.exit(failed);
