// Sylvain — relevé des RDV affichés dans la liste du portail (lecture seule, aucune fiche ouverte).
// À exécuter dans l'onglet https://portal.flatpay.fr/sales?meetingDate=...&teamId=...
// La page affiche ensuite les lignes à lire avec get_page_text :
//   équipe | field sales | commerce | SIREN | type RDV | source | date RDV | statut
(async () => {
const sleep = t => new Promise(r => setTimeout(r, t));
const waitFor = async (f, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = f(); if (v) return v; await sleep(150); } return null; };
const txt = () => document.body.innerText;
const rows = () => [...document.querySelectorAll('table tbody tr')];
const cellsOf = r => [...r.querySelectorAll('td')].map(td => td.innerText.replace(/\s+/g, ' ').trim());
const btn = l => [...document.querySelectorAll('button')].find(b => b.innerText.trim() === l);
await waitFor(() => /Afficher \d|Aucun/.test(txt()) && (rows().length || /Aucun/.test(txt())), 20000);
await sleep(300);
const out = [];
for (let guard = 0; guard < 40; guard++) {
  rows().forEach(r => { const c = cellsOf(r); if (c.length >= 8) out.push([c[6], c[1], c[0], c[2].replace(/\s/g, ''), c[3], c[4], c[5], c[7]].map(v => String(v || '').replace(/[|\n]/g, ' ').trim()).join('|')); });
  const nx = btn('Suivant'); if (!nx || nx.disabled) break;
  const first = rows()[0].innerText; nx.click();
  await waitFor(() => rows()[0] && rows()[0].innerText !== first, 10000); await sleep(250);
}
document.body.innerHTML = '<pre id="sylvain">' + (out.join('\n') || 'AUCUNE') + '</pre>';
return `FINI ${out.length} RDV`;
})()
