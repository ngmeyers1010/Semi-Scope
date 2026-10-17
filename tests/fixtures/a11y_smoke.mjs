// Accessibility audit with axe-core at phone size, light and dark (docs/ served on :8765):
//   AXE=path/to/axe.min.js node tests/fixtures/a11y_smoke.mjs [data.json]
// Every dashboard tab, a stock's detail panel, the first-visit tour, weekly.html and setup.html.
// Fails (exit 1) on any "serious" or "critical" WCAG 2 A/AA violation; prints the rest.
import { chromium } from 'playwright';
import fs from 'fs';
const BASE = `http://localhost:${process.env.SMOKE_PORT || 8765}`;   // tests/run_smokes.py passes a free port
const axe = fs.readFileSync(process.env.AXE, 'utf8');
const data = fs.readFileSync(process.argv[2] || 'docs/data.json', 'utf8');
const chartjs = process.env.CHARTJS ? fs.readFileSync(process.env.CHARTJS, 'utf8') : null;
const b = await chromium.launch(process.env.CHROMIUM ? {executablePath: process.env.CHROMIUM} : {});
const found = new Map();     // rule -> {impact, help, n, targets:Set, where:Set}
async function audit(p, where) {
  await p.addScriptTag({content: axe});
  const r = await p.evaluate(async () => (await axe.run(document, {
    runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']},
    resultTypes: ['violations']})).violations.map(v => ({id: v.id, impact: v.impact, help: v.help,
      targets: v.nodes.map(n => n.target.join(' ') + (n.any[0] && n.any[0].data && n.any[0].data.contrastRatio ? ` (${n.any[0].data.contrastRatio}:1 ${n.any[0].data.fgColor} on ${n.any[0].data.bgColor})` : ''))})));
  for (const v of r) {
    const e = found.get(v.id) || {impact: v.impact, help: v.help, n: 0, targets: new Set(), where: new Set()};
    e.n += v.targets.length; v.targets.forEach(t => e.targets.add(t)); e.where.add(where); found.set(v.id, e);
  }
}
for (const scheme of ['light', 'dark']) {
  const ctx = await b.newContext({viewport:{width:390, height:844}, serviceWorkers:'block', colorScheme:scheme});
  await ctx.addInitScript(() => { try { localStorage.setItem('semiscope.tour', 'done'); } catch (e) {} });
  if (chartjs) await ctx.route('**/cdnjs.cloudflare.com/**', r=>r.fulfill({body:chartjs, contentType:'application/javascript', headers:{'access-control-allow-origin':'*'}}));
  await ctx.route('**/data.json*', r=>r.fulfill({body:data, contentType:'application/json'}));
  const p = await ctx.newPage();
  await p.goto(`${BASE}/index.html`); await p.waitForTimeout(1200);
  for (const tab of await p.$$eval('nav button', bs=>bs.map(b=>b.dataset.tab))) {
    await p.click(`nav button[data-tab="${tab}"]`); await p.waitForTimeout(500);
    await audit(p, `${scheme}:${tab}`);
  }
  await p.click('nav button[data-tab="rank"]'); await p.waitForTimeout(300);
  await p.evaluate(() => showDetail(D.rankings.find(r => r.rank === 1).ticker)); await p.waitForTimeout(500);
  await audit(p, `${scheme}:detail`);
  await p.goto(`${BASE}/index.html#tour`); await p.reload(); await p.waitForTimeout(1300);
  await audit(p, `${scheme}:tour`);
  for (const page of ['weekly.html', 'setup.html']) {
    await p.goto(`${BASE}/${page}`); await p.waitForTimeout(900);
    await audit(p, `${scheme}:${page}`);
  }
  await ctx.close();
}
await b.close();
let bad = 0;
const order = {critical: 0, serious: 1, moderate: 2, minor: 3};
for (const [id, e] of [...found].sort((a, b) => order[a[1].impact] - order[b[1].impact])) {
  if (e.impact === 'critical' || e.impact === 'serious') bad += e.n;
  console.log(`${e.impact.padEnd(8)} ${id} ×${e.n} — ${e.help}\n    where: ${[...e.where].slice(0, 6).join(', ')}${e.where.size > 6 ? ' …' : ''}\n    e.g.: ${[...e.targets].slice(0, 2).join(' | ')}`);
}
console.log(found.size ? `${bad} serious/critical node(s)` : 'no violations');
if (process.env.A11Y_COLORS) {                    // which colour pairs fail contrast, and where
  const pairs = new Map();
  for (const t of (found.get('color-contrast') || {targets: new Set()}).targets) {
    const m = /\(([\d.]+):1 (#\w+) on (#\w+)\)$/.exec(t); if (!m) continue;
    const k = `${m[2]} on ${m[3]} (${m[1]})`; const e = pairs.get(k) || {n: 0, ex: t}; e.n++; pairs.set(k, e);
  }
  [...pairs].sort((a, b) => b[1].n - a[1].n).forEach(([k, e]) => console.log(`  ${k} ×${e.n}  e.g. ${e.ex.slice(0, 90)}`));
}
process.exit(bad ? 1 : 0);
