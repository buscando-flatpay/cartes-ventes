#!/usr/bin/env python3
"""Jones — fusionne le relevé du portail dans ventes.json (ventes + RDV).

Usage : python3 fusion.py ventes.json releve.txt AAAA-MM-JJ(aujourd'hui) [rapport.json]

releve.txt : une ligne par rendez-vous, telle que sortie par releve.js :
  équipe | field sales | commerce | SIREN | type RDV | source | date RDV (JJ/MM/AAAA HH:MM) | statut
  | adresse | produit | lat | lon | score géocodage | code NAF

Ventes : ajoutées si (commercial, SIREN) ou (commercial, nom du commerce) est absent.
RDV    : à partir de la date de bascule (rdvcut, fixée au premier passage), chaque jour relevé
         remplace sa version précédente (statuts à jour, pas de double comptage) ; les agrégats
         `rdv` = base figée avant la bascule + jours relevés par Jones.
"""
import copy, json, os, re, sys, unicodedata
from collections import Counter, defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from categ import categorie
from maj import tc, nom, EQUIPE, PALETTE

RDV_CUT = '2026-11-20'          # premier jour de RDV pris en charge par Jones
RDONE = {'V', 'R', 'I', 'D', 'O'}
TYPES = {'MEETING': 'M', 'RESCHEDULED': 'R', 'FOLLOW_UP': 'F'}

def statut(s):
    s0 = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    if s0 == 'vente': return 'V'
    if s0.startswith('refus'): return 'R'
    if s0.startswith('impossible'): return 'I'
    if 'offre' in s0: return 'O'
    if 'document' in s0 or 'information' in s0 or 'validation' in s0: return 'D'
    if 'mcc' in s0: return 'M'
    if 'qualite' in s0: return 'Q'
    if s0.startswith('annul'): return 'A'
    if 'reprogramm' in s0: return 'P'
    return 'X'

PETITS = {'sur', 'sous', 'les', 'la', 'le', 'de', 'du', 'des', 'en', 'et', 'aux', 'au', 'lez', 'l', 'd'}
def ville_fmt(v):
    v = re.sub(r'\s+\d+.*$', '', v.strip())                      # « MARSEILLE 57 », « 9e Arrondissement »
    v = re.sub(r'\s+(\d+\s*(e|er|eme)\b.*)$', '', v, flags=re.I)
    if re.match(r'(?i)^marseille\b', v): return 'Marseille'
    v = unicodedata.normalize('NFD', v).encode('ascii', 'ignore').decode()
    parts = re.split(r"([\- '])", v.lower()); out = []
    for i, p in enumerate(parts):
        if p in "- '" or not p: out.append(p); continue
        nxt = parts[i + 1] if i + 1 < len(parts) else ''
        out.append(p if (i > 0 and (p in PETITS and (p not in ('l', 'd') or nxt == "'"))) else p[:1].upper() + p[1:])
    r = ''.join(out); return r[:1].upper() + r[1:]

def adresse(a):
    """« BD DE TESSE 46, 83000 TOULON » -> (« 46 Bd de Tesse, 83000 Toulon », '83000', 'Toulon')"""
    a = re.sub(r'\s+', ' ', a or '').strip()
    m = re.search(r',?\s*(\d{5})\s+([^,]+)', a)
    if not m: return (tc(a) if a else ''), '', ''
    rue, cp, ville = a[:m.start()].strip(' ,'), m.group(1), ville_fmt(m.group(2))
    n = re.match(r'^(.*?)[\s,]+(\d+\s*(?:bis|ter)?)$', rue, re.I)
    if n and not re.match(r'^\d', rue): rue = f"{n.group(2)} {n.group(1)}"
    rue = re.sub(r'^0\s+', '', rue)
    return f"{tc(rue)}, {cp} {ville}" if rue else f"{cp} {ville}", cp, ville

def iso(d):
    m = re.search(r'(\d\d)/(\d\d)/(\d{4})', d or '')
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ''

def produit(p):
    p = (p or '').strip()
    if not p: return None, None
    if re.search(r'(?i)terminal', p): return 'TPE', 'Terminal'
    if re.search(r'(?i)caisse', p):
        if re.search(r'15', p): return 'POS', 'Caisse 15"'
        if re.search(r'(?i)tablette', p): return 'POS', 'Caisse tablette'
        if re.search(r'(?i)mobile', p): return 'POS', 'Caisse mobile'
        return 'POS', 'Caisse'
    return None, p

def keyn(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower())

def main(vj, releve, jour, rapport=None):
    cur = json.load(open(vj, encoding='utf-8'))
    eq, col = cur['equipes'], cur['couleurs']
    have = {(d['s'], d.get('siren', '')) for d in cur['ventes']} | {(d['s'], 'N:' + keyn(d.get('n', ''))) for d in cur['ventes']}
    connus = set(sum(eq.values(), []))
    lignes = []
    for l in open(releve, encoding='utf-8'):
        p = [x.strip() for x in l.rstrip('\n').split('|')]
        if len(p) < 8 or not iso(p[6]): continue
        p += [''] * (14 - len(p))
        lignes.append(p)
    added, nouveaux = [], []

    def inscrire(s, tm, team):
        if s in connus: return
        t = 'Autres' if tm else EQUIPE.get(team, 'Autres')
        eq.setdefault(t, []).append(s); connus.add(s); nouveaux.append((s, t))
        if s not in col:
            used = set(col.values()); col[s] = next((c for c in PALETTE if c not in used), '#cbd5e1')

    # ---- ventes
    for team, s0, n, siren, ty, src, date, st, a, pr, lat, lon, sc, naf in lignes:
        if statut(st) != 'V': continue
        s, tm = nom(s0)
        sv = siren if re.fullmatch(r'\d{9}', siren) else ''
        if (sv and (s, sv) in have) or (s, 'N:' + keyn(n)) in have: continue
        inscrire(s, tm, team)
        d = dict(s=s, n=n, siren=sv or siren); rem = []
        d['c'] = categorie(naf, n)
        d['d'] = iso(date)
        pp, prd = produit(pr)
        if pp: d['pr'] = pp
        if prd: d['prd'] = prd
        if a:
            d['a'], cp, ville = adresse(a)
            if cp: d['v'] = f"{ville} ({cp[:2]})"
            try:
                la, lo = float(lat), float(lon)
                if 41.3 < la < 51.2 and -5.2 < lo < 9.7: d['lat'] = la; d['lon'] = lo
                else: rem.append('Adresse hors France métropolitaine · point hors carte')
                if sc and float(sc) < 0.45: rem.append('Position approximative (adresse peu précise)')
            except ValueError:
                rem.append('Adresse non localisée')
        else:
            d['a'] = 'Adresse non renseignée dans le CRM'; rem.append('Adresse absente du CRM')
        if not sv: rem.append('SIREN non renseigné dans le CRM')
        if rem: d['r'] = ' · '.join(rem)
        cur['ventes'].append(d); added.append(dict(d, team=team))
        have.add((s, sv or siren)); have.add((s, 'N:' + keyn(n)))
    cur['maj'] = jour

    # ---- RDV (jours >= bascule, jusqu'à la veille)
    if 'rdvbase' not in cur:
        cur['rdvbase'] = copy.deepcopy(cur.get('rdv', {})); cur['rdvcut'] = RDV_CUT
    cut = cur['rdvcut']
    rdvj = cur.setdefault('rdvj', {})
    jours = defaultdict(list)
    for team, s0, n, siren, ty, src, date, st, a, pr, lat, lon, sc, naf in lignes:
        dj = iso(date)
        if not (cut <= dj < jour): continue
        s, tm = nom(s0)
        ville = adresse(a)[2] if a else ''
        jours[dj].append([s, src or '?', TYPES.get(ty, (ty or 'I')[:1]), statut(st), ville])
    for dj, rows in jours.items(): rdvj[dj] = rows        # remplace la version précédente du jour
    agg = copy.deepcopy(cur['rdvbase'])
    for dj in sorted(rdvj):
        for s, src, t, st, ville in rdvj[dj]:
            R = agg.setdefault(s, {'k': [], 'c': [], 'f': dj})
            if dj < R.get('f', dj): R['f'] = dj
            k = next((x for x in R['k'] if x[0] == src and x[1] == t and x[2] == st), None)
            if k: k[3] += 1
            else: R['k'].append([src, t, st, 1])
            if st in RDONE and ville:
                c = next((x for x in R['c'] if x[0] == ville and x[1] == src), None)
                if not c: c = [ville, src, 0, 0]; R['c'].append(c)
                c[2] += 1; c[3] += 1 if st == 'V' else 0
    cur['rdv'] = agg
    if jours: cur['rdvmaj'] = jour
    if 'Autres' in eq: eq['Autres'] = eq.pop('Autres')
    json.dump(cur, open(vj, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    # ---- compte rendu
    veille = max(jours) if jours else None
    rv = [r for r in rdvj.get(veille, [])] if veille else []
    rep = {
        'jour': jour,
        'ventes_ajoutees': len(added),
        'par_equipe': Counter(EQUIPE.get(d['team'], 'Autres') for d in added),
        'par_commercial': Counter(d['s'] for d in added),
        'categories': Counter(d['c'] for d in added),
        'sans_point': [f"{d['s']} · {d['n']} ({d.get('r', '')})" for d in added if 'lat' not in d],
        'nouveaux_commerciaux': nouveaux,
        'rdv_jours_releves': sorted(jours),
        'rdv_veille': {'jour': veille, 'total': len(rv), 'realises': sum(1 for r in rv if r[3] in RDONE),
                       'ventes': sum(1 for r in rv if r[3] == 'V')},
        'total_ventes_carte': len(cur['ventes']),
    }
    txt = json.dumps(rep, ensure_ascii=False, indent=1)
    if rapport: open(rapport, 'w', encoding='utf-8').write(txt)
    print(txt)

if __name__ == '__main__':
    main(*sys.argv[1:5])
