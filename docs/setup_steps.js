// Setup progress detection, shared by index.html and setup.html.
// Python mirror: check_setup.steps_done (tests/test_setup.py checks they agree).
const SETUP_STEPS = [
  {id:'upload',  title:'Create the repo and upload the files'},
  {id:'pages',   title:'Turn on GitHub Pages'},
  {id:'secret',  title:'Add the SEC_USER_AGENT secret'},
  {id:'perms',   title:'Let the Action save its results'},
  {id:'firstrun',title:'Run the first update'},
  {id:'healthy', title:'Latest update succeeded'},
  {id:'alerts',  title:'Turn on phone alerts'},
  {id:'trades',  title:'Log your first real trade'},
];
// data: data.json (or null), runlog: run_log.json array (or null),
// ctx: {hosted: page served from *.github.io, manual: {alerts: true/false}}
function stepsDone(data, runlog, ctx){
  ctx = ctx || {};
  const live = !!data && data.mode === 'live';
  const log = Array.isArray(runlog) ? runlog : [];
  const failed = live && data.data_health && data.data_health.rows
    ? data.data_health.rows.filter(r => (r.flags||[]).some(f => /SEC download failed|SEC ticker list/.test(f))).length : 0;
  const hosted = !!ctx.hosted || live;           // live data can only come from a deployed run
  return {
    upload:   hosted,
    pages:    hosted,
    secret:   live && failed === 0,
    perms:    log.length >= 2,                    // the log only grows across runs if commits work
    firstrun: live,
    healthy:  log.length > 0 && log[log.length-1].status === 'ok',
    alerts:   !!(ctx.manual && ctx.manual.alerts),
    trades:   live && !!data.my_trades && !data.my_trades.demo && (data.my_trades.n_trades||0) > 0,
  };
}
function stepsCount(done){ return Object.values(done).filter(Boolean).length; }
if (typeof module !== 'undefined') module.exports = {SETUP_STEPS, stepsDone, stepsCount};
