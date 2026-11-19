// Hugues — règle les segments du rapport Power BI avant la lecture (page TM Dash ou Sales Performance).
// Le lanceur définit avant ce code : window.SEGMENTS = {equipe:'Quentin Dicharry', annee:2026, mois:11}
// Règle Team puis Period seulement s'ils ne sont pas déjà bons, puis écrit un bloc à lire avec get_page_text :
//   SEG|team|<valeur affichée>    SEG|period|<valeur affichée>    SEG|ok   (ou SEG|ERREUR|…)
// NE JAMAIS utiliser « Rétablir les valeurs par défaut » : cela remet la vue de l'auteur (Team = Tout, mois figé).
(async () => {
const C = window.SEGMENTS || {};
const sleep = t => new Promise(r => setTimeout(r, t));
const out = [];
const show = () => { let p = document.getElementById('hugues-seg'); if (!p) { p = document.createElement('pre'); p.id = 'hugues-seg'; document.body.appendChild(p); } p.textContent = out.join('\n'); return out.join('\n'); };
const slicer = nom => [...document.querySelectorAll('.visualContainer')].find(v => (v.querySelector('.slicer-header-text') || {}).innerText?.trim() === nom);
const etat = nom => ((slicer(nom) || document).querySelector('.slicer-restatement') || {}).innerText?.trim() || '';
const visibles = () => [...document.querySelectorAll('[role=treeitem]')].filter(e => e.offsetParent);
const menu = nom => (slicer(nom) || document).querySelector('.slicer-dropdown-menu');
const basculer = b => { for (const t of ['mousedown', 'mouseup', 'click']) b.dispatchEvent(new MouseEvent(t, { bubbles: true })); };
const ouvert = nom => (menu(nom) || {}).getAttribute?.('aria-expanded') === 'true';
const fermer = async nom => { await sleep(300); if (ouvert(nom)) basculer(menu(nom)); await sleep(800); };
const ouvrir = async nom => {
  for (const n of ['Team', 'Period']) if (n !== nom) await fermer(n);
  const b = menu(nom); if (!b) return false;
  if (!ouvert(nom)) basculer(b);
  for (let i = 0; i < 20 && !visibles().length; i++) await sleep(200);
  await sleep(500);
  return ouvert(nom) && visibles().length > 0;
};
try {
  if (!slicer('Team') || !slicer('Period')) { out.push('SEG|ERREUR|segments Team/Period introuvables sur cette page'); return show(); }
  // ---- Team
  if (C.equipe && etat('Team') !== C.equipe) {
    if (!(await ouvrir('Team'))) { out.push('SEG|ERREUR|OUVRIR_TEAM'); return show(); }
    const inp = [...document.querySelectorAll('input')].find(i => i.offsetParent && /Rechercher|Search/i.test(i.getAttribute('aria-label') || i.placeholder || ''));
    if (inp) { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, C.equipe); inp.dispatchEvent(new Event('input', { bubbles: true })); await sleep(1500); }
    const it = visibles().find(e => e.innerText.trim() === C.equipe);
    if (!it) { out.push('SEG|ERREUR|équipe ' + C.equipe + ' absente du segment Team'); await fermer('Team'); return show(); }
    it.click(); await sleep(2500); await fermer('Team');
  }
  // ---- Period (année niveau 1, mois niveau 2 ; un clic sur le mois le sélectionne seul)
  const voulu = new RegExp('^' + C.annee + '\\D.*\\b' + C.mois + '\\s*\\(month');
  if (C.annee && C.mois && !voulu.test(etat('Period'))) {
    if (!(await ouvrir('Period'))) { out.push('SEG|ERREUR|OUVRIR_PERIOD'); return show(); }
    let sc = visibles()[0];
    while (sc && !(sc.scrollHeight > sc.clientHeight + 5 && /auto|scroll/.test(getComputedStyle(sc).overflowY))) sc = sc.parentElement;
    if (sc) sc.scrollTop = 0;
    let y = null, fait = false;
    for (let i = 0; i < 80 && !fait; i++) {
      for (const e of visibles()) {
        const t = e.innerText.trim();
        if (e.getAttribute('aria-level') === '1') { if (/^\d{4}$/.test(t)) y = t; }
        else if (t === String(C.mois) && y === String(C.annee)) { e.click(); fait = true; break; }
      }
      if (!fait && sc) { sc.scrollTop += 30; await sleep(200); } else if (!sc) break;
    }
    await sleep(2500); await fermer('Period');
    if (!fait) { out.push('SEG|ERREUR|mois ' + C.mois + '/' + C.annee + ' introuvable dans Period'); return show(); }
  }
  await sleep(1500);
  out.push('SEG|team|' + etat('Team'), 'SEG|period|' + etat('Period'));
  out.push(voulu.test(etat('Period')) && (!C.equipe || etat('Team') === C.equipe) ? 'SEG|ok' : 'SEG|ERREUR|segments pas au bon réglage');
} catch (e) { out.push('SEG|ERREUR|' + e.message); }
return show();
})();
