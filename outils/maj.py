#!/usr/bin/env python3
"""Ajoute à ventes.json les ventes relevées sur le portail Flatpay.
Usage : python3 maj.py ventes.json lignes.txt AAAA-MM-JJ
lignes.txt : une vente par ligne, champs séparés par |
  équipe portail | field sales | commerce | SIREN | date RDV | adresse siège | lat | lon | état (ex. AA, CF)
"""
import json,re,sys
from collections import Counter
small={'de','du','des','la','le','les','et','au','aux','en','sur','sous','a'}
def tc(w):
    parts=re.split(r"([\-' ])",w.lower());out=[]
    for i,p in enumerate(parts):
        if p in "-' " : out.append(p);continue
        if not p: continue
        if p in ('l','d') and i+1<len(parts) and parts[i+1]=="'": out.append(p);continue
        if p in small and i>0: out.append(p);continue
        if re.fullmatch(r'(rd|rn|zi|za|zac|cc|bat|vc|ld|appt|imb|res)\d*',p) or re.fullmatch(r'[0-9a-z]*\d[0-9a-z]*',p): out.append(p.upper() if not p.isdigit() else p);continue
        out.append(p[:1].upper()+p[1:])
    r=''.join(out); return r[:1].upper()+r[1:]
def fmt(a):
    m=re.search(r'\b(\d{5})\s+(.+)$',a)
    if not m: return tc(a),None
    street=a[:m.start()].strip(); ville=re.sub(r'\s+(\d+\s*(EME|E ARRONDISSEMENT|ER)?|1)$','',m.group(2)).strip()
    return f"{tc(street)}, {m.group(1)} {tc(ville)}", m.group(1)

REN={'HOCHET Kelly':'Kelly Hochet','Raphael Bouteille':'Raphaël Bouteille','Roméo Michel Paul Rulleau':'Roméo Rulleau'}
EQUIPE={'Var - Marseille':'Quentin','Bouches du Rhône - Marseille':'Jean Barbier','Vaucluse - Marseille':'Roméo'}
PALETTE=["#fb7185","#34d399","#c084fc","#fbbf24","#2dd4bf","#f472b6","#60a5fa","#a3e635","#f97316","#e879f9","#4ade80","#facc15"]
def nom(s):
    s=s.strip();tm=s.startswith('(TM)')
    s=re.sub(r'^\(TM\)\s*','',s);s=REN.get(s,s)
    return s,tm
def main(vj,lignes,jour):
    cur=json.load(open(vj));eq=cur['equipes'];col=cur['couleurs']
    have={(d['s'],d['siren']) for d in cur['ventes']}
    connus=set(sum(eq.values(),[]))
    added=[];nouveaux=[]
    for l in open(lignes,encoding='utf-8'):
        l=l.rstrip('\n')
        if not l.strip(): continue
        p=l.split('|')
        if len(p)<9: print('ligne ignorée :',l);continue
        team,s,n,siren,date,a,lat,lon,st=[x.strip() for x in p[:9]]
        s,tm=nom(s);siren=re.sub(r'\s','',siren)
        if not re.fullmatch(r'\d{9}',siren) or (s,siren) in have: continue
        if s not in connus:
            t='Autres' if tm else EQUIPE.get(team,'Autres')
            eq.setdefault(t,[]).append(s);connus.add(s);nouveaux.append((s,t))
            if s not in col:
                used=set(col.values());col[s]=next((c for c in PALETTE if c not in used),'#cbd5e1')
        d=dict(s=s,n=n,siren=siren);rem=[]
        if not a or a=='NOTFOUND':
            d['a']='Adresse inconnue';rem.append('SIREN introuvable au registre')
        elif 'NON-DIFFUSIBLE' in a:
            d['a']='Adresse non publique au registre';rem.append('Adresse non publique (entrepreneur ayant refusé la diffusion)')
        else:
            d['a'],cp=fmt(a);m=re.search(r'(\d{5}) (.+)$',d['a'])
            if m: d['v']=f"{m.group(2)} ({m.group(1)[:2]})"
            try:
                la,lo=float(lat),float(lon)
                if 42.8<la<45.2 and 3.5<lo<7.8: d['lat']=la;d['lon']=lo
                else: rem.append('Siège hors région · point hors carte')
            except ValueError: rem.append('Pas de coordonnées au registre')
        if st[:1]=='C': rem.append('Entreprise cessée au registre')
        elif st[1:2]=='F': rem.append('Siège fermé au registre')
        if rem: d['r']=' · '.join(rem)
        cur['ventes'].append(d);added.append(d);have.add((s,siren))
    if 'Autres' in eq: eq['Autres']=eq.pop('Autres')
    cur['maj']=jour
    json.dump(cur,open(vj,'w'),ensure_ascii=False,separators=(',',':'))
    print('ajoutées',len(added),'· total',len(cur['ventes']))
    for s,c in Counter(d['s'] for d in added).most_common(): print(' ',s,c)
    sans=[d for d in added if 'lat' not in d]
    if sans: print('sans point :',len(sans))
    for s,t in nouveaux: print('nouveau commercial :',s,'->',t)
if __name__=='__main__': main(*sys.argv[1:4])
