# Règles juridiques de l'analyse de site

Les règles métier sont ici, **pas dans le prompt de l'IA**. Le fichier
`obligations.json` est lu et validé par `moteur.py`, qui l'applique aux
pages récupérées par `outils/site_web.py`.

## Contenu de `obligations.json`

| Clé | Rôle |
| --- | --- |
| `version`, `verifie_le`, `note` | date et provenance des références légales |
| `obligations` | liste des 21 obligations vérifiées (voir ci-dessous) |
| `signatures` | motifs techniques de détection (liens des pages légales, scripts de traceurs, cookies, outils de consentement, indices de vente en ligne, indices d'éditeur professionnel, numéros SIREN) |

## Schéma d'une obligation

```json
{
  "id": "mentions_siege",
  "theme": "Mentions légales",
  "description": "Adresse du siège social (personne morale) ou adresse de l'entreprise.",
  "reference_legale": {
    "texte": "Loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique (LCEN)",
    "article": "1-1",
    "legifrance_id": "LEGIARTI000049568614",
    "url": "https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000049568614"
  },
  "autres_references": [],
  "verification": "Présence d'une mention « siège social » ou « adresse ».",
  "gravite": "avertissement",
  "applicabilite": "professionnel",
  "detection": {"type": "mots_cles", "pages": ["mentions_legales", "cgv"], "motifs": ["si[èe]ge\\s+social"]}
}
```

- `gravite` : `information`, `avertissement` ou `critique`.
- `applicabilite` : `toujours`, `professionnel` (éditeur professionnel
  détecté : SIREN, RCS, forme de société, vente en ligne), `e_commerce`
  (indice de vente en ligne détecté) ou `traceurs` (traceur ou bandeau détecté).
- `detection.type` :
  - `https` : l'adresse finale commence par `https://` ;
  - `page` : un lien vers la page (`detection.page`) est trouvé et la page est lue ;
  - `mots_cles` : un des `motifs` (expressions régulières, sans casse) est
    trouvé dans les `pages` listées ;
  - `siren` : un SIREN valide est trouvé puis vérifié dans l'API Recherche d'entreprises ;
  - `traceurs` : scripts de traceurs connus et outil de consentement (CMP) dans le HTML initial.
- `legifrance_id` : identifiant LEGIARTI quand il est connu avec certitude,
  sinon chaîne vide (cas du RGPD, texte européen : lien EUR-Lex).
- `autres_references` (facultatif) : références complémentaires, même format.

## Statuts renvoyés

Chaque obligation donne **un** statut, une preuve courte (extrait ou URL,
e-mails et téléphones masqués) et sa référence légale :

- `conforme` : l'élément a été **détecté** (le contenu reste à valider par un humain) ;
- `manquant` : l'obligation s'applique et l'élément n'a pas été trouvé ;
- `a_verifier` : impossible de conclure automatiquement (obligation dont
  l'applicabilité n'est pas établie, page non récupérée, site généré en
  JavaScript, bandeau cookies dont le refus doit être testé à la main...).

Il n'y a **jamais** de verdict global « conforme ».

## Obligations couvertes

| id | Référence |
| --- | --- |
| `https` | RGPD art. 32 |
| `mentions_legales_page`, `mentions_editeur`, `mentions_siege`, `mentions_contact`, `mentions_siren`, `directeur_publication`, `hebergeur` | LCEN art. 1-1 (LEGIARTI000049568614, numérotation issue de la loi SREN 2024) |
| `tva_intracommunautaire` | LCEN art. 19 (LEGIARTI000032236011) |
| `politique_confidentialite_page`, `rgpd_responsable`, `rgpd_finalites`, `rgpd_base_legale`, `rgpd_duree_conservation`, `rgpd_droits`, `rgpd_reclamation_cnil` | RGPD art. 13 |
| `cookies_information`, `cookies_consentement` | Loi Informatique et Libertés art. 82 (LEGIARTI000037813978) |
| `ecommerce_cgv`, `ecommerce_retractation` | Code de la consommation L221-5 (LEGIARTI000053310511) |
| `ecommerce_mediateur` | Code de la consommation L616-1 (LEGIARTI000032224762) |

Les références complémentaires (L111-1, L221-18, L612-1, R616-1 du Code de
la consommation, L441-1 et R123-237 du Code de commerce, LCEN art. 1-2 et 6)
figurent dans `autres_references`.

## Modifier une règle

1. Vérifier l'article sur Légifrance et noter son identifiant LEGIARTI.
2. Modifier `obligations.json` (un `id` unique par obligation).
3. Lancer `pytest -q` : le moteur refuse un fichier mal formé.
