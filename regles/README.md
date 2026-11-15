# Schéma des obligations

`obligations.json` reste vide : aucune règle juridique n'est inventée.
Chaque entrée future respectera le schéma illustratif suivant (ce n'est
pas une obligation réelle) :

```json
{
  "id": "identifiant_unique",
  "theme": "thème documenté",
  "description": "obligation à sourcer",
  "reference_legale": {
    "texte": "nom du texte officiel",
    "article": "numéro de l'article",
    "legifrance_id": "identifiant officiel facultatif"
  },
  "verification": "critère de vérification observable",
  "gravite": "information"
}
```

`gravite` : `information`, `avertissement` ou `critique`.
`legifrance_id` est facultatif ; tous les autres champs sont requis.
