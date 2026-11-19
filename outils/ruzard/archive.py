#!/usr/bin/env python3
"""Ruzard — gardien des archives du QG.

Usage :
  python3 archive.py semaine statut.json AAAA-MM-JJ sortie.json [semaine_precedente.json]
  python3 archive.py mois    statut.json AAAA-MM-JJ sortie.json [semaines_du_mois.json ...]
  python3 archive.py index   index.json  sortie.json <type> <id> <libellé>

statut.json : le document qg/statut du QG (comptes rendus de Jones, Sylvain, Hugues + historique).
semaine : photo de la semaine, document archives/semaines/AAAA-Wnn.
          Hugues : compilation du mois au vendredi + chiffres de la semaine par commercial
          (cumul de ce vendredi − cumul du vendredi précédent, si même mois ; sinon depuis le 1er du mois).
mois    : compilation provisoire du dernier jour, document archives/mois/AAAA-MM.
          Hugues la remplace le 1er du mois suivant par la compilation définitive (hugues_final).
index   : ajoute une entrée à archives/index (liste des archives disponibles pour le QG).
"""
import json, sys
from datetime import date, timedelta

CH = ['inst', 'ventes', 'og', 'pos_ventes', 'pos_inst']

def load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return None

def rapport(st, agent):
    a = (st.get('agents') or {}).get(agent) or {}
    return a.get('rapport') or a.get('dernier_rapport'), a

def activite(st, du, au):
    return {ag: {d: e for d, e in sorted(h.items()) if du <= d <= au} for ag, h in (st.get('historique') or {}).items()}

def hugues_photo(r):
    if not r or r.get('bug') or r.get('compilation') is None: return None
    return {k: r.get(k) for k in ('jour', 'mois', 'maj_powerbi', 'equipe', 'totaux', 'compilation')}

def semaine(st, jour, sortie, prec=None):
    J = date.fromisoformat(jour)
    lundi = J - timedelta(days=J.weekday()); vendredi = lundi + timedelta(days=4)
    an, num, _ = J.isocalendar()
    arc = {'type': 'semaine', 'id': f'{an}-W{num:02d}', 'du': lundi.isoformat(), 'au': vendredi.isoformat(), 'cree': jour,
           'activite': activite(st, lundi.isoformat(), (lundi + timedelta(days=6)).isoformat()), 'notes': []}
    rh, ah = rapport(st, 'hugues')
    h = hugues_photo(rh)
    p = load(prec) if prec else None
    if h:
        ph = (p or {}).get('hugues') or {}
        base = {x['nom']: x for x in ph.get('compilation') or []} if ph.get('mois') == h['mois'] else {}
        if not base: arc['notes'].append("Chiffres de la semaine comptés depuis le 1er du mois (pas d'archive de la semaine précédente sur ce mois).")
        h['semaine'] = sorted([{'nom': x['nom'], **{c: x.get(c, 0) - base.get(x['nom'], {}).get(c, 0) for c in CH}} for x in h['compilation']],
                              key=lambda y: (-y['ventes'], -y['inst'], y['nom']))
        h['semaine_tot'] = {c: sum(y[c] for y in h['semaine']) for c in CH}
        if ah.get('etat') == 'bloque': arc['notes'].append(f"Hugues bloqué le {ah.get('jour')} : chiffres du {h['jour']}.")
    else:
        arc['notes'].append("Pas de compilation Hugues exploitable cette semaine.")
    arc['hugues'] = h
    rs, _ = rapport(st, 'sylvain')
    arc['sylvain'] = rs
    rj, _ = rapport(st, 'jones')
    if rj:
        arc['jones'] = {'jour': rj.get('jour'), 'total_ventes_carte': rj.get('total_ventes_carte')}
        pj = ((p or {}).get('jones') or {}).get('total_ventes_carte')
        if isinstance(pj, int) and isinstance(rj.get('total_ventes_carte'), int):
            arc['jones']['ajoutees_semaine'] = rj['total_ventes_carte'] - pj
    write(arc, sortie)

def mois(st, jour, sortie, *semaines):
    J = date.fromisoformat(jour)
    debut = J.replace(day=1).isoformat()
    arc = {'type': 'mois', 'id': f'{J.year}-{J.month:02d}', 'du': debut, 'au': jour, 'cree': jour,
           'activite': activite(st, debut, jour), 'notes': []}
    rh, _ = rapport(st, 'hugues')
    h = hugues_photo(rh)
    if h and h['mois'] != arc['id']:
        arc['notes'].append(f"La dernière compilation Hugues porte sur {h['mois']}."); h = None
    arc['hugues_provisoire'] = h
    if h: arc['notes'].append(f"Compilation provisoire (Power BI du {h['jour']}). Hugues fige la version définitive au premier passage du mois suivant.")
    arc['semaines'] = sorted({s['id'] for s in map(load, semaines) if s and s.get('id')})
    rj, _ = rapport(st, 'jones')
    if rj: arc['jones'] = {'jour': rj.get('jour'), 'total_ventes_carte': rj.get('total_ventes_carte')}
    write(arc, sortie)

def index(idx, sortie, typ, ident, lib):
    i = load(idx) or {}
    i.setdefault('semaines', []); i.setdefault('mois', [])
    k = 'semaines' if typ == 'semaine' else 'mois'
    i[k] = [e for e in i[k] if e.get('id') != ident] + [{'id': ident, 'lib': lib}]
    i[k].sort(key=lambda e: e['id'], reverse=True)
    write(i, sortie)

def write(o, p):
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    open(p, 'w', encoding='utf-8').write(s); print(s[:1500])

if __name__ == '__main__':
    t, a = sys.argv[1], sys.argv[2:]
    if t != 'index': a[0] = load(a[0]) or {}
    {'semaine': semaine, 'mois': mois, 'index': index}[t](*a)
