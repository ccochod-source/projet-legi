"""Tests sans réseau de analyser_site, du client web et du moteur de règles."""

import asyncio
import json

import httpx
import pytest
from bs4 import BeautifulSoup

import clients.web as web
import outils.site_web as site_web
from erreurs import ErreurOutil
from outils.site_web import (
    analyser_site,
    analyser_traceurs,
    detecter_e_commerce,
    trouver_liens_legaux,
)
from regles.moteur import STATUTS, _valider, charger_regles, masquer_donnees

CLES_SOURCE = {"titre", "reference", "url", "date_recuperation"}


async def dns_public(hote, port):
    return ["93.184.216.34"]


def recuperer(url, gestionnaire, resoudre=dns_public):
    async def lancer():
        async with httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire), follow_redirects=False) as client:
            return await web.recuperer_page(url, client=client, resoudre=resoudre)
    return asyncio.run(lancer())


def page_html(corps="<p>Bonjour</p>", code=200, en_tetes=None):
    return httpx.Response(code, content=f"<html><body>{corps}</body></html>".encode(),
                          headers={"Content-Type": "text/html; charset=utf-8", **(en_tetes or {})})


def jamais_appele(requete):
    raise AssertionError(f"aucune requête attendue vers {requete.url}")


# --- Garde-fous du client web ----------------------------------------------

@pytest.mark.parametrize("ip", [
    "127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.169.254",
    "0.0.0.0", "100.64.0.1", "224.0.0.1", "::1", "fe80::1", "fd00::1", "::ffff:127.0.0.1",
])
def test_ip_non_publiques_refusees(ip):
    assert not web.ip_publique(ip)


@pytest.mark.parametrize("ip", ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111"])
def test_ip_publiques_acceptees(ip):
    assert web.ip_publique(ip)


@pytest.mark.parametrize("url, message", [
    ("file:///etc/passwd", "http:// et https://"),
    ("ftp://exemple.fr", "http:// et https://"),
    ("http://localhost:8000", "locale"),
    ("http://admin.localhost", "locale"),
    ("http://user:mdp@exemple.fr", "identifiants"),
])
def test_urls_refusees_sans_requete(url, message):
    with pytest.raises(ErreurOutil, match=message):
        recuperer(url, jamais_appele)


@pytest.mark.parametrize("url", ["http://169.254.169.254/latest/meta-data", "http://10.0.0.1", "http://[::1]/"])
def test_ip_litterales_privees_refusees(url):
    async def dns_reel(hote, port):
        return [hote]
    with pytest.raises(ErreurOutil, match="privée"):
        recuperer(url, jamais_appele, resoudre=dns_reel)


def test_domaine_resolu_vers_ip_privee_refuse():
    async def dns_piege(hote, port):
        return ["93.184.216.34", "10.0.0.5"]
    with pytest.raises(ErreurOutil, match="privée"):
        recuperer("https://piege.exemple", jamais_appele, resoudre=dns_piege)


def test_redirection_vers_metadata_refusee():
    async def dns(hote, port):
        return [hote] if hote[0].isdigit() else ["93.184.216.34"]

    appels = []

    def gestionnaire(requete):
        appels.append(str(requete.url))
        return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest/meta-data"})

    with pytest.raises(ErreurOutil, match="privée"):
        recuperer("https://exemple.fr", gestionnaire, resoudre=dns)
    assert len(appels) == 1 and "169.254" not in appels[0]


def test_trop_de_redirections():
    with pytest.raises(ErreurOutil, match="redirections"):
        recuperer("https://exemple.fr", lambda r: httpx.Response(301, headers={"Location": "/boucle"}))


def test_redirection_suivie_et_user_agent():
    requetes = []

    def gestionnaire(requete):
        requetes.append(requete)
        if requete.url.path == "/":
            return httpx.Response(301, headers={"Location": "https://www.exemple.fr/accueil",
                                                "Set-Cookie": "_ga=GA1.2.secret; Path=/"})
        return page_html(en_tetes={"Set-Cookie": "session=abc; Path=/"})

    page = recuperer("https://exemple.fr/", gestionnaire)
    assert page["url"] == "https://www.exemple.fr/accueil"
    assert page["cookies_deposes"] == ["_ga", "session"]
    assert "secret" not in json.dumps(page["cookies_deposes"])
    assert all(r.url.host == "93.184.216.34" for r in requetes)
    assert requetes[1].headers["Host"] == "www.exemple.fr"
    assert requetes[0].headers["User-Agent"].startswith("projet-legi/")


def test_taille_bornee(monkeypatch):
    monkeypatch.setattr(web, "TAILLE_MAX_OCTETS", 100)
    with pytest.raises(ErreurOutil, match="volumineuse"):
        recuperer("https://exemple.fr", lambda r: page_html("x" * 500))


def test_contenu_non_html_refuse():
    reponse = httpx.Response(200, content=b"%PDF", headers={"Content-Type": "application/pdf"})
    with pytest.raises(ErreurOutil, match="HTML"):
        recuperer("https://exemple.fr", lambda r: reponse)


def test_code_http_erreur():
    with pytest.raises(ErreurOutil, match="403"):
        recuperer("https://exemple.fr", lambda r: httpx.Response(403))


def test_erreur_de_connexion():
    def gestionnaire(requete):
        raise httpx.ConnectError("refus", request=requete)
    with pytest.raises(ErreurOutil, match="Impossible de se connecter"):
        recuperer("https://exemple.fr", gestionnaire)


# --- Détections ------------------------------------------------------------

def test_liens_legaux_priorite_au_motif_le_plus_fiable():
    html = """
      <a href="/protection-des-donnees-dans-le-monde">La protection des données dans le monde</a>
      <a href="/donnees-personnelles">Données personnelles</a>
      <a href="/mentions">Mentions légales</a>
      <a href="/cgv">CGV</a>
      <a href="mailto:contact@exemple.fr">Contact</a>
    """
    liens = trouver_liens_legaux(BeautifulSoup(html, "html.parser"), "https://exemple.fr/",
                                 charger_regles()["signatures"]["liens"])
    assert liens["confidentialite"] == "https://exemple.fr/donnees-personnelles"
    assert liens["mentions_legales"] == "https://exemple.fr/mentions"
    assert liens["cgv"] == "https://exemple.fr/cgv"


def test_liens_legaux_avec_balise_base():
    html = '<base href="/fr/"><a href="mentions-legales">Mentions légales</a>'
    liens = trouver_liens_legaux(BeautifulSoup(html, "html.parser"), "https://exemple.fr/accueil",
                                 charger_regles()["signatures"]["liens"])
    assert liens["mentions_legales"] == "https://exemple.fr/fr/mentions-legales"


def test_traceur_bloque_seulement_si_type_non_executable():
    signatures = charger_regles()["signatures"]
    html = """
      <script data-category="analytics" src="https://connect.facebook.net/fbevents.js"></script>
      <script type="text/plain" data-cookieconsent="statistics" src="https://static.hotjar.com/c/hotjar.js"></script>
    """
    traceurs, cmp = analyser_traceurs(html, [], signatures)
    assert traceurs["actifs"] == ["Meta Pixel (Facebook)"]
    assert traceurs["bloques"] == ["Hotjar"]


def test_e_commerce_sans_faux_positif_sur_le_texte():
    motifs = charger_regles()["signatures"]["e_commerce"]
    assert detecter_e_commerce("<p>Hébergez votre site PrestaShop ou Magento</p>", motifs) == []
    assert detecter_e_commerce('<a href="/panier">Mon panier</a>', motifs)


def test_masquage_email_et_telephone():
    texte = masquer_donnees("Contact : jean.dupont@exemple.fr ou 06 12 34 56 78")
    assert "jean.dupont" not in texte and "06 12" not in texte


# --- Règles -----------------------------------------------------------------

def test_regles_ont_une_reference_legale():
    regles = charger_regles()
    assert len(regles["obligations"]) >= 15
    for obligation in regles["obligations"]:
        reference = obligation["reference_legale"]
        assert reference["texte"] and reference["article"] and reference["url"]
        assert reference.get("legifrance_id", "").startswith(("LEGIARTI", "LEGITEXT", ""))


def test_regles_invalides_refusees():
    with pytest.raises(ErreurOutil):
        _valider({"obligations": [{"id": "x"}]})


# --- Analyse complète (réseau simulé) ---------------------------------------

ACCUEIL = """
<html><head>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-123"></script>
</head><body>
  <a href="/mentions-legales">Mentions légales</a>
  <a href="/confidentialite">Politique de confidentialité</a>
  <a href="/cgv">Conditions générales de vente</a>
  <button>Ajouter au panier</button>
  <p>{TEXTE}</p>
</body></html>
""".replace("{TEXTE}", "Bienvenue dans notre boutique de produits artisanaux. " * 10)
MENTIONS = """<p>Site édité par Exemple SAS au capital de 10 000 euros, siège social : Paris.
RCS Paris 433 891 850. Contact : jean.dupont@exemple.fr, 01 23 45 67 89.
Directeur de la publication : la présidente. Hébergeur : Hébergeur SA.</p>"""
CONFIDENTIALITE = "<p>Le responsable du traitement est Exemple SAS. Vous disposez d'un droit d'accès.</p>"
CGV = "<p>Droit de rétractation de 14 jours. Médiateur de la consommation : CM2C.</p>"


def installer_faux_site(monkeypatch, accueil=ACCUEIL, entreprise_etat="active"):
    pages = {
        "https://exemple.fr/": accueil,
        "https://exemple.fr/mentions-legales": MENTIONS,
        "https://exemple.fr/confidentialite": CONFIDENTIALITE,
        "https://exemple.fr/cgv": CGV,
    }
    demandes = []

    async def faux_recuperer(url, **kwargs):
        demandes.append(url)
        if url not in pages:
            raise ErreurOutil(f"Le site a répondu avec le code HTTP 404 pour {url}.")
        return {"url": url, "url_demandee": url, "code_http": 200, "type_contenu": "text/html",
                "contenu": pages[url], "cookies_deposes": [], "date_recuperation": "2026-11-15T15:00:00+00:00"}

    async def faux_chercher(siren, **kwargs):
        return {"statut": "ok", "entreprises": [{
            "siren": siren, "nom": "EXEMPLE", "etat": entreprise_etat, "date_creation": "2000-01-01",
            "activite_principale": "62.01Z", "commune_siege": "PARIS", "code_postal_siege": "75001"}],
            "sources": [{"titre": "API", "reference": f"SIREN {siren}", "url": "https://api", "date_recuperation": "2026-11-15"}]}

    monkeypatch.setattr(site_web, "recuperer_page", faux_recuperer)
    monkeypatch.setattr(site_web, "chercher_entreprises", faux_chercher)
    return demandes


def par_id(resultat):
    return {v["id"]: v for v in resultat["analyse"]["verifications"]}


def test_analyse_complete(monkeypatch):
    demandes = installer_faux_site(monkeypatch)
    resultat = asyncio.run(analyser_site("exemple.fr/"))
    assert resultat["statut"] == "ok"
    analyse = resultat["analyse"]
    assert len(demandes) <= site_web.MAX_PAGES
    assert analyse["vente_en_ligne_detectee"] is True
    assert analyse["entreprise_verifiee"]["siren"] == "433891850"

    for verification in analyse["verifications"]:
        assert verification["statut"] in STATUTS
        assert verification["preuve"]
        assert verification["reference"]["texte"] and verification["reference"]["article"]

    points = par_id(resultat)
    assert points["mentions_legales_page"]["statut"] == "conforme"
    assert points["mentions_siren"]["statut"] == "conforme"
    assert points["hebergeur"]["statut"] == "conforme"
    assert points["ecommerce_mediateur"]["statut"] == "conforme"
    assert points["cookies_consentement"]["statut"] == "manquant"
    assert points["rgpd_reclamation_cnil"]["statut"] == "manquant"
    assert points["cookies_consentement"]["reference"]["article"] == "82"

    texte = json.dumps(resultat, ensure_ascii=False)
    assert "jean.dupont" not in texte and "01 23 45" not in texte
    assert "verdict" not in analyse and set(analyse["resume"]) == set(STATUTS)
    assert resultat["sources"] and all(set(s) == CLES_SOURCE for s in resultat["sources"])


def test_cmp_detectee_donne_a_verifier(monkeypatch):
    accueil = ACCUEIL.replace("</head>", '<script src="https://cdn.cookielaw.org/otSDKStub.js"></script></head>')
    installer_faux_site(monkeypatch, accueil=accueil)
    assert par_id(asyncio.run(analyser_site("https://exemple.fr/")))["cookies_consentement"]["statut"] == "a_verifier"


def test_google_tag_manager_seul_donne_a_verifier(monkeypatch):
    accueil = ACCUEIL.replace("gtag/js?id=G-123", "gtm.js?id=GTM-123")
    installer_faux_site(monkeypatch, accueil=accueil)
    assert par_id(asyncio.run(analyser_site("https://exemple.fr/")))["cookies_consentement"]["statut"] == "a_verifier"


def test_entreprise_cessee_donne_a_verifier(monkeypatch):
    installer_faux_site(monkeypatch, entreprise_etat="cessée")
    assert par_id(asyncio.run(analyser_site("https://exemple.fr/")))["mentions_siren"]["statut"] == "a_verifier"


def test_site_sans_pages_legales(monkeypatch):
    installer_faux_site(monkeypatch, accueil="<html><body><p>" + "Mon blog de cuisine. " * 30 + "</p></body></html>")
    points = par_id(asyncio.run(analyser_site("https://exemple.fr/")))
    assert points["mentions_legales_page"]["statut"] == "manquant"
    assert points["ecommerce_cgv"]["statut"] == "a_verifier"
    assert points["mentions_siren"]["statut"] == "a_verifier"


def test_site_genere_en_javascript_donne_a_verifier(monkeypatch):
    installer_faux_site(monkeypatch, accueil='<html><body><div id="app"></div></body></html>')
    points = par_id(asyncio.run(analyser_site("https://exemple.fr/")))
    assert points["mentions_legales_page"]["statut"] == "a_verifier"
    assert "JavaScript" in points["mentions_legales_page"]["preuve"]


def test_page_legale_en_erreur_signalee(monkeypatch):
    installer_faux_site(monkeypatch, accueil=ACCUEIL.replace("/cgv", "/cgv-absente"))
    analyse = asyncio.run(analyser_site("https://exemple.fr/"))["analyse"]
    assert analyse["pages_non_recuperees"][0]["type"] == "cgv"
    assert "404" in analyse["pages_non_recuperees"][0]["erreur"]
    points = {v["id"]: v for v in analyse["verifications"]}
    assert points["ecommerce_retractation"]["statut"] == "a_verifier"
    assert "non récupérée" in points["ecommerce_retractation"]["preuve"]


@pytest.mark.parametrize("url", ["", "file:///etc/passwd", "http://localhost", "http://127.0.0.1"])
def test_analyse_refuse_les_adresses_dangereuses(url):
    resultat = asyncio.run(analyser_site(url))
    assert set(resultat) == {"statut", "erreur"} and resultat["statut"] == "erreur"


def test_analyse_ne_leve_jamais(monkeypatch):
    async def panne(url, **kwargs):
        raise RuntimeError("détail interne")
    monkeypatch.setattr(site_web, "recuperer_page", panne)
    resultat = asyncio.run(analyser_site("https://exemple.fr"))
    assert resultat["statut"] == "erreur" and "détail interne" not in resultat["erreur"]
