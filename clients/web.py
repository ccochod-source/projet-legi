"""Récupération sécurisée des pages web publiques.

Garde-fous (protection contre les requêtes vers le réseau interne) :
- seuls les schémas http et https sont acceptés, sans identifiants dans l'URL ;
- le nom de domaine est résolu (DNS) et toute adresse IP privée, locale,
  réservée ou de « metadata » cloud est refusée ; la connexion se fait
  ensuite vers l'IP vérifiée (pas de seconde résolution DNS) ;
- les redirections sont suivies à la main et revérifiées à chaque étape ;
- taille, délai et nombre de redirections sont bornés ;
- un User-Agent explicite annonce l'outil.
"""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import httpx

import config
from erreurs import ErreurOutil

USER_AGENT = (
    "projet-legi/0.1 (analyse automatique de conformite ; projet etudiant ; "
    "+https://github.com/ccochod-source/projet-legi)"
)
TAILLE_MAX_OCTETS = 2_000_000
MAX_REDIRECTIONS = 5
TYPES_ACCEPTES = ("text/html", "application/xhtml+xml")

Resolveur = Callable[[str, int], Awaitable[list[str]]]


async def resoudre_dns(hote: str, port: int) -> list[str]:
    """Renvoie toutes les adresses IP associées à un nom d'hôte."""
    boucle = asyncio.get_running_loop()
    try:
        infos = await boucle.getaddrinfo(hote, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ErreurOutil(f"Nom de domaine introuvable : {hote}.") from None
    return sorted({info[4][0] for info in infos})


def ip_publique(adresse: str) -> bool:
    """Vrai seulement pour une adresse IP publique routable sur Internet."""
    try:
        ip = ipaddress.ip_address(adresse.split("%")[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    # is_global exclut privé, loopback, lien local (169.254.169.254), réservé...
    return ip.is_global and not ip.is_multicast


def valider_url(url: str) -> httpx.URL:
    """Vérifie la forme de l'URL ; lève ErreurOutil si elle est refusée."""
    try:
        adresse = httpx.URL((url or "").strip())
    except (httpx.InvalidURL, TypeError):
        raise ErreurOutil("Adresse web invalide.") from None
    if adresse.scheme not in {"http", "https"}:
        raise ErreurOutil("Adresse refusée : seuls http:// et https:// sont acceptés.")
    if not adresse.host:
        raise ErreurOutil("Adresse web invalide : nom de domaine manquant.")
    if adresse.userinfo:
        raise ErreurOutil("Adresse refusée : identifiants interdits dans l'URL.")
    if adresse.host.lower() in {"localhost", "localhost.localdomain"} or adresse.host.lower().endswith(".localhost"):
        raise ErreurOutil("Adresse refusée : destination locale.")
    return adresse


async def _ip_verifiee(adresse: httpx.URL, resoudre: Resolveur) -> str:
    """Résout l'hôte et renvoie une IP publique ; refuse s'il y en a une privée."""
    port = adresse.port or (443 if adresse.scheme == "https" else 80)
    ips = await resoudre(adresse.host, port)
    if not ips:
        raise ErreurOutil(f"Nom de domaine introuvable : {adresse.host}.")
    if not all(ip_publique(ip) for ip in ips):
        raise ErreurOutil(
            "Adresse refusée : le site pointe vers une adresse privée, locale "
            "ou réservée."
        )
    return ips[0]


def _url_vers_ip(adresse: httpx.URL, ip: str) -> httpx.URL:
    """Remplace le nom d'hôte par l'IP déjà vérifiée."""
    return adresse.copy_with(host=ip)


async def _telecharger(
    client: httpx.AsyncClient, url_demandee: str, resoudre: Resolveur
) -> dict[str, Any]:
    adresse = valider_url(url_demandee)
    for _ in range(MAX_REDIRECTIONS + 1):
        ip = await _ip_verifiee(adresse, resoudre)
        en_tetes = {
            "User-Agent": USER_AGENT,
            "Host": adresse.netloc.decode("ascii"),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }
        extensions = {"sni_hostname": adresse.host} if adresse.scheme == "https" else {}
        async with client.stream(
            "GET", _url_vers_ip(adresse, ip), headers=en_tetes, extensions=extensions
        ) as reponse:
            if reponse.is_redirect:
                cible = reponse.headers.get("Location", "")
                if not cible:
                    raise ErreurOutil("Redirection invalide renvoyée par le site.")
                adresse = valider_url(str(adresse.join(cible)))
                continue
            if reponse.status_code >= 400:
                raise ErreurOutil(
                    f"Le site a répondu avec le code HTTP {reponse.status_code} "
                    f"pour {adresse}."
                )
            type_contenu = reponse.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if type_contenu not in TYPES_ACCEPTES:
                raise ErreurOutil(f"{adresse} n'est pas une page HTML.")
            longueur = reponse.headers.get("Content-Length", "")
            if longueur.isdigit() and int(longueur) > TAILLE_MAX_OCTETS:
                raise ErreurOutil("Page trop volumineuse pour être analysée.")
            morceaux = []
            total = 0
            async for morceau in reponse.aiter_bytes():
                total += len(morceau)
                if total > TAILLE_MAX_OCTETS:
                    raise ErreurOutil("Page trop volumineuse pour être analysée.")
                morceaux.append(morceau)
            contenu = b"".join(morceaux).decode(reponse.encoding or "utf-8", errors="replace")
            # Seuls les noms des cookies sont gardés, jamais leurs valeurs.
            cookies = sorted({
                valeur.split("=", 1)[0].strip()
                for valeur in reponse.headers.get_list("Set-Cookie")
                if "=" in valeur
            })
            return {
                "url": str(adresse),
                "url_demandee": url_demandee,
                "code_http": reponse.status_code,
                "type_contenu": type_contenu,
                "contenu": contenu,
                "cookies_deposes": cookies,
                "date_recuperation": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
    raise ErreurOutil("Trop de redirections : page abandonnée.")


async def recuperer_page(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    resoudre: Resolveur = resoudre_dns,
) -> dict[str, Any]:
    """Renvoie url, contenu, type_contenu, cookies_deposes et date_recuperation.

    Lève ErreurOutil (message clair) en cas de refus, de délai dépassé,
    de page trop lourde, de code HTTP d'erreur ou de problème réseau.
    """
    client_cree = client is None
    if client is None:
        client = httpx.AsyncClient(
            follow_redirects=False, timeout=config.TIMEOUT_S, trust_env=False
        )
    try:
        return await asyncio.wait_for(
            _telecharger(client, url, resoudre), timeout=config.TIMEOUT_S
        )
    except asyncio.TimeoutError:
        raise ErreurOutil("Délai dépassé : le site met trop de temps à répondre.") from None
    except httpx.TimeoutException:
        raise ErreurOutil("Délai dépassé : le site met trop de temps à répondre.") from None
    except httpx.ConnectError:
        raise ErreurOutil("Impossible de se connecter au site (réseau ou certificat).") from None
    except httpx.HTTPError:
        raise ErreurOutil("Erreur réseau pendant la récupération de la page.") from None
    finally:
        if client_cree:
            await client.aclose()
