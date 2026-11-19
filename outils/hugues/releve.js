// Hugues — lecture du rapport Power BI « Field Sales Report - TM - FR » (lecture seule).
// Le lanceur définit avant ce code : window.HUGUES = {mode:'dash'} sur la page TM Dash,
// ou {mode:'og'} sur la page « Sales Performance ». La page affiche ensuite un bloc à lire avec get_page_text :
//   META|periode|<filtre Period>          (ex. 2026 (year) + 11 (month_number))
//   META|maj|<Données mises à jour le JJ/MM/AA>
//   META|equipe|<filtre Team>
//   L|<ligne>|<col1>=<v>|<col2>=<v>…        une ligne par ligne du tableau (France, Sud Est, TM, commerciaux, Total)
(async () => {
const CFG = Object.assign({ mode: 'dash' }, window.HUGUES || {});
const KEEP = { dash: ['Installations', 'Sales (Signed)', 'POS Sales', 'POS Installations'], og: ['Sales OG'] }[CFG.mode] || null;
const keep = k => !KEEP || KEEP.some(p => k === p || (p === 'Sales OG' && k.startsWith(p)));
const sleep = t => new Promise(r => setTimeout(r, t));
const waitFor = async (f, ms = 20000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = f(); if (v) return v; await sleep(250); } return null; };
const clean = s => String(s || '').replace(/Mise en forme conditionnelle supplémentaire/g, '').replace(/[|\n]/g, ' ').replace(/\s+/g, ' ').trim();
const norm = s => clean(s).replace(/[^\p{L}\p{N}%()# ]/gu, '').replace(/\s+/g, ' ').trim();
const grid = () => [...document.querySelectorAll('[role=grid],[role=treegrid]')].filter(g => g.querySelectorAll('[role=columnheader]').length > 5)
  .sort((a, b) => b.querySelectorAll('[role=row]').length - a.querySelectorAll('[role=row]').length)[0];
const g0 = await waitFor(() => { const g = grid(); return g && g.querySelectorAll('[role=row]').length > 3 ? g : null; });
if (!g0) return 'ERREUR tableau introuvable (rapport pas chargé, ou session Power BI expirée)';
await sleep(1500);
const slicers = {};
document.querySelectorAll('.visualContainer').forEach(v => { const t = v.querySelector('.slicer-header-text'); const r = v.querySelector('.slicer-restatement'); if (t) slicers[t.innerText.trim()] = r ? r.innerText.trim() : ''; });
const maj = (document.body.innerText.match(/Données mises à jour le [0-9\/]+/) || [''])[0];
const data = {};   // ligne -> {colonne: valeur}
const order = [];
const capture = () => {
  const g = grid(); if (!g) return;
  const heads = {};
  g.querySelectorAll('[role=columnheader]').forEach(h => { const i = h.getAttribute('aria-colindex'); if (i) heads[i] = norm(h.innerText); });
  g.querySelectorAll('[role=row]').forEach(r => {
    const cells = [...r.querySelectorAll('[role=rowheader],[role=gridcell]')];
    if (!cells.length) return;
    const nameCell = r.querySelector('[role=rowheader]') || cells[0];
    const name = clean(nameCell.innerText); if (!name) return;
    if (!data[name]) { data[name] = {}; order.push(name); }
    cells.forEach(c => { const i = c.getAttribute('aria-colindex'); if (i && heads[i] && c !== nameCell) data[name][heads[i]] = clean(c.innerText); });
  });
};
capture();
// défilement horizontal : Power BI ne rend que les colonnes visibles
const vp = () => { const g = grid(); return (g.closest('.visualContainer') || g).querySelector('.scrollable-cells-viewport') || g; };
for (let pass = 0; pass < 6; pass++) {
  const el = vp(), r = el.getBoundingClientRect();
  for (let i = 0; i < 8; i++) { el.dispatchEvent(new WheelEvent('wheel', { deltaX: 200, deltaY: 0, bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 })); await sleep(100); }
  await sleep(700); capture();
}
const out = [`META|periode|${clean(slicers['Period'])}`, `META|maj|${clean(maj)}`, `META|equipe|${clean(slicers['Team'])}`, `META|mode|${CFG.mode}`];
order.forEach(n => out.push(['L', n, ...Object.entries(data[n]).filter(([k]) => keep(k)).map(([k, v]) => `${k.startsWith('Sales OG') ? 'Sales OG' : k}=${v}`)].join('|')));
document.body.innerHTML = '<pre id="hugues">' + out.join('\n') + '</pre>';
return `FINI ${order.length} lignes`;
})()
