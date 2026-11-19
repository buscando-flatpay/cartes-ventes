// Jones — relevé d'une équipe sur le portail Flatpay (à exécuter dans l'onglet de la liste des ventes).
// Le lanceur définit avant ce code : window.JONES = {rdvFrom:'AAAA-MM-JJ', budget:40000}
// Reprise automatique : chaque appel traite ce qu'il peut en ~40 s puis répond « SUITE n » ;
// relancer le même code jusqu'à « FINI n » : la page affiche alors les lignes à lire avec get_page_text.
// Ne lit que ce qui est affiché à l'écran (liste + fiche rendez-vous) : aucune API, aucun identifiant.
(async () => {
const CFG = Object.assign({ rdvFrom: '9999-12-31', budget: 40000 }, window.JONES || {});
const T0 = Date.now();
const sleep = t => new Promise(r => setTimeout(r, t));
const waitFor = async (f, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = f(); if (v) return v; await sleep(150); } return null; };
const KEY = 'jones_cache_v1';
let cache = {}; try { cache = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (_) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(cache)); } catch (_) {} };
const isDone = st => !!st && !/^annul|reprogramm|résultat requis|^à reprog/i.test(st);
const txt = () => document.body.innerText;
const iso = d => { const m = d.match(/(\d\d)\/(\d\d)\/(\d{4})/); return m ? `${m[3]}-${m[2]}-${m[1]}` : ''; };
const rows = () => [...document.querySelectorAll('table tbody tr')];
const cellsOf = r => [...r.querySelectorAll('td')].map(td => td.innerText.replace(/\s+/g, ' ').trim());
const keyOf = c => [c[6], c[1], c[0], c[5]].join('|');
const pageInfo = () => (txt().match(/(\d+) de (\d+)/) || [0, 1, 1]).slice(1).map(Number);
const btn = l => [...document.querySelectorAll('button')].find(b => b.innerText.trim() === l);
const ready = async () => { await waitFor(() => /Afficher \d|Aucun/.test(txt()) && (rows().length || /Aucun/.test(txt())), 20000); await sleep(250); };
const gotoPage = async p => {
  let [cur] = pageInfo(); let guard = 0;
  while (cur !== p && guard++ < 40) {
    const b = btn(cur < p ? 'Suivant' : 'Précédent'); if (!b || b.disabled) break;
    const first = rows()[0] ? rows()[0].innerText : ''; b.click();
    await waitFor(() => rows()[0] && rows()[0].innerText !== first, 10000); await sleep(200);
    [cur] = pageInfo();
  }
};

await ready();
// 1. Toutes les lignes, toutes pages (lecture seule)
await gotoPage(1);
const all = [];
for (let guard = 0; guard < 40; guard++) {
  const [p] = pageInfo();
  rows().forEach(r => { const c = cellsOf(r); if (c.length >= 8) all.push({ c, p }); });
  const nx = btn('Suivant'); if (!nx || nx.disabled) break;
  const first = rows()[0].innerText; nx.click();
  await waitFor(() => rows()[0] && rows()[0].innerText !== first, 10000); await sleep(200);
}
// 2. Fiches à ouvrir : ventes, et RDV réalisés depuis rdvFrom, absents du cache
const need = all.filter(x => {
  const st = x.c[7], d = iso(x.c[5]);
  return !cache[keyOf(x.c)] && (st === 'Vente' || (isDone(st) && d >= CFG.rdvFrom));
});
let opened = 0;
for (const x of need) {
  if (Date.now() - T0 > CFG.budget) break;
  await gotoPage(x.p);
  const r = rows().find(r => keyOf(cellsOf(r)) === keyOf(x.c));
  if (!r) continue;
  r.click();
  const ok = await waitFor(() => /Adresse:/.test(txt()), 12000);
  await sleep(250);
  const t = txt();
  const adr = ok ? ((t.match(/Adresse:\s*([^\n]*)/) || [])[1] || '').trim() : '';
  const prod = ((t.match(/\nProduit\s*\n+\s*([^\n]+)/) || [])[1] || '').trim();
  cache[keyOf(x.c)] = { a: adr, pr: prod, t: Date.now() };
  opened++; save();
  history.back(); await ready();
}
const left = need.filter(x => !cache[keyOf(x.c)]).length;
if (left) return `SUITE ${left} fiche(s) restante(s) · ${opened} ouverte(s) cet appel · ${all.length} lignes`;

// 3. Coordonnées (ventes seulement) et code NAF (si SIREN valide), mis en cache
const geo = async a => {
  try {
    const m = a.match(/(\d{5})\s+(.+)$/); const cp = m ? m[1] : '';
    const j = await fetch('https://api-adresse.data.gouv.fr/search/?limit=1&q=' + encodeURIComponent(a) + (cp ? '&postcode=' + cp : '')).then(r => r.json());
    const f = j.features && j.features[0];
    if (!f) return {};
    return { lat: f.geometry.coordinates[1].toFixed(5), lon: f.geometry.coordinates[0].toFixed(5), sc: f.properties.score.toFixed(2) };
  } catch (_) { return {}; }
};
const naf = async s => {
  for (let i = 0; i < 4; i++) {
    try {
      const r = await fetch('https://recherche-entreprises.api.gouv.fr/search?q=' + s + '&per_page=3');
      if (r.status === 429) { await sleep(1500); continue; }
      const j = await r.json(); const e = (j.results || []).find(z => z.siren === s);
      return e ? (e.activite_principale || (e.siege || {}).activite_principale || '') : '';
    } catch (_) { await sleep(800); }
  }
  return '';
};
for (const x of all.filter(x => x.c[7] === 'Vente')) {
  const k = cache[keyOf(x.c)]; if (!k) continue;
  if (k.a && !k.geo) { const g = await geo(k.a); k.lat = g.lat || ''; k.lon = g.lon || ''; k.sc = g.sc || ''; k.geo = 1; }
  const s = x.c[2].replace(/\s/g, '');
  if (/^\d{9}$/.test(s) && k.naf === undefined) { k.naf = await naf(s); await sleep(180); }
}
save();
// 4. Sortie : une ligne par rendez-vous de la liste
const clean = v => String(v || '').replace(/[|\n]/g, ' ').trim();
const out = all.filter(x => x.c[7] === 'Vente' || iso(x.c[5]) >= CFG.rdvFrom).map(x => {
  const k = cache[keyOf(x.c)] || {};
  return [x.c[6], x.c[1], x.c[0], x.c[2].replace(/\s/g, ''), x.c[3], x.c[4], x.c[5], x.c[7], k.a, k.pr, k.lat, k.lon, k.sc, k.naf].map(clean).join('|');
});
document.body.innerHTML = '<pre id="jones">' + (out.join('\n') || 'AUCUNE') + '</pre>';
return `FINI ${out.length} lignes utiles sur ${all.length} · ${opened} fiche(s) ouverte(s) cet appel`;
})()
