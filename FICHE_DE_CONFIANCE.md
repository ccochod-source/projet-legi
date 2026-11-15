# Fiche de confiance — projet-legi

**Projet étudiant · Aide au repérage juridique, pas un conseil juridique.**

## 1. Pourquoi ce projet ?
Un étudiant ou un porteur de projet web ne sait pas toujours quelles informations légales chercher. À partir d'une URL ou d'une description, projet-legi rassemble des indices publics, des références et les informations restant à vérifier. Il ne délivre **aucun verdict global de conformité** : « conforme » signifie seulement qu'un élément a été détecté.

## 2. Pourquoi ces API et la lecture du site ?
- **Légifrance via PISTE** : consulter le droit français officiel avec OAuth et des sources datées. Les lois (LCEN, cookies) se cherchent dans `LODA_DATE`, les codes dans `CODE_DATE`.
- **API Recherche d'entreprises** : sans clé, rapprocher un nom ou un SIREN du répertoire public. Une immatriculation ne prouve pas la conformité.
- **Lecture HTTP du site** : observer le HTML réellement reçu et les pages légales liées, plutôt que demander à l'IA d'en deviner le contenu.

## 3. Pourquoi exactement quatre outils ?
`analyser_site` observe les pages et applique les règles ; `verifier_entreprise` recherche l'identité publique ; `rechercher_textes_loi` repère des textes ; `consulter_article` lit une version précise d'un article `LEGIARTI`. Chaque outil a un rôle distinct et testable. En retirer un supprimerait une étape ; un cinquième n'est pas nécessaire au périmètre actuel. Séparer recherche et lecture évite de confondre extrait et article complet.

## 4. Quelles actions, quels refus ?
Les outils effectuent des lectures publiques, pas de modification du site. Ils renvoient des données sourcées ou une erreur explicite. Le client web refuse les protocoles autres que HTTP/HTTPS, les URL avec identifiants et les destinations privées, y compris après redirection. Taille, temps et nombre de pages sont bornés. Une page absente, illisible ou trop courte ne prouve pas une mention manquante : le résultat reste `a_verifier`. Les e-mails et téléphones détectés dans les preuves sont masqués et les dirigeants ne sont pas renvoyés par la recherche d'entreprises. L'application refuse les outils non autorisés et dégrade les preuves ou références non retrouvées dans les résultats.

## 5. Pourquoi cette architecture ?
**IA Groq ↔ application locale FastAPI ↔ serveur MCP en stdio ↔ API et sites publics.** Groq propose les appels ; l'application les contrôle et le serveur exécute les outils. Cette séparation permet de travailler en parallèle et de tester chaque partie. Les règles sont dans `regles/` ; les clés sont chargées depuis `.env` (ou l'environnement), jamais envoyées au navigateur ni incluses dans le ZIP. **Local ne signifie pas hors ligne** : la demande et les résultats d'outils sont transmis à Groq. Ne pas saisir de secrets ni de données sensibles.

## Garde-fous vérifiés et limites
**245 tests réussis** avec `.venv/bin/pytest -q` ; un avertissement de dépréciation Starlette/httpx. Exemples réels (réseau simulé, pas une certification) :
- `tests/test_site_web.py` : `test_redirection_vers_metadata_refusee`, `test_lisibilite_page_confidentialite`, `test_blocage_lecture_automatisee` — réseau privé, lecture incertaine, erreur 403.
- `tests/test_legifrance.py` : `test_oauth_basic_formulaire_et_cache` — authentification et cache du jeton.
- `tests/test_entreprises.py` : `test_liste_blanche_sans_dirigeants_ni_adresse` — données renvoyées limitées.
- `tests/test_app.py` : `test_refus_des_inventions`, `test_erreur_outil_ne_devient_pas_une_conformite`, `test_zip_exclut_les_fichiers_prives_et_caches` — preuves, erreurs et archive.

**Limites connues :** JavaScript non exécuté ; six pages maximum ; certains sites bloquent la lecture automatisée (403) : coller plutôt le texte légal dans la discussion. Seul le **sandbox Légifrance a été vérifié**, même si la configuration prévoit la production. Le RGPD est un texte de l'UE à consulter sur **EUR-Lex**, pas dans ces fonds Légifrance. Les mots-clés et l'IA peuvent se tromper : vérifier les versions, l'applicabilité et les conclusions avec une personne compétente.
