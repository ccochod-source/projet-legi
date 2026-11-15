"""Outil de recherche d'identité d'une entreprise (API Recherche d'entreprises).

Seuls quelques champs publics sont renvoyés (liste blanche). Les dirigeants,
l'adresse complète et les noms d'entrepreneurs individuels ne sont jamais
transmis à l'IA.
"""

import re
from datetime import datetime, timezone
from typing import Any

from clients.entreprises_api import (
    NB_MAX_RESULTATS,
    URL_RECHERCHE,
    rechercher_entreprise,
)
from erreurs import ErreurOutil, convertir_erreur

URL_FICHE = "https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}"
# SIREN de La Poste : seule exception connue à la clé de Luhn.
SIREN_LA_POSTE = "356000000"
ETATS = {"A": "active", "C": "cessée"}
AVERTISSEMENT = (
    "L'inscription d'une entreprise au répertoire ne prouve pas que son site "
    "ou son activité respecte la loi."
)


def _date_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cle_luhn_valide(numero: str) -> bool:
    """Vérifie la clé de Luhn utilisée par les numéros SIREN."""
    total = 0
    for position, chiffre in enumerate(reversed(numero)):
        valeur = int(chiffre)
        if position % 2 == 1:
            valeur *= 2
            if valeur > 9:
                valeur -= 9
        total += valeur
    return total % 10 == 0


def siren_valide(siren: str) -> bool:
    """Un SIREN valide a 9 chiffres et une clé de Luhn correcte."""
    if not re.fullmatch(r"\d{9}", siren):
        return False
    return siren == SIREN_LA_POSTE or cle_luhn_valide(siren)


def normaliser_requete(nom_ou_siren: str) -> tuple[str, str | None]:
    """Renvoie (requête, siren_attendu). Lève ErreurOutil si l'entrée est invalide.

    Une entrée composée uniquement de chiffres (espaces et points tolérés)
    est traitée comme un SIREN (9 chiffres) ou un SIRET (14 chiffres).
    """
    texte = (nom_ou_siren or "").strip()
    if not texte:
        raise ErreurOutil("Indiquez un nom d'entreprise ou un numéro SIREN.")
    chiffres = re.sub(r"[\s.]", "", texte)
    if chiffres.isdigit():
        if len(chiffres) == 14:
            chiffres = chiffres[:9]
        if len(chiffres) != 9 or not siren_valide(chiffres):
            raise ErreurOutil(
                "Numéro SIREN mal formé : 9 chiffres attendus avec une clé valide "
                "(ou 14 chiffres pour un SIRET)."
            )
        return chiffres, chiffres
    return texte, None


def filtrer_entreprise(brut: dict[str, Any]) -> dict[str, Any]:
    """Applique la liste blanche des champs à un résultat brut de l'API."""
    siege = brut.get("siege") or {}
    nature = str(brut.get("nature_juridique") or "")
    nom = brut.get("nom_complet") or brut.get("nom_raison_sociale")
    # Nature juridique « 1xxx » = personne physique : son nom est une donnée personnelle.
    if nature.startswith("1"):
        nom = "Entrepreneur individuel (nom masqué)"
    etat = ETATS.get(brut.get("etat_administratif"), "inconnu")
    return {
        "siren": brut.get("siren"),
        "nom": nom,
        "etat": etat,
        "date_creation": brut.get("date_creation"),
        "activite_principale": brut.get("activite_principale"),
        "commune_siege": siege.get("libelle_commune"),
        "code_postal_siege": siege.get("code_postal"),
    }


async def chercher_entreprises(nom_ou_siren: str, *, client=None) -> dict[str, Any]:
    """Logique commune à l'outil et à l'analyse de site ; lève ErreurOutil."""
    requete, siren_attendu = normaliser_requete(nom_ou_siren)
    donnees = await rechercher_entreprise(requete, NB_MAX_RESULTATS, client=client)
    entreprises = [
        filtrer_entreprise(brut)
        for brut in donnees["results"][:NB_MAX_RESULTATS]
        if isinstance(brut, dict)
    ]
    if siren_attendu:
        # Une recherche par SIREN ne garde que la correspondance exacte.
        entreprises = [e for e in entreprises if e["siren"] == siren_attendu]

    date = _date_iso()
    sources = [{
        "titre": "API Recherche d'entreprises (répertoire Sirene de l'INSEE et RNE)",
        "reference": f"Recherche « {requete} »",
        "url": URL_RECHERCHE,
        "date_recuperation": date,
    }]
    for entreprise in entreprises:
        sources.append({
            "titre": f"Fiche Annuaire des entreprises – SIREN {entreprise['siren']}",
            "reference": f"SIREN {entreprise['siren']}",
            "url": URL_FICHE.format(siren=entreprise["siren"]),
            "date_recuperation": date,
        })

    if not entreprises:
        message = (
            f"Aucune entreprise trouvée pour « {requete} ». "
            "Aucune donnée n'a été inventée."
        )
    elif siren_attendu:
        message = f"Entreprise identifiée par son SIREN {siren_attendu}."
    else:
        total = donnees.get("total_results", len(entreprises))
        message = (
            f"{len(entreprises)} résultat(s) affiché(s) sur {total} : recherche par nom, "
            "homonymies possibles. Confirmez l'entreprise avec son SIREN."
        )
    return {
        "statut": "ok",
        "recherche": requete,
        "recherche_par_siren": siren_attendu is not None,
        "message": message,
        "avertissement": AVERTISSEMENT,
        "entreprises": entreprises,
        "sources": sources,
    }


async def verifier_entreprise(nom_ou_siren: str) -> dict[str, Any]:
    """Recherche une entreprise par nom ou SIREN dans l'API publique.

    Renvoie au plus 5 entreprises avec seulement : SIREN, nom, état
    (active / cessée), date de création, code d'activité, commune et code
    postal du siège. Jamais les dirigeants ni l'adresse complète. Une
    recherche par nom peut renvoyer des homonymes : ce n'est pas une
    identification certaine. Une inscription n'est pas une preuve de
    conformité. Aucun résultat = liste vide, rien n'est inventé.
    """
    try:
        return await chercher_entreprises(nom_ou_siren)
    except ErreurOutil as erreur:
        return convertir_erreur(erreur)
    except Exception:
        return convertir_erreur(ErreurOutil(
            "Erreur inattendue pendant la vérification de l'entreprise."
        ))
