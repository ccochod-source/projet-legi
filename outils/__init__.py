"""Contrat commun des quatre outils MCP asynchrones.

Chaque outil retourne un dictionnaire. Succès : {"statut": "ok", ...}
avec ses champs de données et "sources", liste de dictionnaires contenant
"titre", "reference", "url", "date_recuperation" (date ISO 8601).
Échec : {"statut": "erreur", "erreur": "<message clair>"}.
Aucune donnée, référence ni conclusion juridique ne doit être inventée.
Les entrées invalides et échecs des services seront des ErreurOutil converties
via convertir_erreur ; les clients restent indépendants du protocole MCP.

Champs de succès réservés : rechercher_textes_loi -> textes (liste),
consulter_article -> article (objet), verifier_entreprise -> entreprises
(liste), analyser_site -> analyse (objet). Les listes vides sont des succès
sans résultat, non une autorisation d'inventer des données.
"""
