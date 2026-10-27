"""Code NAF (+ nom du commerce) -> catégorie métier lisible."""
import re, unicodedata

def _norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s) + ' '

# mots-clés sur le nom : prioritaires quand le NAF est générique
KW = [
    ('Discothèque / club', r' (discotheque|night ?club|nightclub|club disco|boite de nuit) '),
    ('Boulangerie / pâtisserie', r' (boulang\w*|patisser\w*|fournil|viennois\w*) '),
    ('Restauration rapide', r' (pizz\w*|kebab|tacos|burger\w*|snack\w*|sandwich\w*|fast ?food|food ?truck|poke|sushi\w*|crepe\w*|crepier\w*|bagel\w*|wok|friterie|chicken|grill\w*|food\w*|naan) '),
    ('Bar / café', r' (bar|pub|cafe|lounge|brasserie|cave a biere|tapas|bistrot|bistro) '),
    ('Restaurant', r' (restaurant|resto|marmite|trattoria|osteria|auberge|table|cuisine) '),
    ('Coiffure / barbier', r' (coiff\w*|barber\w*|barbier|hair\w*|salon) '),
    ('Beauté / esthétique', r' (beaute|esthetique|ongle\w*|nails?|onglerie|spa|massage|institut|cils|lash\w*|tattoo|tatouage|bronzage) '),
    ('Boucherie / traiteur', r' (boucher\w*|charcut\w*|traiteur|volaill\w*) '),
    ('Épicerie / alimentation', r' (epicer\w*|primeur\w*|fromag\w*|superette|market|alimentation|cave|vins?|caviste|poissonn\w*|halal) '),
    ('Tabac / presse / vape', r' (tabac|presse|vape|smoke|cigarette\w*|cbd) '),
    ('Garage / auto / moto', r' (garage|auto\w*|moto\w*|carross\w*|pneu\w*|lavage) '),
    ('Téléphonie / informatique', r' (phone\w*|telephon\w*|gsm|mobile|informatique|repar\w*) '),
    ('Hôtellerie / hébergement', r' (hotel\w*|camping|gite\w*|residence) '),
    ('Fleuriste', r' (fleur\w*|florist\w*) '),
]

def by_naf(naf):
    if not naf or naf in ('NF', 'NA', 'ERR', '?', '00.00Z'):
        return None
    c = naf.replace('.', '')
    d2, d4 = c[:2], c[:4]
    if c == '5610A': return 'Restaurant'
    if c in ('5610B', '5610C'): return 'Restauration rapide'
    if c == '5630Z': return 'Bar / café'
    if d4 in ('5621', '5629'): return 'Boucherie / traiteur'
    if c in ('1071B', '1071C', '1071D', '4724Z', '1072Z'): return 'Boulangerie / pâtisserie'
    if c in ('1011Z', '1012Z', '1013A', '1013B', '4722Z', '1085Z'): return 'Boucherie / traiteur'
    if c in ('4723Z',): return 'Épicerie / alimentation'
    if d4 in ('4711', '4721', '4725', '4729', '4781') or c in ('1039B', '1052Z', '1082Z', '1089Z', '1101Z', '1102B'): return 'Épicerie / alimentation'
    if c in ('4726Z', '4762Z'): return 'Tabac / presse / vape'
    if c == '9602A': return 'Coiffure / barbier'
    if c in ('9602B', '9604Z', '9609Z'): return 'Beauté / esthétique'
    if d2 == '55': return 'Hôtellerie / hébergement'
    if d2 == '45' or c in ('7711A', '7711B', '5221Z'): return 'Garage / auto / moto'
    if c in ('4741Z', '4742Z', '4743Z', '9511Z', '9512Z', '9521Z', '9522Z', '9529Z', '6201Z', '6202A'): return 'Téléphonie / informatique'
    if c == '4776Z': return 'Fleuriste'
    if c in ('4773Z', '4774Z', '4778A') or d2 in ('86', '87', '75'): return 'Santé / pharmacie / optique'
    if c in ('4771Z', '4772A', '4772B', '4782Z'): return 'Mode / chaussures'
    if d4 in ('4751', '4752', '4753', '4754', '4759'): return 'Maison / déco / bricolage'
    if c == '4775Z': return 'Beauté / esthétique'
    if d2 == '47': return 'Commerce de détail'
    if d2 == '46': return 'Commerce de gros'
    if d2 in ('93', '92', '90', '91') or c in ('8551Z', '7721Z', '7990Z', '7911Z', '7912Z'): return 'Sport / loisirs / culture'
    if d2 in ('41', '42', '43'): return 'BTP / artisans du bâtiment'
    if d2 == '49' or d2 in ('50', '51', '53'): return 'Transport / taxi / livraison'
    if c.startswith('9601'): return 'Pressing / laverie'
    if d2 in ('85', '88'): return 'Éducation / services à la personne'
    if d2 in ('10', '11') or d2 in ('13', '14', '15', '16', '18', '20', '22', '23', '25', '31', '32', '33'): return 'Artisanat / fabrication'
    if d2 in ('64', '66', '68', '70'): return 'Holding / activité non précisée'
    if d2 in ('69', '71', '72', '73', '74', '78', '80', '81', '82', '63', '58', '59', '60', '61', '62'): return 'Services aux entreprises'
    if d2 in ('01', '02', '03'): return 'Agriculture'
    return 'Autres services'

GENERIC = {None, 'Holding / activité non précisée', 'Autres services', 'Services aux entreprises', 'Commerce de gros', 'Commerce de détail', 'Artisanat / fabrication'}

def categorie(naf, nom):
    c = by_naf(naf)
    n = _norm(nom)
    # discothèque : souvent codée 56.30Z (débit de boissons) ou 93.29Z
    if re.search(KW[0][1], n): return KW[0][0]
    if c in GENERIC or (c == 'Sport / loisirs / culture' and re.search(r' (bar|pub|lounge|club) ', n)):
        for cat, rx in KW[1:]:
            if re.search(rx, n):
                return cat
    return c or 'Non classé'
