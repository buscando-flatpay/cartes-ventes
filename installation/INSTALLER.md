# Installer Igor et Sylvie pour un manager Flatpay

Ces instructions s'adressent à Claude, dans le compte du manager qui veut ses propres agents.
Elles reproduisent le QG de Quentin Dicharry (équipe Var – Marseille), réduit à Igor et Sylvie.
Réponds en français, explique chaque étape en une phrase, et demande au manager ce qui te manque.

**Règles pendant toute l'installation**
- Tu travailles uniquement dans le compte et le navigateur du manager. Tu ne saisis jamais de mot de passe ;
  s'il faut se connecter (portail Flatpay, Slack, Outlook), c'est lui qui le fait.
- Portail Flatpay : lecture seule. Slack : pendant l'installation tu ouvres des conversations pour lire leur
  adresse, tu n'écris aucun message. Outlook : tu n'y vas pas pendant l'installation.
- Les noms et identifiants de son équipe vont dans SON QG (document `qg/config`), jamais dans ce dépôt public.

## Étape 1 · Vérifier les prérequis
Vérifie que tu as : les outils Claude in Chrome (`mcp__claude-in-chrome__*`), les outils d'artifact
(`mcp__claude-artifacts__*` : publish_files, declare_capabilities, db_get, db_write, get_artifact) et les tâches
planifiées (`create_trigger`, `update_trigger`). Charge-les avec ToolSearch. S'il en manque, dis au manager ce
qu'il doit activer (appli Claude ouverte sur son ordinateur, extension Claude in Chrome connectée) et arrête.
Clone le dépôt : `git clone --depth 1 https://github.com/buscando-flatpay/cartes-ventes /tmp/installation`.

## Étape 2 · Les informations du manager
Demande-lui en une seule fois :
1. son prénom et son nom, exactement comme ils apparaissent dans Slack ;
2. son adresse e-mail Flatpay ;
3. le nom de son équipe ou de sa région (ex. « Lyon ») ;
4. la liste de ses commerciaux (prénom nom, comme dans Slack) et ceux à exclure de ses agents.

## Étape 3 · Les identifiants portail de ses commerciaux
Dans Chrome (nouvel onglet), ouvre https://portal.flatpay.fr/awaiting-installations.
Demande au manager de cocher lui-même ses commerciaux dans le filtre des commerciaux de cette page, puis de te
dire quand c'est fait. Lis alors l'adresse de la page : le paramètre `salesPersons=` contient les identifiants
(séparés par des virgules). Retire ceux des commerciaux exclus s'il les a cochés. Vérifie avec lui le nombre
d'installations affiché. Ce sont les `portail_sales`.

## Étape 4 · Les conversations Slack
Ouvre https://app.slack.com/client dans le même onglet et attends 10 secondes.
Pour lui-même puis pour chaque commercial :
1. `javascript_tool` : `document.activeElement.blur()` ;
2. touche `cmd+k` (ctrl+k sous Windows), attends 1 s, vérifie par `javascript_tool` que
   `document.activeElement.getAttribute('aria-label') === 'Query'` (sinon recommence une fois) ;
3. tape le nom, attends 2 s, fais une capture zoomée de la liste : choisis le résultat qui est la conversation
   privée avec cette seule personne (« Prénom Nom · @Prénom Nom », ou « (you) » pour lui-même), jamais une
   conversation de groupe ;
4. Entrée, attends 2 s, puis lis l'adresse : `https://app.slack.com/client/<slack_equipe>/<id>`.
Tu ne tapes rien dans le champ de message. Récapitule le tableau nom → id au manager.

## Étape 5 · Créer son QG
1. `cp /tmp/installation/installation/qg_modele.html /tmp/qg/index.html` puis remplace `{{PRENOM}}` par son prénom et
   `{{REGION}}` par son équipe (sed). Laisse `{{TRIG_…}}` pour l'instant.
2. Publie avec `publish_files` (nouvel artifact, titre « Le QG · agents de <Prénom> », icône « MapPin »).
   Note le slug et le lien.
3. `declare_capabilities` sur ce slug :
   `{"db":{"rules":[{"path":"","read":"admin","write":"owner"}]},"mcp":{"servers":[{"server":"Claude Code Remote","tools":["fire_trigger"]}]}}`
4. `db_write` (sans ifVersion, ce sont des créations) :
   - `qg/config` = `{"nom":…,"email":…,"region":…,"portail_sales":"…","exclus":[…],"slack_equipe":"…","slack_moi":"…","slack_dm":{"Prénom Nom":"D…",…},"rh_expediteurs":[]}`
   - `qg/reglages` = `{"slack_essai":true,"note":"slack_essai true = les messages de Sylvie x Igor partent dans l'espace perso du manager uniquement"}`
   - `qg/statut` = `{"agents":{},"historique":{},"v":1}`

## Étape 6 · Créer les trois tâches
Pour chaque fichier de `/tmp/installation/installation/taches/` (igor.txt, sylvie_slack.txt, sylvie_mails.txt) :
remplace `{{COMMUN}}` par le contenu de `commun.txt`, puis `{{PRENOM}}`, `{{REGION}}`, `{{SLUG_QG}}`, `{{LIEN_QG}}`.
Vérifie qu'il ne reste aucun `{{` dans le texte. Puis `create_trigger` avec `requires_local_device: true`,
`initiation: "human_request"`, `notifications: {"push": true}` :
- « Igor — installations en direct (à la demande) » : prompt = igor.txt, sans horaire ;
- « Sylvie — point installations aux commerciaux (Slack, à la demande) » : prompt = sylvie_slack.txt, sans horaire ;
- « Sylvie — mails du soir (19h) » : prompt = sylvie_mails.txt, `cron_expression: "CRON_TZ=Europe/Paris 0 19 * * *"`
  (seulement si le manager veut le tri des mails ; sinon ne la crée pas et retire le bouton de tri dans la page).
Note les trois identifiants `trig_…`. Dis au manager quel réglage d'approbation chaque tâche a reçu ; si ses
exécutions demandent une approbation, explique-lui comment passer la tâche en « Automatically approve » dans
ses réglages (sans ça, les tâches lancées depuis le QG s'arrêtent en attendant son accord).

## Étape 7 · Brancher les boutons du QG
Dans /tmp/qg/index.html remplace `{{TRIG_IGOR}}`, `{{TRIG_SYLVIE_SLACK}}` et `{{TRIG_SYLVIE_MAILS}}` (chaîne vide si
pas de tri des mails). `get_artifact` pour la version, puis `publish_files` sur le même slug avec `base_version`.

## Étape 8 · Premier essai, avec lui
1. Donne-lui le lien du QG et demande-lui de l'ouvrir, de cliquer sur Igor puis « Lancer la filature ».
2. Quand Igor a fini (5 à 10 minutes), il clique sur le bouton rose « Sylvie : envoyer le point aux commerciaux ».
   Mode essai : tous les messages arrivent dans son espace perso Slack.
3. Il relit ; quand ça lui va, il décoche « Mode essai » dans le panneau d'Igor.
Termine par un récapitulatif : lien du QG, tâches créées, mode essai actif, et ce qu'il doit garder ouvert
(ordinateur allumé, appli Claude, Chrome connecté au portail, à Slack et à Outlook).
