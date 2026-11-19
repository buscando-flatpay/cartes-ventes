#!/usr/bin/env python3
"""Hugues — compilation du mois et chiffres de la veille, d'après le Power BI « Field Sales Report - TM - FR ».

Usage : python3 analyse.py releve.txt AAAA-MM-JJ(aujourd'hui) rapport.json [precedent.json] [--cloture AAAA-MM] [--fin-mois cloture.json]

--cloture AAAA-MM : relevé du mois précédent (Period réglé sur ce mois) pour figer sa compilation définitive,
                    rangée ensuite par Ruzard dans archives/mois/AAAA-MM (champ hugues_final).
                    La « veille » sort aussi : dernier jour du mois = clôture − dernier passage du mois.
--fin-mois cloture.json : au premier passage d'un nouveau mois, reprend la veille calculée par la clôture
                    (ventes et installations du dernier jour du mois précédent).

releve.txt : sorties de outils/hugues/releve.js (mode dash = TM Dash, puis mode og = Sales Performance)
precedent.json : le rapport du passage précédent (agents.hugues.rapport du QG), pour calculer la veille

Compilation (mois en cours, par commercial) : installations, ventes (Sales Signed), ventes OG, ventes POS,
installations POS, objectif du mois (Budget (Adj) (index)) et % de l'objectif atteint en installations et en ventes.
Veille : différence entre le cumul du mois lu aujourd'hui et celui du passage précédent (même mois).

CONTRÔLE POWER BI : si le total des installations du mois de l'équipe vaut 0 (à partir du 3 du mois),
ou si le filtre Period n'est pas sur le mois en cours, le Power BI est considéré en panne :
le rapport sort avec "bug": true et la raison ; Hugues ne remplace pas les données de la veille.
"""
import json, re, sys
from datetime import date, timedelta

CHAMPS = {'Installations': 'inst', 'Sales (Signed)': 'ventes', 'Sales OG': 'og', 'POS Sales': 'pos_ventes', 'POS Installations': 'pos_inst'}
BUDGET = 'Budget (Adj) (index)'   # objectif du mois (installations et ventes), colonne 2 du Power BI
HORS = {'France', 'Sud Est', 'Total'}

def num(v):
    v = (v or '').replace(' ', '').replace(' ', '').replace(',', '.')
    try: return int(float(v)) if v not in ('', '-', '(Vide)') else 0
    except ValueError: return 0

def main(releve, jour, rapport, precedent=None, cloture=None, fin_mois=None):
    J = date.fromisoformat(jour)
    meta, lignes = {}, {}
    for l in open(releve, encoding='utf-8'):
        p = l.rstrip('\n').split('|')
        if p[0] == 'META' and len(p) >= 3: meta.setdefault(p[1], p[2])
        elif p[0] == 'L' and len(p) >= 2:
            d = lignes.setdefault(p[1].strip(), {})
            for kv in p[2:]:
                if '=' in kv:
                    k, v = kv.split('=', 1)
                    if k in CHAMPS: d[CHAMPS[k]] = num(v)
                    elif k == BUDGET: d['budget'] = num(v)
    equipe = meta.get('equipe', '')
    m = re.search(r'(\d{4}).*?(\d{1,2})\s*\(month', meta.get('periode', ''))
    mois = f"{m.group(1)}-{int(m.group(2)):02d}" if m else ''
    total = lignes.get('Total') or lignes.get(equipe) or {}
    rep = {'jour': jour, 'mois': mois, 'maj_powerbi': meta.get('maj', ''), 'equipe': equipe, 'bug': False, 'raison': '', 'avertissements': []}

    # ---- contrôle de cohérence (bug Power BI)
    attendu = cloture or f"{J.year}-{J.month:02d}"
    if cloture: rep.update(cloture=True, definitif=True)
    if not lignes or not total:
        rep.update(bug=True, raison="Tableau Power BI vide ou illisible")
    elif mois != attendu:
        rep.update(bug=True, raison=f"Le filtre Period du Power BI est sur {mois or '?'} au lieu de {attendu}")
    elif total.get('inst', 0) == 0 and (cloture or J.day >= 3):
        rep.update(bug=True, raison="Total des installations du mois à 0 : le Power BI beugue")
    md = re.search(r'(\d\d)/(\d\d)/(\d\d)', rep['maj_powerbi'])
    if md:
        dmaj = date(2000 + int(md.group(3)), int(md.group(2)), int(md.group(1)))
        if dmaj < J - timedelta(days=1):
            rep['avertissements'].append(f"Données Power BI mises à jour le {dmaj.strftime('%d/%m')} seulement")
    if rep['bug']:
        out = json.dumps(rep, ensure_ascii=False, indent=1); open(rapport, 'w', encoding='utf-8').write(out); print(out); return

    # ---- compilation du mois
    comp = []
    for nom, d in lignes.items():
        if nom in HORS or nom == equipe: continue
        n = re.sub(r'^\(terminated\)\s*', '', nom)
        x = {'nom': n, 'parti': n != nom, 'budget': d.get('budget', 0), **{c: d.get(c, 0) for c in CHAMPS.values()}}
        x['pct_inst'] = round(100 * x['inst'] / x['budget']) if x['budget'] else None
        x['pct_ventes'] = round(100 * x['ventes'] / x['budget']) if x['budget'] else None
        comp.append(x)
    comp.sort(key=lambda x: (-x['inst'], -x['ventes'], x['nom']))
    if not comp:
        rep.update(bug=True, raison="Aucune ligne commercial dans le tableau (matrice repliée : déplier Sud Est puis l'équipe)")
        out = json.dumps(rep, ensure_ascii=False, indent=1); open(rapport, 'w', encoding='utf-8').write(out); print(out); return
    rep['compilation'] = comp
    rep['totaux'] = {c: total.get(c, sum(x[c] for x in comp)) for c in CHAMPS.values()}
    rep['totaux']['budget'] = total.get('budget', sum(x['budget'] for x in comp))
    b = rep['totaux']['budget']
    rep['totaux']['pct_inst'] = round(100 * rep['totaux']['inst'] / b) if b else None
    rep['totaux']['pct_ventes'] = round(100 * rep['totaux']['ventes'] / b) if b else None

    # ---- veille (différence avec le passage précédent)
    prev = None
    if precedent:
        try: prev = json.load(open(precedent, encoding='utf-8'))
        except Exception: prev = None
    if prev and prev.get('base_veille', True) and prev.get('mois') == mois and prev.get('compilation') is not None and prev.get('jour') != jour:
        pc = {x['nom']: x for x in prev['compilation']}
        v = [{'nom': x['nom'], **{c: x[c] - pc.get(x['nom'], {}).get(c, 0) for c in CHAMPS.values()}} for x in comp]
        rep['veille'] = sorted(v, key=lambda y: (-y['ventes'], -y['inst'], y['nom']))
        rep['veille_depuis'] = prev.get('jour')
        if any(v[c] < 0 for v in rep['veille'] for c in CHAMPS.values()):
            rep['avertissements'].append("Certains chiffres ont baissé depuis hier (corrections dans le Power BI)")
    elif prev and prev.get('mois') and prev.get('mois') != mois and prev.get('base_veille', True):
        fm = None
        if fin_mois:
            try: fm = json.load(open(fin_mois, encoding='utf-8'))
            except Exception: fm = None
        if fm and fm.get('mois') == prev.get('mois') and fm.get('veille') is not None:
            rep['veille'] = fm['veille']; rep['veille_depuis'] = fm.get('veille_depuis')
            rep['veille_note'] = f"Nouveau mois : la compilation repart de zéro. « Veille » = dernier jour de {prev['mois']}, d'après la compilation définitive."
        else:
            rep['veille'] = None; rep['veille_note'] = "Nouveau mois : la compilation repart de zéro, pas de chiffres de la veille aujourd'hui."
    else:
        rep['veille'] = None; rep['veille_note'] = "Premier passage : les chiffres de la veille seront disponibles dès demain."
    out = json.dumps(rep, ensure_ascii=False, indent=1)
    open(rapport, 'w', encoding='utf-8').write(out); print(out)

if __name__ == '__main__':
    a, opt = [], {}
    it = iter(sys.argv[1:])
    for x in it:
        if x == '--cloture': opt['cloture'] = next(it)
        elif x == '--fin-mois': opt['fin_mois'] = next(it)
        else: a.append(x)
    main(*a[:4], **opt)
