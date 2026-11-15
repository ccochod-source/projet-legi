# Projet Légi

Une application locale pour préparer la vérification juridique d'un site public
ou d'un projet en France. Elle produit un tableau **point / statut / preuve /
référence légale**, puis les informations manquantes. Les trois statuts sont
`conforme`, `manquant` et `a_verifier`, **pour chaque point seulement**.
Ce rapport préparatoire ne constitue ni une certification globale ni un avis juridique.

## Installation sur Mac

1. Téléchargez le ZIP du dépôt (bouton **Code → Download ZIP** sur GitHub) puis
   décompressez-le dans un dossier que vous retrouverez facilement.
2. Installez Python **3.10 ou plus récent** depuis
   <https://www.python.org/downloads/macos/>. Avec Homebrew déjà installé, vous
   pouvez aussi exécuter `brew install python@3.12`.
3. Créez une clé Groq gratuite sur <https://console.groq.com/keys>.
   L'offre gratuite impose des quotas : aucun abonnement payant n'est nécessaire.
4. Pour interroger Légifrance, créez un compte sur <https://piste.gouv.fr>, une
   application et les accès à l'API Légifrance. Gardez son identifiant client et
   son secret. Le projet utilise l'environnement `sandbox` par défaut ; les
   identifiants doivent correspondre à cet environnement. Vous pouvez ignorer
   ces deux clés au lancement : les recherches nécessitant Légifrance resteront
   alors incomplètes et seront signalées.
5. Ouvrez **Terminal** (via Spotlight). Tapez `cd ` avec un espace, glissez le
   dossier décompressé dans le Terminal, puis appuyez sur Entrée.
6. Lancez cette unique commande :

   ```bash
   bash lancer.sh
   ```

Le script vérifie Python, crée `.venv`, installe `requirements.txt`, copie
`.env.example` vers `.env` si nécessaire et demande les clés manquantes.
**Rien ne s'affiche pendant la saisie d'une clé : c'est normal.** Validez avec
Entrée. Les clés sont conservées dans `.env` avec des permissions privées.
Ne partagez jamais ce fichier. Une variable déjà définie dans l'environnement
du Terminal prend le dessus sur `.env`.

Le navigateur s'ouvre sur <http://127.0.0.1:8001>. Gardez le Terminal ouvert.
Pour arrêter : **Ctrl+C**. Pour relancer un autre jour : même commande,
dans le même dossier. En cas de lancement lent, ouvrez l'adresse manuellement.
La première installation nécessite Internet ; les analyses aussi.

## Utilisation

Collez l'URL d'une page publique ou décrivez votre projet en précisant son pays,
son activité et votre question. Cliquez sur **Lancer la vérification**. Évitez
les données personnelles, les identifiants privés et les pages nécessitant une
connexion. Les sites intranet et les adresses privées ne sont pas des cibles
prises en charge par les outils.

L'analyse dure au maximum trois minutes. Le tableau présente les constats et
leurs références cliquables, suivis des limites et des informations à compléter.
Le volet **Outils appelés pendant cette analyse** indique chaque appel et ses
éventuelles erreurs. **Exporter .md** télécharge le même rapport en Markdown.
Chaque nouvelle demande démarre une analyse indépendante.

Une absence sur une page consultée ne démontre pas une absence sur tout le
site. Un outil en erreur, une recherche vide ou une immatriculation ne prouvent
pas la conformité. Les statuts restent des constats préparatoires : vérifiez
l'applicabilité des textes et faites valider les décisions importantes.

## Fonctionnement et garde-fous

- Le navigateur communique seulement avec l'application FastAPI locale.
- L'application est un **client MCP** : elle lance `server.py` en stdio avec le
  même interpréteur Python, initialise une `ClientSession`, puis découvre les
  outils avec `list_tools`. Les arguments demandés par le modèle sont exécutés
  uniquement par `call_tool`, jamais par un accès direct de l'IA aux API métier.
- Le client officiel `groq` utilise `GROQ_MODEL` de `config.py` (par défaut
  `llama-3.3-70b-versatile`). Les appels sont limités à six tours, douze outils
  et 180 secondes, sans nouvelle tentative automatique payante ou cachée.
- Les règles juridiques appartiennent aux outils. Le rapport n'accepte une
  référence que si son couple référence/URL figure dans les `sources` d'un
  outil réussi. Les liens juridiques HTTPS acceptés sont ceux de Légifrance,
  EUR-Lex, CNIL, Service-Public et du ministère de l'Économie. Aucun autre lien
  n'est transformé en référence légale.
- Une preuve doit être une citation retrouvée dans les résultats d'un outil.
  Sinon, ou si la référence manque, le point devient `a_verifier`. Ce contrôle
  vérifie la provenance, pas la justesse du raisonnement juridique du modèle.
- L'interface construit les éléments avec `textContent` ; elle n'exécute pas
  de HTML généré par l'IA. Les clés restent côté serveur. Les erreurs des
  fournisseurs ne sont pas recopiées avec leurs détails internes.

L'application écoute uniquement sur `127.0.0.1`. Elle ne sauvegarde ni historique
ni rapport automatiquement. **Groq reçoit la description saisie et les résultats
filtrés des outils**, nécessaires à l'analyse. Les outils doivent retirer les
données personnelles inutiles avant ce transfert. Le rapport exporté reste
sur votre ordinateur. Le lancement ne déploie aucun site public.

L'alternative Mistral n'est pas implémentée : cette interface utilise Groq.

## Résoudre un problème

| Message | Que faire ? |
| --- | --- |
| Python absent ou ancien | Installez Python 3.10+ puis rouvrez le Terminal. |
| Installation impossible | Vérifiez Internet, puis relancez `bash lancer.sh`. |
| Clé Groq absente | Relancez le script ; il la demande sans l'afficher. |
| Clé Groq invalide ou expirée | Corrigez `GROQ_API_KEY` dans `.env` et redémarrez. Si elle vient du Terminal, corrigez cette variable aussi. |
| Quota Groq atteint (429) | Attendez le renouvellement du quota gratuit, puis réessayez. |
| MCP ne démarre pas | Relancez le script pour installer les dépendances ; vérifiez que `server.py` est présent. |
| Outil en erreur | Consultez son message dans le volet des outils. Vérifiez les clés Légifrance et leur environnement si nécessaire. |
| Limite de tours ou délai dépassé | Réduisez la demande à une page ou une obligation précise. |
| Adresse déjà utilisée | Arrêtez l'ancienne application avec Ctrl+C dans son Terminal. |

## Bonus : brancher le MCP sur Claude Desktop

L'application Groq reste utilisable sans Claude. Si vous utilisez Claude Desktop,
vous pouvez brancher directement les mêmes outils MCP :

1. Lancez une fois `bash lancer.sh` pour installer les dépendances et préparer
   `.env`, puis arrêtez l'application avec Ctrl+C.
2. Dans Claude Desktop, ouvrez **Settings → Developer → Edit Config**. Sur Mac,
   le fichier est `~/Library/Application Support/Claude/claude_desktop_config.json`.
3. Ajoutez ce serveur dans `mcpServers`, en préservant les autres serveurs. Remplacez
   les deux chemins d'exemple par les chemins **absolus** de votre dossier :

   ```json
   {
     "mcpServers": {
       "projet-legi": {
         "command": "/Users/votre-compte/projet-legi/.venv/bin/python",
         "args": ["/Users/votre-compte/projet-legi/server.py"]
       }
     }
   }
   ```

4. Fermez complètement et redémarrez Claude Desktop. Vérifiez que les quatre
   outils de `projet-legi` sont proposés. `config.py` lit automatiquement le
   `.env` situé à côté de `server.py` ; ne recopiez pas les clés dans ce JSON.

Les garde-fous du rapport local sont dans l'application Groq : Claude Desktop
utilise les outils et sa propre interface. Son offre et ses quotas sont distincts.
Pour un autre client MCP compatible HTTP local :
`.venv/bin/python server.py --http` (serveur MCP sur `127.0.0.1:8000/mcp`).

## Tests sans réseau

```bash
.venv/bin/python -m pytest -q
```

Les tests de l'application simulent Groq et les outils MCP : succès, références
inventées, preuves absentes, quotas, clé invalide, lancement MCP impossible et
limites de boucle. Aucun appel réel n'est nécessaire pour ces tests.

## Préparer le ZIP de rendu

Après avoir ajouté la fiche de confiance demandée par le cours à la racine :

```bash
bash scripts/faire_zip.sh
```

Le ZIP horodaté est créé à la racine et contient un dossier `projet-legi/`.
Il exclut `.venv`, `.env` et ses sauvegardes, `__pycache__`, `.pytest_cache`,
`.git`, les autres ZIP, les liens symboliques et les fichiers de clés usuels.
Il conserve `.env.example`, le code, les tests et la documentation.
Vérifiez le contenu avant de rendre le ZIP ; ne placez aucun secret dans un
document ou un fichier source. Ce script emballe la fiche de confiance si elle
est présente, il ne la rédige pas.
