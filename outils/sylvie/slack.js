// Sylvie — envoi d'UN message dans UNE conversation privée Slack de Quentin (Claude in Chrome, app.slack.com).
// Le lanceur définit avant ce code : window.SLACK_ENVOI = {dest:'Matis Deroin', dm:'D0A33R3SG0L', texte:'…'}
// et l'onglet doit déjà être sur https://app.slack.com/client/T06TFEQQ0UV/<dm>.
// Contrôles : bonne conversation (titre = dest), champ de saisie vide (on ne touche jamais à un brouillon de
// Quentin), message pas déjà envoyé (anti-doublon), texte collé identique avant l'envoi, envoi confirmé.
// Réponses : ENVOYE | DEJA_ENVOYE | ERREUR <raison>. Ne fait rien d'autre dans Slack.
(async () => {
const C = window.SLACK_ENVOI || {};
const sleep = t => new Promise(r => setTimeout(r, t));
const waitFor = async (f, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = f(); if (v) return v; await sleep(200); } return null; };
const norm = s => String(s || '').normalize('NFC').replace(/[^\p{L}\p{N}]+/gu, '').toLowerCase();
if (!C.dm || !C.dest || !C.texte) return 'ERREUR window.SLACK_ENVOI incomplet';
if (!location.pathname.endsWith('/' + C.dm)) return 'ERREUR mauvaise page : ouvrir https://app.slack.com/client/T06TFEQQ0UV/' + C.dm;
const titre = await waitFor(() => { const h = document.querySelector('[data-qa="channel_name"]'); return h && h.innerText.trim() ? h.innerText.trim() : null; }, 20000);
if (!titre || !norm(titre).startsWith(norm(C.dest))) return 'ERREUR conversation inattendue : ' + (titre || 'titre introuvable');
const ed = await waitFor(() => document.querySelector('[data-qa="message_input"] .ql-editor'), 15000);
if (!ed) return 'ERREUR champ de saisie introuvable';
await sleep(1500);
const lignes = C.texte.split('\n').filter(l => l.trim());
const cle = norm(lignes.slice(0, 2).join(' '));
const dejaLa = () => [...document.querySelectorAll('[data-qa="message-text"]')].slice(-15).some(m => norm(m.innerText).includes(cle));
if (dejaLa()) return 'DEJA_ENVOYE';
if (norm(ed.innerText) !== '') return 'ERREUR un brouillon est déjà en cours dans cette conversation (non touché)';
ed.focus();
const r = document.createRange(); r.selectNodeContents(ed); r.collapse(false);
const s = getSelection(); s.removeAllRanges(); s.addRange(r);
document.execCommand('insertText', false, C.texte);
await sleep(600);
if (norm(ed.innerText) !== norm(C.texte)) {
  ed.focus(); document.execCommand('selectAll', false); document.execCommand('delete', false);
  return 'ERREUR texte mal collé : champ vidé, rien envoyé';
}
const btn = document.querySelector('[data-qa="texty_send_button"]');
if (!btn || btn.disabled || btn.getAttribute('aria-disabled') === 'true') {
  ed.focus(); document.execCommand('selectAll', false); document.execCommand('delete', false);
  return 'ERREUR bouton Envoyer indisponible : champ vidé, rien envoyé';
}
btn.click();
const vide = await waitFor(() => norm(ed.innerText) === '', 8000);
const vu = await waitFor(dejaLa, 10000);
if (vu) return 'ENVOYE';
return vide ? 'ERREUR envoi non confirmé (champ vidé mais message non retrouvé) : vérifier la conversation' : 'ERREUR le message est resté dans le champ : vérifier la conversation';
})();
