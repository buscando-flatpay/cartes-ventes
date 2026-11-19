#!/usr/bin/env python3
"""Sylvie — tri des mails Outlook de Quentin (d'après outils/sylvie/releve.js, lecture seule).

Étape 1 : python3 analyse.py candidats releve.txt DEPUIS candidats.json
          DEPUIS = AAAA-MM-JJTHH:MM (heure de Paris) : début de la fenêtre (en général la veille 19h00).
          Garde les mails reçus depuis DEPUIS qui entrent dans au moins une catégorie :
            flatpay  : expéditeur Flatpay (hors robots), ou mail où Quentin est en copie avec des gens de Flatpay
            retention: mail qui parle de rétention / résiliation / churn
            support  : mail de ou vers support@flatpay.fr
            rh       : RH (Personio, équipe RH, congés, paie, mutuelle, période d'essai, notes de frais…)
          Un fil (même sujet) = une ligne : le dernier mail reçu, avec le nombre de mails du fil.
          Si Quentin a répondu après le dernier mail reçu, le fil est marqué "repondu".
Étape 2 : Sylvie lit candidats.json et écrit decisions.json :
          {"<id>": {"intervention": true|false, "pourquoi": "…", "a_faire": "…"}}
Étape 3 : python3 analyse.py rapport candidats.json decisions.json J rapport.json
"""
import json, re, sys, unicodedata
from datetime import datetime

MOI = 'quentin.dicharry@flatpay.fr'
DOM = ('@flatpay.fr', '@flatpay.com', '@flatpay.dk')
ROBOT = re.compile(r'(no-?reply|do_not_reply|donotreply|notification|mailer-daemon)', re.I)
RH_EXP = ('personio', 'salma.ettalbi', 'caroline.dechilly', 'lily.sully', 'zakaria.benfadel', 'nina.bazoge', 'rh@flatpay', 'hr@flatpay', 'people@flatpay', 'payroll', 'paie@')
RH_MOTS = re.compile(r"(cong[ée]s|\brtt\b|\bpaie\b|bulletin de salaire|fiche de paie|mutuelle|arr[êe]t maladie|p[ée]riode d.essai|note de frais|frais km|remboursement frais|ressources humaines|\brh\b|entretien annuel|onboarding|offboarding|d[ée]mission|rupture conventionnelle|avenant)", re.I)
RET_MOTS = re.compile(r'(r[ée]tention|retention|r[ée]silia|churn|r[ée]silier)', re.I)
DOSSIERS_EXCLUS = {'deleted items', 'éléments supprimés', 'junk email', 'courrier indésirable', 'drafts', 'brouillons'}

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'^\s*((re|tr|fw|fwd|rep)\s*:\s*)+', '', s)
    return re.sub(r'\W+', ' ', s).strip()

def lire(path):
    out = []
    for l in open(path, encoding='utf-8'):
        p = l.rstrip('\n').split('|')
        if p[0] != 'M' or len(p) < 10: continue
        tag, mid, email, nom, date, sujet, dossier, flags, apercu = p[1], p[2], p[3].lower(), p[4], p[5], p[6], p[7], p[8], '|'.join(p[9:])
        try: dt = datetime.strptime(date, '%d/%m/%Y %H:%M')
        except ValueError: continue
        out.append(dict(tag=tag, id=mid, email=email, nom=nom, dt=dt, sujet=sujet, dossier=dossier, flags=[f for f in flags.split(',') if f], apercu=apercu))
    return out

def categories(m, tags):
    txt = f"{m['sujet']} {m['apercu']}"
    c = set()
    flatpay_exp = m['email'].endswith(DOM) and not ROBOT.search(m['email'])
    if flatpay_exp or 'cc' in tags or 'interne' in tags: c.add('flatpay')
    if 'support' in tags or m['email'] == 'support@flatpay.fr' or 'support@flatpay.fr' in txt.lower(): c.add('support')
    if 'retention' in tags or RET_MOTS.search(txt): c.add('retention')
    if any(k in m['email'] for k in RH_EXP) or RH_MOTS.search(m['sujet']) or (flatpay_exp and RH_MOTS.search(txt)): c.add('rh')
    return c

def candidats(releve, depuis, sortie):
    D = datetime.fromisoformat(depuis)
    ms = lire(releve)
    tags = {}
    uniq = {}
    for m in ms:
        k = (m['email'], m['dt'], norm(m['sujet']))
        tags.setdefault(k, set()).add(m['tag'])
        if k not in uniq or (m['dossier'].lower() == 'inbox'): uniq[k] = m
    envoyes = [m for m in uniq.values() if m['email'] == MOI and m['dossier'].lower() in ('sent items', 'éléments envoyés') and '[Brouillon]' not in m['flags']]
    fils = {}
    for k, m in uniq.items():
        if m['dt'] < D or m['email'] == MOI: continue
        if m['dossier'].lower() in DOSSIERS_EXCLUS or '[Brouillon]' in m['flags']: continue
        if any(f in m['flags'] for f in ('Réunion acceptée', 'Réunion refusée')): continue
        if re.match(r"(notification de transfert de r[ée]union|accept[ée] ?:|refus[ée] ?:|accepted:|declined:)", m['sujet'], re.I): continue
        if ROBOT.search(m['email']) and not any(x in m['email'] for x in RH_EXP): continue
        c = categories(m, tags[k])
        if not c: continue
        f = fils.setdefault(norm(m['sujet']) or m['id'], {'mails': [], 'cats': set()})
        f['mails'].append(m); f['cats'] |= c
    res = []
    for cle, f in fils.items():
        f['mails'].sort(key=lambda m: m['dt'])
        d = f['mails'][-1]
        rep = any(norm(e['sujet']) == cle and e['dt'] > d['dt'] for e in envoyes) or 'A répondu' in d['flags']
        res.append({'id': d['id'][:8], 'categories': sorted(f['cats']), 'expediteur': d['nom'], 'email': d['email'],
                    'date': d['dt'].strftime('%Y-%m-%d %H:%M'), 'sujet': d['sujet'], 'apercu': d['apercu'][:300],
                    'non_lu': 'Non lu' in d['flags'], 'repondu': rep, 'nb_mails': len(f['mails']),
                    'autres_expediteurs': sorted({m['nom'] for m in f['mails'][:-1]} - {d['nom']})})
    res.sort(key=lambda x: x['date'], reverse=True)
    o = {'depuis': depuis, 'nb_lus': len([m for m in uniq.values() if m['dt'] >= D]), 'candidats': res}
    json.dump(o, open(sortie, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(o, ensure_ascii=False, indent=1))

def rapport(cand, dec, jour, sortie):
    C = json.load(open(cand, encoding='utf-8'))
    try: D = json.load(open(dec, encoding='utf-8'))
    except Exception: D = {}
    a, info = [], []
    for c in C['candidats']:
        d = D.get(c['id'], {})
        x = {**c, 'pourquoi': d.get('pourquoi', ''), 'a_faire': d.get('a_faire', '')}
        (a if d.get('intervention') else info).append(x)
    cats = {}
    for c in C['candidats']:
        for k in c['categories']: cats[k] = cats.get(k, 0) + 1
    o = {'jour': jour, 'depuis': C['depuis'], 'nb_lus': C['nb_lus'], 'nb_tries': len(C['candidats']),
         'par_categorie': cats, 'a_traiter': a,
         'pour_info': [{k: x[k] for k in ('id', 'categories', 'expediteur', 'date', 'sujet', 'pourquoi', 'repondu')} for x in info]}
    json.dump(o, open(sortie, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(o, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    {'candidats': candidats, 'rapport': rapport}[sys.argv[1]](*sys.argv[2:])
