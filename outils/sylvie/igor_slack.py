#!/usr/bin/env python3
"""Sylvie × Igor — rédige le point « installations » de chaque commercial pour Slack.

Usage : python3 igor_slack.py rapport_igor.json sortie_dossier [--test] [--seulement "Prénom Nom"] [--config manager.json]

- rapport_igor.json : le rapport d'Igor (agents.igor.rapport du QG).
- Écrit dans sortie_dossier : messages.json (liste {sales, dm, prenom, texte, nb}), apercu.txt et un fichier
  envoi_N.js par message, prêt à exécuter dans Slack (Claude in Chrome) : il contient le texte et le script
  d'envoi outils/sylvie/slack.js.
- --test : tous les messages partent dans l'espace perso de Quentin (« Quentin Dicharry (you) »), avec en tête
  « [ESSAI — message prévu pour X] ». Rien n'est envoyé aux commerciaux.

Catégories (calculées par Igor, analyse.py) : valide, proche, suivre, alerte, checker.
"""
import json, os, sys
from datetime import date

EQUIPE = 'T06TFEQQ0UV'
QUENTIN = ('Quentin Dicharry', 'D099DHUJW2X')
DM = {   # conversations privées Slack de Quentin avec chaque commercial (relevées le 20/11/2026)
    'Matis Deroin': 'D0A33R3SG0L',
    'Nicolas Yakdi': 'D09KXE9R8GL',
    'Ilyas Laraba': 'D0A6LEK5PK5',
    'Adam Kandil': 'D0AGD2BSV99',
    'Mattéo Dionot': 'D0BSX5Z6EQ4',
    'Sandy Debackere': 'D0CDYUDLXLY',
    'Baptiste Mignoni': 'D0CE15P8WUQ',
}
EXCLUS = {'Anisse Caputo'}


def eur(v):
    v = round(float(v or 0), 2)
    ent, dec = f"{v:,.2f}".split('.')
    ent = ent.replace(',', ' ')
    return f"{ent} €" if dec == '00' else f"{ent},{dec} €"


def pct(v):
    v = float(v or 0)
    return f"{v:.0f} %" if v >= 10 or v == int(v) else f"{v:.1f} %".replace('.', ',')


def quand(r, J):
    j = r.get('jours_sans')
    if r.get('dernier_inconnu') and j is None: return "dernier encaissement introuvable"
    if j is None: return "aucun encaissement pour l'instant"
    if j == 0: return "a encaissé aujourd'hui"
    if j == 1: return "dernier encaissement hier"
    d = date.fromisoformat(r['dernier'])
    return f"dernier encaissement le {d.strftime('%d/%m')} (il y a {j} jours)"


def ligne(r, cat, J):
    nom, chiffres = r['nom'], f"{eur(r['live'])} / {eur(r['seuil'])}"
    verif = " (chiffre à vérifier)" if r.get('controle') == 'KO' or not r.get('lu', True) else ''
    if cat == 'valide':
        if (r.get('jour') or 0) > 0:
            return f"• {nom} est validée grâce aux {eur(r['jour'])} encaissés aujourd'hui ({chiffres}){verif}"
        return f"• {nom} est validée ({chiffres}){verif}"
    if cat == 'proche':
        if (r.get('jour') or 0) > 0:
            return (f"• {nom} va pas tarder à valider : {pct(r['pct'])} ({chiffres}), le client a encore encaissé "
                    f"{eur(r['jour'])} aujourd'hui. Plus que {eur(r['reste'])} !{verif}")
        return f"• {nom} va pas tarder à valider : {pct(r['pct'])} ({chiffres}), plus que {eur(r['reste'])} · {quand(r, J)}{verif}"
    if cat == 'suivre':
        return f"• {nom} : {pct(r['pct'])} ({chiffres}) · {quand(r, J)}{verif}"
    if cat == 'alerte':
        j = r.get('jours_sans')
        depuis = f"n'a pas encaissé depuis {j} jours" if j is not None else "n'a pas d'encaissement récent connu"
        return (f"• {nom} {depuis} alors qu'elle est à {pct(r['pct'])} de validation ({chiffres}), "
                f"suis-la de près, j'attends ton retour !{verif}")
    # checker
    bits = [f"{pct(r['pct'])} ({chiffres})"]
    if r.get('statut') and r['statut'] != 'Livré': bits.append(r['statut'].lower())
    bits.append(quand(r, J))
    if r.get('attente_j') is not None: bits.append(f"créée il y a {r['attente_j']} j")
    return f"• {nom} : " + ' · '.join(bits) + verif


SECTIONS = [
    ('valide', '🎉 FÉLICITATIONS !'),
    ('proche', '🚀 ÇA AVANCE FORT !'),
    ('suivre', '👀 À SUIVRE !'),
    ('alerte', '⚠️ ATTENTION !'),
    ('checker', '🔧 À CHECKER OU INSTALLER'),
]


def message(sales, insts, sorties, rap, J):
    prenom = sales.split()[0]
    jour = date.fromisoformat(rap['jour']).strftime('%d/%m')
    heure = (rap.get('heure') or '').replace(':', 'h')
    out = [f"Salut {prenom} 👋 Le point sur tes installations en attente ({jour}{' à ' + heure if heure else ''}) :"]
    par = {c: [] for c, _ in SECTIONS}
    for r in insts:
        c = r.get('categorie')
        if not c:   # rapport d'un ancien Igor : on recalcule
            q = r.get('pct') or 0
            c = 'valide' if q >= 100 else 'proche' if q >= 80 else ('suivre' if (r.get('jours_sans') is not None and r['jours_sans'] <= 2) else 'alerte') if q >= 40 else 'checker'
        par[c].append(r)
    fel = [ligne(r, 'valide', J) for r in par['valide']]
    fel += [f"• {s['nom']} est sortie de la liste des installations en attente : validée ✅" for s in sorties]
    for c, titre in SECTIONS:
        lignes = fel if c == 'valide' else [ligne(r, c, J) for r in sorted(par[c], key=lambda r: -(r.get('pct') or 0))]
        if lignes: out += ['', titre, *lignes]
    return '\n'.join(out), sum(len(v) for v in par.values()) + len(sorties)


def charger_config(chemin):
    """Réglages d'un autre manager (voir config/exemple_manager.json). Sans --config : réglages de Quentin."""
    global EQUIPE, QUENTIN, DM, EXCLUS
    c = json.load(open(chemin, encoding='utf-8'))
    EQUIPE = c.get('slack_equipe', EQUIPE)
    QUENTIN = (c['nom'], c['slack_moi'])
    DM = dict(c['slack_dm'])
    EXCLUS = set(c.get('exclus', []))


def main():
    args = sys.argv[1:]
    if '--config' in args:
        i = args.index('--config'); charger_config(args[i + 1]); del args[i:i + 2]
    test = '--test' in args
    seul = None
    if '--seulement' in args: seul = args[args.index('--seulement') + 1]
    pos = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] != '--seulement')]
    rap = json.load(open(pos[0], encoding='utf-8'))
    if 'rapport' in rap and 'installations' not in rap: rap = rap['rapport']
    dossier = pos[1]
    os.makedirs(dossier, exist_ok=True)
    J = date.fromisoformat(rap['jour'])
    par = {}
    for r in rap.get('installations', []):
        if r['sales'] in EXCLUS: continue
        par.setdefault(r['sales'], []).append(r)
    sorties = {}
    for s in rap.get('sorties', []) or []:
        if s.get('sales') not in EXCLUS: sorties.setdefault(s.get('sales'), []).append(s)
    msgs, inconnus = [], []
    for sales in sorted(set(par) | set(sorties)):
        if seul and sales != seul: continue
        if sales not in DM: inconnus.append(sales); continue
        texte, nb = message(sales, par.get(sales, []), sorties.get(sales, []), rap, J)
        dest_nom, dest_dm = (QUENTIN if test else (sales, DM[sales]))
        if test: texte = f"[ESSAI — message prévu pour {sales}]\n" + texte
        msgs.append({'sales': sales, 'prenom': sales.split()[0], 'dest': dest_nom, 'dm': dest_dm,
                     'url': f"https://app.slack.com/client/{EQUIPE}/{dest_dm}", 'texte': texte, 'nb': nb})
    json.dump({'jour': rap['jour'], 'heure': rap.get('heure'), 'test': test, 'messages': msgs, 'sans_slack': inconnus},
              open(os.path.join(dossier, 'messages.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    base = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slack.js'), encoding='utf-8').read()
    corps = base[base.index('(async () => {'):]
    with open(os.path.join(dossier, 'apercu.txt'), 'w', encoding='utf-8') as ap:
        for i, m in enumerate(msgs, 1):
            cfg = {'dest': m['dest'], 'dm': m['dm'], 'texte': m['texte']}
            open(os.path.join(dossier, f'envoi_{i}.js'), 'w', encoding='utf-8').write(
                'window.SLACK_ENVOI=' + json.dumps(cfg, ensure_ascii=False) + ';\nawait ' + corps)
            ap.write(f"===== {i}. {m['sales']} → {m['dest']} ({m['url']})\n{m['texte']}\n\n")
            print(f"{i}. {m['sales']} → {m['dest']} : {m['nb']} installation(s)  [envoi_{i}.js]")
    if inconnus: print('SANS CONVERSATION SLACK :', ', '.join(inconnus))


if __name__ == '__main__':
    main()
