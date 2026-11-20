// Igor — suivi en direct des installations de l'équipe (portail Flatpay, LECTURE SEULE).
// Le lanceur définit avant ce code : window.IGOR = {sales:'90104,90107,…', budget:40000}
// Chaque appel avance pendant ~40 s puis répond « SUITE … » ; relancer le même code jusqu'à « FINI n » :
// la page affiche alors un bloc <pre id="igor"> à lire avec get_page_text.
// Étapes : 1) liste « En attente d'installations » filtrée sur les sales ; 2) fiche de chaque installation
// (SIREN, terminaux ; mémorisés d'un jour à l'autre) ; 3) pour chaque SIREN : recherche Client → ouverture du
// client → Transactions du jour (somme des ventes terminées, remboursements déduits).
// Ne clique jamais sur Enregistrer, Créer, un interrupteur ou un champ : seulement des lignes de tableau et « Suivant ».
// Sortie : I|sales|nom|siren|volume|creation|livraison|statut|recettes|nb_tx_jour|montant_jour|controle|note|dernier
// dernier = date (JJ/MM/AAAA) de la dernière vente terminée : aujourd'hui s'il y en a une, sinon on relit les
// transactions depuis la création de l'installation jusqu'à hier (liste triée de la plus récente à la plus ancienne).
(async () => {
const CFG = Object.assign({ sales: '', budget: 40000 }, window.IGOR || {});
const T0 = Date.now();
const sleep = t => new Promise(r => setTimeout(r, t));
const waitFor = async (f, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = f(); if (v) return v; await sleep(150); } return null; };
const txt = () => document.body.innerText;
const clean = s => String(s ?? '').replace(/[|\n\r]/g, ' ').replace(/\s+/g, ' ').trim();
const num = s => { const v = parseFloat(String(s || '').replace(/[^\d,.-]/g, '').replace(/\s/g, '').replace(',', '.')); return isNaN(v) ? 0 : v; };
const go = async (path) => { history.pushState({}, '', path); dispatchEvent(new PopStateEvent('popstate', { state: {} })); await sleep(400); };
const now = new Date(), J = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
const FROM = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0).toISOString().replace(/:\d\d\.\d+Z$/, ':00.000Z');
const TO = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59).toISOString().replace(/\.\d+Z$/, '.000Z');
const KEY = 'igor_v1', KS = 'igor_fiches_v1';
let st = {}; try { st = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (_) {}
let fiches = {}; try { fiches = JSON.parse(localStorage.getItem(KS) || '{}'); } catch (_) {}
if (st.jour !== J || st.sales !== CFG.sales || (st.t && Date.now() - st.t > 3 * 3600e3)) st = { jour: J, sales: CFG.sales, t: Date.now(), liste: null, tx: {} };
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); localStorage.setItem(KS, JSON.stringify(fiches)); } catch (_) {} };
const cle = r => r.nom + '|' + r.creation;
const rows = () => [...document.querySelectorAll('tbody tr')].filter(r => r.children.length >= 8);
const listeUrl = '/awaiting-installations?salesPersons=' + encodeURIComponent(CFG.sales);
const allerListe = async (page) => {   // la liste ne se recharge pas si on y est déjà : on passe par une autre page
  if (/^\/awaiting-installations/.test(location.pathname)) { await go('/customer'); await sleep(800); }
  await go(listeUrl + '&page=' + page);
  await waitFor(() => new RegExp('Afficher ' + ((page - 1) * 20 + 1) + ' ').test(txt()) && rows().length, 20000); await sleep(300);
};
const listeReady = async () => { await waitFor(() => /Afficher \d|Aucun/.test(txt()) && (rows().length || /Aucun/.test(txt())), 20000); await sleep(300); };
const pageSuivante = async () => {
  const nx = [...document.querySelectorAll('button,a')].find(b => /^Suivant/.test(b.innerText.trim()) && !b.disabled && b.getAttribute('aria-disabled') !== 'true');
  if (!nx || !rows().length) return false;
  const first = rows()[0].innerText; nx.click();
  return !!(await waitFor(() => rows()[0] && rows()[0].innerText !== first, 10000));
};
const lireLigne = r => { const c = [...r.children].map(x => clean(x.innerText)); // colonne 5 = icône
  return { nom: c[0], sales: c[1], volume: num(c[2]), creation: c[3], livraison: c[4], statut: clean(c[6]).replace(/Click row/i, '').trim(), recettes: c[7] === '-' ? 0 : num(c[7]), encours: c[8] }; };

// ---- 1. Liste
if (!st.liste) {
  if (!CFG.sales) return 'ERREUR window.IGOR.sales manquant';
  await allerListe(1);
  if (!/EN ATTENTE D.INSTALLATIONS/i.test(txt())) return 'ERREUR page des installations introuvable (portail déconnecté ?)';
  const all = []; let p = 0;
  do { p++; rows().forEach(r => all.push({ ...lireLigne(r), page: p })); } while (p < 20 && await pageSuivante());
  st.liste = all; st.pages = p; save();
}

// ---- 2. Fiches (SIREN + terminaux), mémorisées
const echecs = st.echecs || (st.echecs = {});
const manquantes = () => st.liste.filter(r => !fiches[cle(r)] && !echecs[cle(r)]);
if (manquantes().length) {
  for (const r of manquantes()) {
    if (Date.now() - T0 > CFG.budget) break;
    await allerListe(r.page);
    let el = rows().find(x => cle(lireLigne(x)) === cle(r));
    for (let k = 0; k < 5 && !el && await pageSuivante(); k++) el = rows().find(x => cle(lireLigne(x)) === cle(r));
    for (let pg = 1; pg <= st.pages && !el; pg++) { if (pg === r.page) continue; await allerListe(pg); el = rows().find(x => cle(lireLigne(x)) === cle(r)); }
    if (!el) { echecs[cle(r)] = 'ligne introuvable dans la liste'; save(); continue; }
    el.click();
    const ok = await waitFor(() => /SIREN:/.test(txt()), 12000);
    if (ok) {
      const t = txt();
      const siren = ((t.match(/SIREN:\s*([0-9 ]{9,11})/) || [])[1] || '').replace(/\s/g, '');
      const bloc = (t.split('Terminaux attribués:')[1] || '').split(/Identifiants des équipements:|INSTALLATION DE LA CONFIGURATION/)[0];
      const tids = (bloc.match(/\b\d{8,20}\b/g) || []);
      const eq = ((t.split('Identifiants des équipements:')[1] || '').split('INSTALLATION DE LA CONFIGURATION')[0] || '').trim().split(/\s+/).filter(Boolean);
      if (siren) fiches[cle(r)] = { siren, tids, equip: eq }; else echecs[cle(r)] = 'SIREN absent de la fiche';
    } else echecs[cle(r)] = 'fiche illisible';
    save();
  }
  if (manquantes().length) return `SUITE fiches : ${manquantes().length} restante(s) sur ${st.liste.length}`;
}

// date de la dernière vente terminée avant aujourd'hui (client déjà ouvert) ; '' si aucune, '?' si illisible
const dernierEncaissement = async (r) => {
  const m = (r.creation || '').match(/(\d\d)\/(\d\d)\/(\d{4})/);
  const debut = m ? new Date(+m[3], +m[2] - 1, +m[1], 0, 0, 0) : new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
  const fin = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 23, 59, 59);
  if (debut > fin) return '';
  const iso = d => d.toISOString().replace(/\.\d+Z$/, '.000Z');
  await go('/customer'); await sleep(600);   // pour forcer le rechargement de la page des transactions
  await go(`/transactions?fromDate=${encodeURIComponent(iso(debut))}&toDate=${encodeURIComponent(iso(fin))}`);
  const pret = await waitFor(() => /fromDate/.test(location.search) && /Total collect/.test(txt()) && (/Aucune donnée/.test(txt()) || document.querySelector('tbody tr')), 15000);
  if (!pret) return '?';
  await sleep(1500);
  if (/Aucune donnée/.test(txt()) && !document.querySelector('tbody tr')) return '';
  let cur = '';
  for (const tr of document.querySelectorAll('tbody tr')) {
    const t = clean(tr.innerText);
    if (/^\d\d\/\d\d\/\d{4}$/.test(t)) { cur = t; continue; }
    const c = [...tr.children].map(x => clean(x.innerText)); if (c.length < 5) continue;
    const statut = c.find(x => /Terminé|Refusé|Annulé|En attente/i.test(x)) || '';
    if (/Terminé/i.test(statut) && !/Rembours/i.test(c[1] || '') && num(c[c.length - 1]) > 0) return cur || '?';
  }
  return '';
};

// ---- 3. Transactions du jour, client par client
const aFaire = () => st.liste.filter(r => { const f = fiches[cle(r)]; return f && f.siren && !st.tx[f.siren]; });
for (const r of aFaire()) {
  if (Date.now() - T0 > CFG.budget) break;
  const f = fiches[cle(r)];
  await go('/customer?q=' + f.siren);
  await waitFor(() => [...document.querySelectorAll('tbody tr')].some(x => x.innerText.includes(f.siren)) || /Aucun|aucun/.test(txt()), 12000); await sleep(300);
  const cands = [...document.querySelectorAll('tbody tr')].filter(x => x.innerText.includes(f.siren));
  const choix = cands.find(x => f.tids.some(t => x.innerText.includes(t))) || cands[0];
  if (!choix) { st.tx[f.siren] = { n: 0, total: 0, ok: false, note: 'client introuvable' }; save(); continue; }
  const nomClient = clean((choix.children[2] || {}).innerText).toUpperCase();
  choix.click();
  await waitFor(() => !/^\/customer/.test(location.pathname), 12000);
  await waitFor(() => !nomClient || txt().slice(0, 300).toUpperCase().includes(nomClient), 8000); await sleep(800);
  await go(`/transactions?fromDate=${encodeURIComponent(FROM)}&toDate=${encodeURIComponent(TO)}`);
  await waitFor(() => /Total collect/.test(txt()) && (/Aucune donnée/.test(txt()) || document.querySelector('tbody tr')), 15000); await sleep(1500);
  const tidsPage = decodeURIComponent((location.search.match(/tids=([^&]*)/) || [])[1] || '').split(',');
  const memes = !f.tids.length || f.tids.some(t => tidsPage.includes(t));
  const perime = tidsPage.join(',') !== '' && tidsPage.join(',') === st.dernierTids;   // page restée sur le client précédent
  const controle = memes || !perime;
  st.dernierTids = tidsPage.join(',');
  const t = txt();
  const nTete = parseInt((t.match(/(\d+)\s*\n\s*Transactions/) || [])[1] || '0', 10);
  const totalTete = num((t.match(/([\d\s  ,.]+)EUR\s*\n\s*Total collect/) || [])[1]);
  let n = 0, somme = 0, lignes = 0;
  for (const tr of document.querySelectorAll('tbody tr')) {
    const c = [...tr.children].map(x => clean(x.innerText)); if (c.length < 5) continue;
    lignes++;
    const typ = c[1] || '', statut = c.find(x => /Terminé|Refusé|Annulé|En attente/i.test(x)) || '', m = num(c[c.length - 1]);
    if (!/Terminé/i.test(statut)) continue;
    if (/Rembours/i.test(typ)) somme -= m; else { somme += m; n++; }
  }
  const complet = lignes >= nTete;
  const nJour = complet ? n : nTete;
  let dernier = nJour > 0 ? J.split('-').reverse().join('/') : '';
  if (!dernier && controle) dernier = await dernierEncaissement(r);
  st.tx[f.siren] = { n: nJour, total: Math.round((complet ? somme : totalTete) * 100) / 100, ok: controle, dernier, note: !controle ? 'la page est restée sur le client précédent' : [memes ? '' : 'terminaux différents de la fiche', complet ? '' : 'total du portail (liste incomplète)'].filter(Boolean).join(' ; ') };
  save();
}
// une seconde chance pour les clients en échec (contrôle des terminaux ou client introuvable)
if (!aFaire().length && !st.reessai) {
  st.reessai = true;
  for (const [s, x] of Object.entries(st.tx)) if (x.ok === false) delete st.tx[s];
  save();
}
if (aFaire().length) return `SUITE transactions : ${aFaire().length} client(s) restant(s) sur ${st.liste.length}`;

// ---- Sortie
const out = st.liste.map(r => { const f = fiches[cle(r)] || { note: echecs[cle(r)] }; const x = st.tx[f.siren] || {};
  return ['I', r.sales, r.nom, f.siren || '', r.volume, r.creation, r.livraison, r.statut, r.recettes, x.n ?? '', x.total ?? '', x.ok === false ? 'KO' : 'OK', clean([f.note, x.note].filter(Boolean).join(' ; ')), x.dernier ?? ''].map(clean).join('|'); });
let pre = document.getElementById('igor'); if (!pre) { pre = document.createElement('pre'); pre.id = 'igor'; }
document.body.innerHTML = ''; document.body.appendChild(pre);
pre.textContent = ['META|jour|' + J, 'META|heure|' + now.toTimeString().slice(0, 5), ...out].join('\n');
localStorage.removeItem(KEY);
return `FINI ${out.length} installations`;
})();
