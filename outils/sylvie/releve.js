// Sylvie — lecture de la boîte Outlook (outlook.cloud.microsoft) en LECTURE SEULE.
// Ne clique jamais sur un mail (ça le marquerait comme lu) : on lit seulement la liste des résultats de recherche.
// Le lanceur exécute ce code une fois dans l'onglet Outlook ; il définit window.SYLVIE :
//   SYLVIE.focus()      → met le curseur dans la recherche et sélectionne son texte. Doit répondre FOCUS_OK avant de taper.
//   SYLVIE.collect(tag) → après une recherche, parcourt la liste des résultats et les garde sous l'étiquette tag. Répond « n=… ».
//   SYLVIE.dump()       → écrit tous les résultats gardés dans un bloc <article> discret, à lire avec get_page_text.
// Format d'une ligne : M|tag|id|email expéditeur|nom expéditeur|date (JJ/MM/AAAA HH:MM)|sujet|dossier|drapeaux|aperçu
(() => {
const sleep = t => new Promise(r => setTimeout(r, t));
const clean = s => String(s || '').replace(/[|\n\r]/g, ' ').replace(/\s+/g, ' ').trim();
const store = (window.SYLVIE && window.SYLVIE.store) || new Map();
const lire = o => {
  const leaves = [...o.querySelectorAll('span,div')].filter(e => e.children.length === 0 && e.textContent.trim());
  const iDate = leaves.findIndex(e => /\d{2}\/\d{2}\/\d{4} \d{1,2}:\d{2}/.test(e.getAttribute('title') || ''));
  const iFrom = leaves.findIndex(e => /@/.test(e.getAttribute('title') || ''));
  const from = iFrom >= 0 ? leaves[iFrom] : null;
  const date = iDate >= 0 ? (leaves[iDate].getAttribute('title').match(/\d{2}\/\d{2}\/\d{4} \d{1,2}:\d{2}/) || [''])[0] : '';
  const sujet = iDate > 0 ? leaves.slice(Math.max(iFrom, 0) + 1, iDate).map(e => e.textContent.trim()).filter(t => !/^\d+$/.test(t)).join(' ') : '';
  const tagEl = leaves.find(e => /InteractionTag/i.test(e.className));
  const apercu = iDate >= 0 ? leaves.slice(iDate + 1).filter(e => e !== tagEl).map(e => e.textContent.trim()).join(' ') : '';
  const al = o.getAttribute('aria-label') || '';
  const flags = ['Non lu', 'A répondu', 'Transféré', 'Expéditeur externe', 'Réunion acceptée', 'Réunion refusée', 'Réunion annulée', 'Réunion', 'Important', 'Avec indicateur', 'Comporte des pièces jointes', '[Brouillon]']
    .filter(f => al.includes(f)).join(',');
  return [o.id || o.getAttribute('data-convid'), from ? from.getAttribute('title') : '', from ? from.textContent.trim() : '', date, sujet, tagEl ? tagEl.textContent.trim() : '', flags, apercu.slice(0, 400)].map(clean);
};
window.SYLVIE = {
  store,
  focus() {
    document.getElementById('sylvie-out')?.remove();
    const i = [...document.querySelectorAll('input[role=combobox],input[type=search]')].find(x => x.offsetParent && /Recherch|Search/i.test((x.getAttribute('aria-label') || '') + (x.placeholder || '')));
    if (!i) return 'PAS_DE_RECHERCHE';
    i.focus(); i.select();
    return document.activeElement === i ? 'FOCUS_OK' : 'FOCUS_KO';
  },
  async collect(tag) {
    const opts = () => [...document.querySelectorAll('[role=option][data-convid]')];
    await sleep(800);
    let n = 0; const vus = new Set();
    let sc = opts()[0];
    while (sc && !(sc.scrollHeight > sc.clientHeight + 5 && /auto|scroll/.test(getComputedStyle(sc).overflowY))) sc = sc.parentElement;
    if (sc) { sc.scrollTop = 0; await sleep(700); }
    const prendre = () => { for (const o of opts()) { const f = lire(o); const k = tag + '|' + f[0] + '|' + f[3] + '|' + f[4]; if (!vus.has(k)) { vus.add(k); store.set(k, ['M', tag, ...f].join('|')); n++; } } };
    for (let i = 0; i < 100; i++) {
      prendre(); if (!sc) break;
      const b = sc.scrollTop; sc.scrollTop += 400; await sleep(450);
      if (sc.scrollTop === b) { await sleep(900); prendre(); break; }
    }
    if (sc) sc.scrollTop = 0;
    return 'n=' + n;
  },
  dump() {
    let a = document.getElementById('sylvie-out');
    if (!a) { a = document.createElement('article'); a.id = 'sylvie-out'; a.style.cssText = 'position:fixed;left:0;bottom:0;width:2px;height:2px;overflow:hidden;pointer-events:none;opacity:0.01;z-index:-1'; document.body.appendChild(a); }
    a.textContent = '';
    const p = document.createElement('pre'); p.textContent = [...store.values()].join('\n') || 'AUCUN'; a.appendChild(p);
    return 'FINI ' + store.size + ' lignes';
  },
};
return 'PRET';
})();
