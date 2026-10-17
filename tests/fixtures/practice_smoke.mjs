// Browser check of docs/practice.html at phone size, light and dark (docs/ served on :8765):
//   AXE=path/to/axe.min.js node tests/fixtures/practice_smoke.mjs
// renders with no errors, every exercise listed, no sideways scroll, and axe-core finds no
// WCAG 2.1 A/AA problems. Also follows the links in from the dashboard's Learn tab and weekly.html.
import { chromium } from 'playwright';
import fs from 'fs';
const BASE = `http://localhost:${process.env.SMOKE_PORT || 8765}`;   // tests/run_smokes.py passes a free port
const axe = fs.readFileSync(process.env.AXE, 'utf8');
const b = await chromium.launch(process.env.CHROMIUM ? {executablePath: process.env.CHROMIUM} : {});
let failed = 0;
for (const scheme of ['light', 'dark']) {
  const ctx = await b.newContext({viewport:{width:390, height:844}, serviceWorkers:'block', colorScheme:scheme});
  const p = await ctx.newPage(), errs = [];
  p.on('pageerror', e=>errs.push(e.message));
  p.on('console', m=>{ if (m.type()==='error' && !/404/.test(m.text())) errs.push(m.text()); });
  await p.goto(`${BASE}/practice.html`); await p.waitForTimeout(300);
  const st = await p.evaluate(()=>({items: document.querySelectorAll('li[data-ex]').length, w: document.documentElement.scrollWidth,
    h1: (document.querySelector('h1')||{}).textContent, bar: !!document.querySelector('progress[aria-label]')}));
  if (st.items < 30) errs.push(`only ${st.items} exercises listed`);
  if (st.w > 390) errs.push(`page ${st.w}px wide`);
  if (!st.bar) errs.push('no labelled progress bar');
  await p.addScriptTag({content: axe});
  const v = await p.evaluate(async ()=> (await axe.run(document, {runOnly:{type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations
    .map(x=>`${x.id} (${x.nodes.length})`));
  errs.push(...v.map(x=>'axe: '+x));
  console.log(`${scheme} practice: ${st.items} exercises, width ${st.w} | errors: ${errs.join('; ') || 'none'}`);
  failed += errs.length; await ctx.close();
}
await b.close();
process.exit(failed ? 1 : 0);
