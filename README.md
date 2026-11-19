# Carte des ventes Sud-Est

Carte des ventes Flatpay (équipes Quentin, Roméo, Jean Barbier), mise à jour automatiquement chaque soir depuis le portail.
Les données (`ventes.enc.json`) sont chiffrées (AES-256-GCM, clé dérivée PBKDF2-SHA256) : la page demande le mot de passe et les déchiffre dans le navigateur.

- `outils/maj.py` : ajoute les ventes relevées sur le portail à `ventes.json` (fichier déchiffré, jamais versionné).
- `outils/crypt.mjs` : chiffre / déchiffre `ventes.enc.json`.

## Jones (agent quotidien, 8h15)
- `outils/jones/releve.js` : relevé d'une équipe dans l'onglet du portail (ventes + RDV, adresse et produit lus sur la fiche du RDV, géocodage api-adresse, NAF si SIREN valide). Reprise automatique (« SUITE » / « FINI »), cache dans le navigateur.
- `outils/jones/fusion.py` : ajoute les nouvelles ventes à `ventes.json` et met à jour les RDV (jours ≥ `rdvcut` remplacés à chaque passage, sans double comptage), écrit un compte rendu JSON.
