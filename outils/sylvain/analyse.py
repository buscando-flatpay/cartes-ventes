#!/usr/bin/env python3
"""Sylvain — planning des 3 prochains jours de RDV de l'équipe de Quentin.

Usage : python3 analyse.py releve.txt ventes.json AAAA-MM-JJ(aujourd'hui) rapport.json [equipe=Quentin]

releve.txt : lignes de outils/sylvain/releve.js
  équipe | field sales | commerce | SIREN | type RDV | source | date RDV (JJ/MM/AAAA HH:MM) | statut
Règles :
  - jours = les 3 prochains jours ouvrés (lundi-vendredi) à partir d'aujourd'hui inclus
  - RDV comptés : tous sauf les reprogrammés (type RESCHEDULED ou statut « reprogrammé »),
    les follow-ups (type FOLLOW_UP) et les annulés (statut commençant par « Annulé »)
  - META : nom du commerce contenant le mot « meta » (META, [meta], (META), Meta POS…)
  - déjà client : SIREN présent dans les ventes de la carte (toutes équipes) ; « suivi_recent » si le même
    commercial a fait la vente il y a 30 jours ou moins (suivi normal, moins urgent)
"""
import json, os, re, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from maj import nom

OBJECTIF = 2.3
EXCLUS = {'Anisse Caputo'}   # commerciaux à ne pas suivre (demande de Quentin)
META = re.compile(r'(?i)(^|[^a-z])meta([^a-z]|$)')

def iso(d):
    m = re.search(r'(\d\d)/(\d\d)/(\d{4})', d or '')
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ''

def jours_suivants(j, n=3):
    d = date.fromisoformat(j); out = []
    while len(out) < n:
        if d.weekday() < 5: out.append(d.isoformat())
        d += timedelta(days=1)
    return out

def main(releve, vj, jour, rapport, equipe='Quentin'):
    v = json.load(open(vj, encoding='utf-8'))
    membres = [m for m in v['equipes'].get(equipe, []) if m not in EXCLUS]
    ventes = {}
    for x in v['ventes']:
        s = x.get('siren', '')
        if re.fullmatch(r'\d{9}', s or ''): ventes.setdefault(s, []).append(x)
    J = jours_suivants(jour)
    par = {}
    alertes, exclus = [], {'reprogrammes': 0, 'follow_up': 0, 'annules': 0}
    for l in open(releve, encoding='utf-8'):
        p = [x.strip() for x in l.rstrip('\n').split('|')]
        if len(p) < 8: continue
        team, s0, n, siren, ty, src, dt, st = p[:8]
        d = iso(dt)
        if d not in J: continue
        s, _ = nom(s0)
        if s in EXCLUS: continue
        if ty == 'RESCHEDULED' or re.search(r'(?i)reprogramm', st): exclus['reprogrammes'] += 1; continue
        if ty == 'FOLLOW_UP': exclus['follow_up'] += 1; continue
        if re.match(r'(?i)annul', st): exclus['annules'] += 1; continue
        if s not in membres: membres.append(s)
        c = par.setdefault(s, {'par_jour': {k: 0 for k in J}, 'meta_par_jour': {k: 0 for k in J}})
        c['par_jour'][d] += 1
        if META.search(n): c['meta_par_jour'][d] += 1
        if siren in ventes:
            x = sorted(ventes[siren], key=lambda y: y.get('d', ''))[-1]
            alertes.append({'commercial': s, 'date': dt, 'commerce': n, 'siren': siren, 'type': ty, 'source': src,
                            'vendu_le': x.get('d', ''), 'vendu_par': x.get('s', ''), 'client': x.get('n', ''), 'produit': x.get('prd', x.get('pr', '')),
                            'suivi_recent': bool(x.get('d')) and x.get('s') == s and (date.fromisoformat(d) - date.fromisoformat(x['d'])).days <= 30})
    com = []
    for s in membres:
        c = par.get(s, {'par_jour': {k: 0 for k in J}, 'meta_par_jour': {k: 0 for k in J}})
        tot = sum(c['par_jour'].values())
        com.append({'nom': s, 'par_jour': c['par_jour'], 'meta_par_jour': c['meta_par_jour'], 'total': tot,
                    'meta': sum(c['meta_par_jour'].values()), 'moyenne': round(tot / len(J), 2),
                    'jours_vides': [k for k in J if c['par_jour'][k] == 0]})
    com.sort(key=lambda x: (-x['total'], x['nom']))
    rep = {'jour': jour, 'jours': J, 'objectif': OBJECTIF, 'equipe': equipe, 'commerciaux': com,
           'totaux': {'rdv': sum(x['total'] for x in com), 'meta': sum(x['meta'] for x in com),
                      'par_jour': {k: sum(x['par_jour'][k] for x in com) for k in J}},
           'exclus': exclus, 'deja_clients': alertes}
    txt = json.dumps(rep, ensure_ascii=False, indent=1)
    open(rapport, 'w', encoding='utf-8').write(txt)
    print(txt)

if __name__ == '__main__':
    main(*sys.argv[1:6])
