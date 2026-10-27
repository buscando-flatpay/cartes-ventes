# Carte des ventes Sud-Est

Carte des ventes Flatpay (équipes Quentin, Roméo, Jean Barbier), mise à jour automatiquement chaque soir depuis le portail.
Les données (`ventes.enc.json`) sont chiffrées (AES-256-GCM, clé dérivée PBKDF2-SHA256) : la page demande le mot de passe et les déchiffre dans le navigateur.

- `outils/maj.py` : ajoute les ventes relevées sur le portail à `ventes.json` (fichier déchiffré, jamais versionné).
- `outils/crypt.mjs` : chiffre / déchiffre `ventes.enc.json`.
