// SemiScope dashboard helpers: small pure functions the page uses, kept apart from the page code so
// tests can run them in node (each block sits between "// ---- name ----" and "// ---- end name ----").
// Loaded by index.html with a plain <script src="helpers.js"> before the page script: no modules,
// everything here is a global the page calls.

// ---- explain tile ----  (pure: plain text in, plain text out; the page sets it with textContent)
function explainTile(term, def, v){
  v = v || {};
  const ok = x => typeof x === 'number' && isFinite(x);
  const p1 = x => `${x>=0?'+':'−'}${Math.abs(x*100).toFixed(1)}%`;
  const usd = x => '$' + Math.round(x).toLocaleString('en-US');
  let s = '';
  if (term === 'CAGR' && ok(v.cagr)){
    s = `CAGR ${p1(v.cagr)}: money in this strategy grew about ${Math.abs(v.cagr*100).toFixed(1)}% a year on average`;
    if (ok(v.total) && v.end) s += `, so $1,000${v.start ? ` in ${v.start.slice(0,4)}` : ''} would be about ${usd(1000*(1+v.total))} by ${v.end}`;
    s += ok(v.spy) ? ` (S&P 500: ${p1(v.spy)} a year).` : '.';
  } else if (term === 'Sharpe ratio' && ok(v.sharpe)){
    s = `Sharpe ${v.sharpe.toFixed(2)}: about ${v.sharpe.toFixed(2)} of yearly return for each 1 of yearly bounce (volatility)` + (ok(v.spy) ? `; the S&P 500 managed ${v.spy.toFixed(2)}.` : '.');
  } else if (term === 'Max drawdown' && ok(v.mdd)){
    s = `Max drawdown ${p1(v.mdd).replace('.0%','%')}: at the worst point, $1,000 at the previous high had shrunk to about ${usd(1000*(1+v.mdd))}` + (ok(v.spy) ? ` (S&P 500 worst: ${p1(v.spy)}).` : '.');
  } else if (term === 'Hit rate' && ok(v.rate) && ok(v.n)){
    s = `It beat the S&P 500 in ${Math.round(v.rate*100)}% of ${v.n} quarters (about ${Math.round(v.rate*v.n)} of them). Above 50% is better than a coin flip; how much it wins by matters too.`;
  } else if (term === 'Volatility' && ok(v.vol)){
    s = `Volatility ${Math.round(v.vol*100)}%: in a typical year these stocks could easily land about ${Math.round(v.vol*100)}% above or below their average return.`;
  } else if (term === 'Beta' && ok(v.beta)){
    s = `Beta ${v.beta.toFixed(2)}: when the S&P 500 moved 1%, these stocks tended to move about ${v.beta.toFixed(1)}% the same way, so a 10% market drop would be roughly ${Math.abs(v.beta*10).toFixed(0)}% for them.`;
  } else if (term === 'VaR (value at risk)' && ok(v.dollars) && ok(v.amount)){
    s = `On a bad day (about 1 trading day in 20), ${usd(v.amount)} in these stocks could lose about ${usd(Math.abs(v.dollars))}` + (ok(v.var) ? ` (${(Math.abs(v.var)*100).toFixed(1)}%)` : '') + ' or more.';
  } else if (term === 'Effective bets' && ok(v.eff) && ok(v.n)){
    s = `These ${v.n} stocks act like about ${v.eff.toFixed(1)} independent bets` + (v.eff < v.n/2 ? ', because they tend to rise and fall together.' : '.');
  } else if (term === 'Information ratio' && ok(v.ir)){
    s = `Information ratio ${v.ir.toFixed(2)}: each 1% a year of wandering away from SPY came with about ${Math.abs(v.ir).toFixed(2)}% a year of ${v.ir >= 0 ? 'lead' : 'lag'}. 0.5+ is good for a stock picker.`;
  } else if (term === 'Tracking error' && ok(v.te)){
    s = `Tracking error ${(v.te*100).toFixed(1)}%: in a typical year the strategy ends up about ${(v.te*100).toFixed(0)}% ahead of or behind SPY.`;
  } else if (term === 't-stat' && ok(v.t)){
    s = `t ${v.t.toFixed(1)}: the average edge over SPY is ${v.t.toFixed(1)} standard errors ${v.t >= 0 ? 'above' : 'below'} zero` + (ok(v.n) ? ` (${v.n} quarters)` : '') + `; 2+ is unlikely to be luck.`;
  } else if (term === 'p-value' && ok(v.p)){
    s = v.p < 0.001 ? 'p < 0.001: if there were no real edge, luck alone would almost never look this good.'
      : `p ${v.p.toFixed(3)}: if there were no real edge, luck alone would look this good about ${v.p < 0.1 ? (v.p*100).toFixed(1) : Math.round(v.p*100)}% of the time (about 1 in ${Math.max(1, Math.round(1/v.p))}).`;
  } else if (term === 'P&L (profit and loss)' && ok(v.pnl)){
    const sm = x => `${x<0?'−':''}${usd(Math.abs(x))}`;
    s = `Total P&L ${sm(v.pnl)}` + (ok(v.realized) && ok(v.unrealized) ? `: ${sm(v.realized)} locked in from shares you sold (realized) and ${sm(v.unrealized)} on shares you still own (unrealized, it can still change).` : '.');
  } else if (term === 'Paper portfolio' && ok(v.ret)){
    s = `Paper return ${p1(v.ret)}${v.since ? ` since ${v.since}` : ''}` + (ok(v.spy) ? `, vs ${p1(v.spy)} for the S&P 500 over the same days` : '') + '. These picks were recorded before the results were known.';
  }
  return [def || '', s].filter(Boolean).join(' ');
}
// Learn by doing: the practice exercise that builds each number (python practice/check.py N).
// Only where the exercise really builds it; tests/test_explain_tile.py checks every entry.
const TERM_EXERCISE = {
  'CAGR': [3, 'total_return'], 'Max drawdown': [6, 'max_drawdown'], 'Volatility': [5, 'annual_vol'],
  't-stat': [15, 't_test'], 'p-value': [15, 't_test'], 'Information ratio': [19, 'rolling_excess'],
  'Tracking error': [19, 'rolling_excess'], 'Hit rate': [11, 'mini_backtest'], 'P&L (profit and loss)': [14, 'fifo_lots'],
  'Backtest': [11, 'mini_backtest'], 'Point-in-time': [11, 'mini_backtest'], 'Factor': [10, 'momentum_z'],
  'z-score': [10, 'momentum_z'], 'σ (z-move)': [13, 'z_move'], 'Inverse-volatility weighting': [16, 'inverse_vol'],
  'P/S vs its own history': [17, 'own_percentile'], 'Composite score': [21, 'reproduce_the_score'],
  'Signal decay': [22, 'signal_decay'], 'Up/down capture': [24, 'up_down_capture'],
  'Underwater / recovery time': [25, 'drawdown_episodes'], 'Bootstrap': [26, 'bootstrap_a_range'],
  'Streak effect': [30, 'stayers_vs_new'], 'Beta': [31, 'beta_and_a_bad_day'], 'VaR (value at risk)': [31, 'beta_and_a_bad_day'],
  'Sharpe ratio': [32, 'sharpe_and_effective_bets'], 'Effective bets': [32, 'sharpe_and_effective_bets'],
  'Paper portfolio': [33, 'paper_portfolio_return'],
};
function practiceLine(term){
  const e = TERM_EXERCISE[term]; if (!e) return null;
  const n = e[0], ex = 'ex' + String(n).padStart(2, '0');
  return {text: `Practice it: ${ex} ${e[1]} (python practice/check.py ${n})`, href: `practice.html#ex-${n}`};
}
// ---- end explain tile ----

// ---- ink ----  (practice/ex28 mirrors these; a test runs both)
function _rgb(h){ h = String(h).trim().replace('#',''); if (h.length===3) h = h.split('').map(c=>c+c).join(''); return [0,2,4].map(i=>parseInt(h.slice(i,i+2),16)/255); }
function _lum(c){ const f = v => v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); }
function inkOn(base, mid, pct){
  const a = _rgb(base), b = _rgb(mid), p = pct/100, bg = _lum(a.map((v,i)=>v*p + b[i]*(1-p)));
  const dark = (bg+0.05)/(_lum(_rgb('#0b0b0b'))+0.05), light = 1.05/(bg+0.05);
  return dark >= light ? '#0b0b0b' : '#ffffff';
}
// ---- end ink ----

// ---- since (mirrors since.py; tests/test_since.py checks they agree) ----
const SINCE_MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function makeSnapshot(data){
  const ranks = {}, priceOnly = [];
  for (const h of data.holdings||[]){ const c = h.current||{}; const r = c.rank!=null ? c.rank : c.would_rank;
    if (r!=null){ ranks[h.ticker] = Math.trunc(r); if (c.rank==null && h.in_universe!==false) priceOnly.push(h.ticker); } }
  const top = (data.rankings||[]).filter(r=>r.rank!=null).sort((a,b)=>a.rank-b.rank).slice(0, data.top_n||5).map(r=>r.ticker);
  const mt = (data.my_trades||{}).totals||{}, pst = (((data.paper||{}).stats||{}).paper)||{};
  return {asof:data.prices_asof, top, ranks, price_only: priceOnly.sort(), pnl: mt.pnl ?? null, paper: pst.total_return ?? null, alerts:(data.alert_log||[]).length};
}
function snapshotValid(s){ return !!s && typeof s==='object' && typeof s.asof==='string' && s.asof.length>=10 && Array.isArray(s.top) && !!s.ranks && typeof s.ranks==='object' && !Array.isArray(s.ranks); }
function diffSnapshots(prev, cur){
  if (!snapshotValid(prev)) return {first:true, items:[], moved:{}, text:"Welcome! Next time you open this, you'll see what changed since today."};
  const [y,m,d] = prev.asof.slice(0,10).split('-').map(Number), since = `${SINCE_MONTHS[m-1]} ${d}`;
  if (prev.asof === cur.asof) return {first:false, items:[], moved:{}, text:`Up to date: nothing new since ${since}.`};
  const items = [], moved = {}, num = v => typeof v==='number' && Number.isFinite(v);
  const entered = cur.top.filter(t=>!prev.top.includes(t)), left = prev.top.filter(t=>!cur.top.includes(t));
  if (entered.length) items.push(`${entered.join(', ')} entered the top ${cur.top.length}`);
  if (left.length) items.push(`${left.join(', ')} left the top ${cur.top.length}`);
  for (const [t,r] of Object.entries(cur.ranks)){
    const p = prev.ranks[t];
    if (num(p) && num(r) && p !== r){ moved[t] = Math.trunc(p); items.push(`${t} ${r<p?'rose':'fell'} #${Math.trunc(p)} → #${r}`); }
  }
  if (Array.isArray(prev.price_only) && Array.isArray(cur.price_only)){
    for (const t of Object.keys(cur.ranks)){
      const now = cur.price_only.includes(t), before = prev.price_only.includes(t);
      if (now && !before && t in prev.ranks) items.push(`${t} now ranked on price data only`);
      else if (before && !now) items.push(`${t} fully ranked again`);
    }
  }
  const gone = Object.keys(prev.ranks).filter(t=>!(t in cur.ranks));
  if (gone.length) items.push('no longer tracking ' + gone.join(', '));
  if (num(prev.pnl) && num(cur.pnl)){ const dd = cur.pnl-prev.pnl; if (Math.abs(dd) >= 1) items.push(`your P&L ${dd>=0?'+':'−'}$${Math.floor(Math.abs(dd)+0.5).toLocaleString('en-US')}`); }
  if (num(prev.paper) && num(cur.paper)){ const dd = (cur.paper-prev.paper)*100; if (Math.abs(dd) >= 0.05) items.push(`paper portfolio ${dd>=0?'+':'−'}${Math.abs(dd).toFixed(1)} pts`); }
  const n = (num(cur.alerts)?cur.alerts:0) - (num(prev.alerts)?prev.alerts:0);
  if (n > 0) items.push(`${n} new alert${n!==1?'s':''}`);
  return {first:false, items, moved, text: items.length ? `Since ${since}: ${items.join('; ')}.` : `Nothing new since ${since}.`};
}
// ---- end since ----

// ---- streaks ----  (mirrors week_diff.streak_of in Python; tests/test_week_diff.py runs both)
function streakOf(history, cur, ticker, topN){
  const inn = r => r!=null && r <= topN;
  if (!inn((cur||{})[ticker])) return 0;
  let n = 1;
  for (const snap of (history||[]).slice().reverse()){
    if (!inn(((snap||{}).ranks||{})[ticker])) break;
    n++;
  }
  return n;
}
// ---- end streaks ----

// ---- valpct (mirrors valuation.label/ordinal in Python; tests/test_valuation.py checks they agree) ----
function valLabel(p){
  if (p==null) return 'not enough history';
  if (p < 10) return 'near its cheapest';
  if (p < 25) return 'cheaper than usual';
  if (p <= 75) return 'about usual';
  if (p <= 90) return 'pricier than usual';
  return 'near its priciest';
}
function ordinal(p){
  const n = Math.round(p), m = n % 100, k = n % 10;
  return n + ((m>=10 && m<=20) ? 'th' : k===1 ? 'st' : k===2 ? 'nd' : k===3 ? 'rd' : 'th');
}
// ---- end valpct ----

// ---- ranksort (tests/test_hardening.py runs this block in node) ----
// sort keys; null = no value, which always sorts LAST whichever way you sort
const RANK_KEYS = {rank:r=>r.rank ?? (r.would_rank!=null ? r.would_rank+0.5 : null), score:r=>r.score==null?null:-r.score,
                   val:r=>r.valuation&&r.valuation.pct!=null ? r.valuation.pct : null};
function sortRankRows(rows, key, dir){
  const k = RANK_KEYS[key];
  return rows.slice().sort((a,b)=>{ const x = k(a), y = k(b);
    if (x==null || y==null) return (x==null) - (y==null);   // blanks last
    return (x - y) * dir; });
}
// ---- end ranksort ----

// ---- compare (mirrors explain.compare in Python; tests/test_compare.py checks they agree) ----
function explainChange(zPrev, zNow, weights){
  const w = Object.fromEntries(Object.entries(weights).filter(([f,v])=>v>0));
  const ok = v => v!=null && !Number.isNaN(v);
  const Wp = Object.keys(w).reduce((a,f)=>a+(ok(zPrev[f])?w[f]:0),0), Wn = Object.keys(w).reduce((a,f)=>a+(ok(zNow[f])?w[f]:0),0);
  const drivers = [];
  for (const f of Object.keys(w)){
    const p = ok(zPrev[f]) ? zPrev[f] : null, n = ok(zNow[f]) ? zNow[f] : null;
    if (p==null && n==null) continue;
    const before = p!=null && Wp ? w[f]*p/Wp : 0, after = n!=null && Wn ? w[f]*n/Wn : 0;
    drivers.push({factor:f, contrib:after-before, z_prev:p, z_now:n});
  }
  drivers.sort((a,b)=>Math.abs(b.contrib)-Math.abs(a.contrib));   // stable sort, like Python
  const sp = Wp ? Object.keys(w).reduce((a,f)=>a+(ok(zPrev[f])?w[f]*zPrev[f]:0),0)/Wp : null;
  const sn = Wn ? Object.keys(w).reduce((a,f)=>a+(ok(zNow[f])?w[f]*zNow[f]:0),0)/Wn : null;
  return {delta: sp!=null && sn!=null ? sn-sp : null, drivers};
}
function compareStocks(a, b, factors, n=3){
  const weights = Object.fromEntries(Object.entries(factors).map(([f,c])=>[f,c.weight]));
  const e = explainChange(b.z||{}, a.z||{}, weights);
  const gaps = e.drivers.map(d=>({factor:d.factor, gap:d.contrib, z_a:d.z_now, z_b:d.z_prev}));
  return {a:a.ticker, b:b.ticker, diff:e.delta, gaps, top:gaps.slice(0,n)};
}
function parseCompareHash(hash, known){
  const m = /(?:^|[#&])compare=([^&]*)/.exec(hash||'');
  if (!m) return [];
  const out = [];
  for (const t of decodeURIComponent(m[1]).split(',').map(x=>x.trim().toUpperCase()))
    if (t && known.includes(t) && !out.includes(t) && out.length < 3) out.push(t);
  return out;
}
// ---- end compare ----

// ---- slim (mirrors slim.py; tests/test_slim.py checks they agree) ----
function unpackPairs(x){
  if (Array.isArray(x)) return x.map(unpackPairs);
  if (!x || typeof x !== 'object') return x;
  if (Array.isArray(x._d)){
    const dates = x._d, same = !!x._same, out = {};
    for (const [k, arr] of Object.entries(x)) if (k !== '_d' && k !== '_same')
      out[k] = dates.map((d,i)=>[d, arr[i]]).filter(p=>same || p[1] != null);
    return out;
  }
  const out = {}; for (const [k,v] of Object.entries(x)) out[k] = unpackPairs(v); return out;
}
function mergeDetail(data, detail){
  const put = r => { if (r && detail[r.ticker]) for (const [k,v] of Object.entries(detail[r.ticker])) if (!(k in r)) r[k] = v; };
  (data.rankings||[]).concat(data.watchlist||[]).forEach(put);
  (data.holdings||[]).forEach(h=>put(h.current));
  return data;
}
// ---- end slim ----

// ---- underwater ----
// [[date, value], ...] -> [[date, value / running max − 1], ...]  (drawdowns.underwater in Python)
function underwaterPts(pts){
  let hi = -Infinity; const out = [];
  for (const [d, v] of (pts||[])){ if (v == null || !isFinite(v)) continue; if (v > hi) hi = v; out.push([d, hi > 0 ? v/hi - 1 : 0]); }
  return out;
}
// ---- end underwater ----

// ---- week diff ----  (mirrors week_diff.diff in Python; tests/test_week_diff.py runs both)
function rankMap(rows){
  const out = {};
  for (const r of rows||[]) if (r && r.rank!=null && !Number.isNaN(+r.rank)) out[r.ticker] = Math.trunc(+r.rank);
  return out;
}
function weekDiff(prev, cur, topN, n=3){
  if (!prev || !cur || !Object.keys(prev).length || !Object.keys(cur).length) return null;
  const inn = r => r!=null && r <= topN, cmp = (a,b) => a<b?-1:a>b?1:0;
  const entered = Object.keys(cur).filter(t=>inn(cur[t]) && !inn(prev[t])).sort((a,b)=>cur[a]-cur[b]);
  const left = Object.keys(prev).filter(t=>inn(prev[t]) && !inn(cur[t])).sort((a,b)=>prev[a]-prev[b]);
  const both = Object.keys(cur).filter(t=>t in prev && prev[t]!==cur[t]);
  const by = d => (a,b)=> d(a)-d(b) || cur[a]-cur[b] || cmp(a,b);
  const up = both.filter(t=>prev[t]>cur[t]).sort(by(t=>cur[t]-prev[t]));
  const down = both.filter(t=>prev[t]<cur[t]).sort(by(t=>prev[t]-cur[t]));
  const item = t => ({ticker:t, from:t in prev ? prev[t] : null, to:t in cur ? cur[t] : null});
  return {entered:entered.map(item), left:left.map(item), up:up.slice(0,n).map(item), down:down.slice(0,n).map(item),
          new:Object.keys(cur).filter(t=>!(t in prev)).sort(cmp)};
}
// ---- end week diff ----

// ---- lots (mirrors mytrades.long_term_date / preview_sell; tests/test_taxlots_js.py) ----
function longTermDate(bought){            // day after the same calendar date next year (Feb 29 -> Mar 1)
  const [y,m,d] = bought.split('-').map(Number);
  const nd = new Date(Date.UTC(y+1, m-1, d));
  if (nd.getUTCMonth() !== m-1) nd.setUTCDate(0);   // Feb 29 -> Feb 28 (same as pandas DateOffset)
  nd.setUTCDate(nd.getUTCDate()+1);
  return nd.toISOString().slice(0,10);
}
function previewSell(lots, ticker, shares, price, asof){
  const L = lots.filter(l=>l.ticker===ticker);
  const have = L.reduce((a,l)=>a+l.shares,0); let left = Math.min(shares, have), st = 0, lt = 0; const pieces = [];
  for (const l of L){
    if (left <= 1e-9) break;
    const take = Math.min(l.shares, left), gain = take*(price-l.price), term = asof >= longTermDate(l.date) ? 'LT' : 'ST';
    if (term==='LT') lt += gain; else st += gain;
    pieces.push({buy_date:l.date, shares:take, gain, term}); left -= take;
  }
  return {ticker, shares:Math.min(shares, have), capped: shares > have + 1e-9, st, lt, pieces};
}
// ---- end lots ----

// ---- tour ----
// First-visit tour. Each step: the tab to open (or null), CSS selectors to try in order (the
// first visible one is highlighted), and plain text. visibleSteps() is pure, so node tests it.
const TOUR_STEPS = [
  {tab:null, sel:['nav'], title:'Seven tabs, one question',
   text:'Does ranking chip stocks on their own filings actually pick winners? Each tab answers part of that. Start on the left and work right.'},
  {tab:'paper', sel:['#paper-card'], title:'The real test: the paper portfolio',
   text:'Every quarter the top picks are written down BEFORE their returns happen, then tracked against SPY and SOXX. This is the only part that proves anything, and it takes time.'},
  {tab:'rank', sel:['#walk-card', '#rank-table'], title:'Today\'s rankings, and why',
   text:'Every stock scored on growth, margins, inventory, cash flow, valuation and momentum. Tap "How did #1 get its score?" to see the exact arithmetic, or tap any row for details.'},
  {tab:'bt', sel:['#edge-card', '#out-card'], title:'The past: the backtest',
   text:'How the same rules would have done since 2012. "Is the edge real?" checks it isn\'t luck; "What could $1,000 become?" shows the range instead of one number. The past is a hint, not a promise.'},
  {tab:null, sel:['#weekly-link', 'nav button[data-tab="learn"]'], title:'Learn as you go',
   text:'Every term on the dashboard is explained in the Learn tab. Once a week, open the weekly review: 3 questions about what changed. Write your answers in your journal.'},
];
function visibleSteps(steps, isVisible){
  const out = [];
  for (const s of steps || []){
    const target = (s.sel || []).find(sel => { try { return !!isVisible(sel); } catch(e){ return false; } });
    if (target) out.push({...s, target});
  }
  return out;
}
// ---- end tour ----

// ---- jump chips ----
// [{id, title, hidden}] -> [{id, title}] for the visible cards, in page order; [] if fewer than JUMP_MIN
const JUMP_MIN = 4;
function chipItems(cards){
  const out = (cards||[]).filter(c=>c && !c.hidden && c.id && String(c.title||'').trim())
                         .map(c=>({id:String(c.id), title:String(c.title).trim()}));
  return out.length >= JUMP_MIN ? out : [];
}
// ---- end jump chips ----
