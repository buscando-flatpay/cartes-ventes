#!/usr/bin/env python3
"""Igor — où en sont les installations de l'équipe, en direct.

Usage : python3 analyse.py releve.txt rapport.json [precedent.json]

Règle de validation : une installation est validée quand ses recettes atteignent 0,5 % du chiffre
d'affaires annuel déclaré, soit Volume attendu × 12 × 0,5 % (= Volume attendu × 0,06).
En direct = « Recettes depuis le démarrage » (arrêtées à la veille) + ventes terminées du jour
(remboursements déduits), lues dans les transactions du client.
precedent.json : le rapport du passage précédent, pour repérer les installations sorties de la liste
(validées) et les nouvelles.
"""
import json, sys
from datetime import date, datetime

def num(v):
    try: return float(str(v).replace(',', '.')) if str(v).strip() not in ('', '-') else 0.0
    except ValueError: return 0.0

def main(releve, sortie, precedent=None):
    meta, inst = {}, []
    for l in open(releve, encoding='utf-8'):
        p = l.rstrip('\n').split('|')
        if p[0] == 'META' and len(p) >= 3: meta[p[1]] = p[2]
        elif p[0] == 'I' and len(p) >= 12:
            inst.append(dict(sales=p[1], nom=p[2], siren=p[3], volume=num(p[4]), creation=p[5], livraison=p[6], statut=p[7],
                             recettes=num(p[8]), n_jour=int(num(p[9])), jour=num(p[10]), controle=p[11], note=p[12] if len(p) > 12 else '',
                             lu=p[9] != ''))
    J = date.fromisoformat(meta.get('jour', date.today().isoformat()))
    res = []
    for x in inst:
        seuil = round(x['volume'] * 0.06, 2)
        live = round(x['recettes'] + x['jour'], 2)
        pct = round(100 * live / seuil, 1) if seuil else None
        try: d = datetime.strptime(x['creation'], '%d/%m/%Y %H:%M').date(); attente = (J - d).days
        except ValueError: attente = None
        res.append({**x, 'annuel': round(x['volume'] * 12), 'seuil': seuil, 'live': live, 'pct': pct,
                    'pct_hier': round(100 * x['recettes'] / seuil, 1) if seuil else None,
                    'reste': round(max(seuil - live, 0), 2), 'valide': bool(pct is not None and pct >= 100), 'attente_j': attente})
    res.sort(key=lambda r: (-(r['pct'] or 0), r['nom']))
    par = {}
    for r in res:
        s = par.setdefault(r['sales'], {'sales': r['sales'], 'nb': 0, 'valides': 0, 'en_cours': 0, 'zero': 0, 'jour': 0.0})
        s['nb'] += 1; s['jour'] = round(s['jour'] + r['jour'], 2)
        if r['valide']: s['valides'] += 1
        elif r['live'] > 0: s['en_cours'] += 1
        else: s['zero'] += 1
    rep = {'jour': J.isoformat(), 'heure': meta.get('heure', ''), 'installations': res,
           'par_sales': sorted(par.values(), key=lambda s: (-s['valides'], -s['en_cours'], s['sales'])),
           'totaux': {'nb': len(res), 'valides': sum(r['valide'] for r in res), 'proches': sum(1 for r in res if not r['valide'] and (r['pct'] or 0) >= 75),
                      'en_cours': sum(1 for r in res if not r['valide'] and r['live'] > 0), 'zero': sum(1 for r in res if r['live'] <= 0),
                      'jour': round(sum(r['jour'] for r in res), 2), 'controle_ko': sum(1 for r in res if r['controle'] == 'KO' or not r['lu'])},
           'sorties': [], 'nouvelles': []}
    if precedent:
        try: prev = json.load(open(precedent, encoding='utf-8'))
        except Exception: prev = None
        if prev and prev.get('installations') is not None:
            k = lambda r: (r['nom'], r['creation'])
            avant = {k(r): r for r in prev['installations']}
            maint = {k(r) for r in res}
            rep['sorties'] = [{'nom': r['nom'], 'sales': r['sales'], 'pct': r.get('pct')} for kk, r in avant.items() if kk not in maint]
            rep['nouvelles'] = [{'nom': r['nom'], 'sales': r['sales']} for r in res if k(r) not in avant]
            rep['depuis'] = f"{prev.get('jour', '')} {prev.get('heure', '')}".strip()
    out = json.dumps(rep, ensure_ascii=False, indent=1)
    open(sortie, 'w', encoding='utf-8').write(out)
    t = rep['totaux']
    print(f"{t['nb']} installations · {t['valides']} validées · {t['proches']} à plus de 75 % · {t['zero']} à 0 € · {t['jour']} € encaissés aujourd'hui")
    for r in res[:12]: print(f"  {r['pct']}% {r['nom']} ({r['sales']}) {r['live']}/{r['seuil']} € dont {r['jour']} aujourd'hui")

if __name__ == '__main__':
    main(*sys.argv[1:4])
