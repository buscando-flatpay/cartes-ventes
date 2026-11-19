# Carte des ventes Sud-Est

Carte des ventes Flatpay (équipes Quentin, Roméo, Jean Barbier), mise à jour automatiquement chaque soir depuis le portail.
Les données (`ventes.enc.json`) sont chiffrées (AES-256-GCM, clé dérivée PBKDF2-SHA256) : la page demande le mot de passe et les déchiffre dans le navigateur.

- `outils/maj.py` : ajoute les ventes relevées sur le portail à `ventes.json` (fichier déchiffré, jamais versionné).
- `outils/crypt.mjs` : chiffre / déchiffre `ventes.enc.json`.

## Jones (agent quotidien, 8h15)
- `outils/jones/releve.js` : relevé d'une équipe dans l'onglet du portail (ventes + RDV, adresse et produit lus sur la fiche du RDV, géocodage api-adresse, NAF si SIREN valide). Reprise automatique (« SUITE » / « FINI »), cache dans le navigateur.
- `outils/jones/fusion.py` : ajoute les nouvelles ventes à `ventes.json` et met à jour les RDV (jours ≥ `rdvcut` remplacés à chaque passage, sans double comptage), écrit un compte rendu JSON.


## Sylvain (agent quotidien, 8h45)
- `outils/sylvain/releve.js` : liste des RDV de l'équipe sur le portail (lecture seule).
- `outils/sylvain/analyse.py` : RDV par commercial et par jour sur 3 jours (hors reprogrammés et annulés), nombre de META, RDV chez des SIREN déjà clients (d'après la carte).

## Hugues (agent quotidien, 8h00)
- `outils/hugues/releve.js` : lecture du Power BI « Field Sales Report - TM - FR » (TM Dash et Sales Performance), en lecture seule.
- `outils/hugues/analyse.py` : compilation du mois par commercial (installations, ventes, OG, POS), chiffres de la veille par différence avec le passage précédent, détection de panne (installations du mois à 0).
- `outils/hugues/segments.js` règle les segments Team et Period avant chaque lecture (`window.SEGMENTS={equipe, annee, mois}`) ; ne jamais utiliser « Rétablir les valeurs par défaut ».
- Changement de mois : au premier passage d'un nouveau mois, Hugues relit le mois précédent (`analyse.py … --cloture AAAA-MM`), fige la compilation définitive dans `archives_mois/AAAA-MM` (champ `hugues_final`), puis repart de zéro (`--fin-mois` pour garder la « veille » du dernier jour).

## Ruzard (archives, vendredi 22h + dernier jour du mois 22h)
- Tâche dans le cloud : lit `qg/statut` dans la base du QG et range des archives (pas besoin du Mac).
- `outils/ruzard/archive.py semaine|mois|index …` : `archives_semaines/AAAA-Wnn` (chiffres de la semaine par commercial = cumul du vendredi − cumul du vendredi précédent), `archives_mois/AAAA-MM` (compilation provisoire), `archives/index` (liste pour le QG).

## Sylvie (mails, tous les soirs 19h)
- `outils/sylvie/releve.js` : lecture SEULE d'Outlook web (outlook.cloud.microsoft) dans Chrome — recherches dans la boîte, lecture de la liste des résultats (expéditeur, date, sujet, aperçu, dossier), sans jamais ouvrir un mail.
- `outils/sylvie/analyse.py candidats|rapport …` : filtre (gens de Flatpay, rétention, support@flatpay.fr, RH), regroupe par fil, repère les fils déjà répondus ; Sylvie décide ensuite ce qui demande une intervention.
