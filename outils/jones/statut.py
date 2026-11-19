#!/usr/bin/env python3
"""Met à jour le statut d'un agent pour le QG privé (document qg/statut de la page Claude « Le QG »).

Usage :
  python3 statut.py statut.json jones ok rapport.json     # mission réussie
  python3 statut.py statut.json jones bloque "message"     # mission bloquée
Le fichier statut.json est créé s'il n'existe pas. Historique gardé sur 60 jours.
"""
import json, os, sys
from datetime import datetime, timedelta

def main(path, agent, etat, arg):
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo('Europe/Paris'))
    except Exception:  # pas de base de fuseaux : heure de Paris approximée (UTC+1, UTC+2 d'avril à octobre)
        from datetime import timezone
        u = datetime.now(timezone.utc); now = u + timedelta(hours=2 if 4 <= u.month <= 10 else 1)
    jour = now.strftime('%Y-%m-%d')
    st = json.load(open(path, encoding='utf-8')) if os.path.exists(path) and os.path.getsize(path) else {}
    st.setdefault('v', 1); st.setdefault('agents', {}); st.setdefault('historique', {})
    a = {'etat': etat, 'jour': jour, 'fin': now.strftime('%Y-%m-%dT%H:%M')}
    if etat == 'ok':
        a['rapport'] = json.load(open(arg, encoding='utf-8'))
    else:
        a['blocage'] = arg
        prev = st['agents'].get(agent, {})
        if prev.get('rapport'): a['dernier_rapport'] = prev['rapport']; a['dernier_ok'] = prev.get('fin') if prev.get('etat') != 'bloque' else prev.get('dernier_ok')
        elif prev.get('dernier_rapport'): a['dernier_rapport'] = prev['dernier_rapport']; a['dernier_ok'] = prev.get('dernier_ok')
    st['agents'][agent] = a
    h = st['historique'].setdefault(agent, {})
    h[jour] = etat
    limite = (now - timedelta(days=60)).strftime('%Y-%m-%d')
    for d in [d for d in h if d < limite]: del h[d]
    st['maj'] = a['fin']
    json.dump(st, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('statut', agent, etat, a['fin'])

if __name__ == '__main__':
    main(*sys.argv[1:5])
