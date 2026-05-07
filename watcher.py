#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONCOURS MAROC WATCHER v1.3 — Hamza Bayahia
Fixes : SSL verify=False | scoring mots-entiers | filtre Rabat | erreurs silencieuses
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import re, json, webbrowser, unicodedata, os, smtplib
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Silence les warnings SSL (certificats gov.ma expirés/auto-signés)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

VILLE_CIBLE = "rabat"          # filtre géographique (mettre "" pour désactiver)
SCORE_MIN_AGR = 25             # score minimum pour afficher un résultat d'agrégateur
TIMEOUT = 15                   # secondes par requête

# Villes marocaines → si une offre mentionne l'une d'elles ET PAS Rabat → exclue
AUTRES_VILLES = [
    "casablanca", "marrakech", "agadir", "tanger", "fès", "fez",
    "meknès", "meknes", "oujda", "tétouan", "tetouan", "kénitra", "kenitra",
    "el jadida", "jorf lasfar", "safi", "mohammedia", "laayoune", "nador", "beni mellal",
    "settat", "khouribga", "errachidia", "guelmim", "ksar el-kébir",
    "ksar elkebir", "berrechid", "khemisset",
]

# ══════════════════════════════════════════════════════════════
#  PROFIL
# ══════════════════════════════════════════════════════════════

PROFIL = {
    "nom":     "Hamza Bayahia",
    "diplome": "Master 2 Data Science / IA — Bac+5 (RNCP Niveau 7)",

    # Correspondent exactement à son expertise → +30 pts (mot entier)
    "domaine": [
        "data", "informatique", "numérique", "digital",
        "systèmes d'information", "système d'information",
        "business intelligence", "intelligence artificielle",
        "statistique", "transformation digitale", "e-gouvernement",
    ],
    # Outils/compétences spécifiques → +15 pts (mot entier)
    "outils": [
        "power bi", "python", "sql", "bi", "si", "erp", "crm",
        "reporting", "data analyst", "data science", "data engineer",
    ],
    # Niveau managérial → +25 pts (mot entier)
    "managerial": [
        "chef de service", "chef de division", "responsable si",
        "responsable data", "directeur si", "chef de département",
        "chef de projet si", "responsable informatique",
    ],
    # Générique management → +10 pts
    "management_gen": [
        "responsable", "chef de projet", "coordinateur", "manager",
        "directeur adjoint", "chargé",
    ],
    # Si ces mots apparaissent → offre clairement hors profil → score = 0
    "exclusions": [
        # Métiers manuels / terrain
        "chauffeur", "gardien", "technicien de surface", "gérant station",
        "agent de sécurité", "femme de ménage", "agent d'entretien",
        "pâtissier", "cuisinier", "plombier", "électricien", "magasinier",
        "technicien de maintenance", "ingénieur de maintenance",
        "maintenance industrielle", "maintenance des équipements",
        "conduite de travaux", "gestion de chantier",
        "mécanique", "electromécanique", "génie civil",
        # Médical / juridique / finance opérationnelle
        "médecin", "infirmier", "pharmacien", "architecte", "urbaniste",
        "juriste", "avocat", "juge", "comptable", "caissier",
        "commercial terrain", "vendeur",
        # Secteur privé industriel clairement non-SI
        "métallurgie", "soudure", "btp", "béton armé",
        "production industrielle", "usine",
    ],
}

# ══════════════════════════════════════════════════════════════
#  ÉTABLISSEMENTS DIRECTS (30)
# ══════════════════════════════════════════════════════════════

ETABLISSEMENTS = [
    # ── MINISTÈRES
    {"nom": "Ministère Économie et Finances",            "sigle": "MEF",      "cat": "Ministère",
     "urls": ["https://www.finances.gov.ma/fr/Pages/Emploi.aspx",
              "https://www.finances.gov.ma/fr/Pages/Accueil.aspx"]},
    {"nom": "Ministère de l'Intérieur",                 "sigle": "MI",       "cat": "Ministère",
     "urls": ["http://www.interieur.gov.ma/articles/emploi",
              "http://www.interieur.gov.ma/"]},
    {"nom": "Ministère Éducation Nationale",             "sigle": "MEN",      "cat": "Ministère",
     "urls": ["https://www.men.gov.ma/Ar/Pages/emploi.aspx",
              "https://www.men.gov.ma/"]},
    {"nom": "Ministère de la Santé",                    "sigle": "MS",       "cat": "Ministère",
     "urls": ["https://www.sante.gov.ma/Pages/Emploi.aspx",
              "https://www.sante.gov.ma/"]},
    {"nom": "Ministère Réforme Admin. et Fonction Publique", "sigle": "MAGG", "cat": "Ministère",
     "urls": ["https://www.mmsp.gov.ma/fr/nos-metiers/recrutement",
              "https://www.mmsp.gov.ma/fr/concours-et-examens-d%E2%80%99aptitude-professionnelle",
              "https://www.mmsp.gov.ma/fr/"]},
    {"nom": "Ministère Transition Numérique",           "sigle": "MTN",      "cat": "Ministère",
     "urls": ["https://mcinet.gov.ma/",
              "https://www.mtntm.gov.ma/fr/emplois"]},
    {"nom": "Ministère de l'Agriculture",               "sigle": "MAPMDREF", "cat": "Ministère",
     "urls": ["https://www.agriculture.gov.ma/fr/content/emploi",
              "https://www.agriculture.gov.ma/"]},
    {"nom": "Ministère de l'Énergie et Mines",          "sigle": "MEM",      "cat": "Ministère",
     "urls": ["https://www.mem.gov.ma/fr/Pages/emploi.aspx",
              "https://www.mem.gov.ma/"]},
    {"nom": "Ministère des Affaires Étrangères",        "sigle": "MAE",      "cat": "Ministère",
     "urls": ["https://www.diplomatie.ma/fr/emplois",
              "https://www.diplomatie.ma/"]},
    {"nom": "Ministère de la Justice",                  "sigle": "MJ",       "cat": "Ministère",
     "urls": ["https://www.justice.gov.ma/fr/ministere/emploi-et-concours.aspx",
              "https://www.justice.gov.ma/"]},
    # ── ÉTABLISSEMENTS PUBLICS
    {"nom": "Haut Commissariat au Plan",                "sigle": "HCP",      "cat": "EPA",
     "urls": ["https://www.hcp.ma/Offres-d-emploi_r5.html",
              "https://www.hcp.ma/"]},
    {"nom": "Bank Al Maghrib",                          "sigle": "BAM",      "cat": "EPA",
     "urls": ["https://bkam.csod.com/ats/careersite/search.aspx?site=11&c=bkam",
              "https://www.bkam.ma/"]},
    {"nom": "Caisse de Dépôt et de Gestion",           "sigle": "CDG",      "cat": "EPA",
     "urls": ["https://www.cdg.ma/fr/rejoindre-cdg/nos-offres-demploi",
              "https://www.cdg.ma/fr/rejoindre-cdg",
              "https://www.cdg.ma/"]},
    {"nom": "ANCFCC — Agence Conservation Foncière",   "sigle": "ANCFCC",   "cat": "EPA",
     "urls": ["https://www.ancfcc.gov.ma/index.php/actualites/concours",
              "https://www.ancfcc.gov.ma/"]},
    {"nom": "ANRT — Agence Réglementation Télécom",    "sigle": "ANRT",     "cat": "EPA",
     "urls": ["https://www.anrt.ma/fr/recrutement",
              "https://www.anrt.ma/"]},
    {"nom": "ANAPEC",                                   "sigle": "ANAPEC",   "cat": "EPA",
     "urls": ["http://www.anapec.ma/",
              "https://www.anapec.ma/"]},
    {"nom": "OMPIC — Office Propriété Industrielle",   "sigle": "OMPIC",    "cat": "EPA",
     "urls": ["http://www.ompic.ma/fr/content/recrutement",
              "http://www.ompic.ma/"]},
    {"nom": "OFPPT",                                    "sigle": "OFPPT",    "cat": "EPA",
     "urls": ["https://www.ofppt.ma/fr/offres-d-emploi",
              "https://www.ofppt.ma/"]},
    {"nom": "CMR — Caisse Marocaine des Retraites",    "sigle": "CMR",      "cat": "EPA",
     "urls": ["https://www.cmr.gov.ma/fr/Pages/Concours-et-emploi.aspx",
              "https://www.cmr.gov.ma/"]},
    {"nom": "CNSS",                                     "sigle": "CNSS",     "cat": "EPA",
     "urls": ["https://www.cnss.ma/fr/emploi",
              "https://www.cnss.ma/"]},
    {"nom": "ONDA — Office National des Aéroports",    "sigle": "ONDA",     "cat": "EPIC",
     "urls": ["https://www.onda.ma/Je-d%C3%A9couvre-ONDA/Ressources-humaines/Recrutement",
              "https://www.onda.ma/"]},
    {"nom": "ANP — Agence Nationale des Ports",        "sigle": "ANP",      "cat": "EPIC",
     "urls": ["https://www.anp.org.ma/Fr/Pages/Emploi.aspx",
              "https://www.anp.org.ma/"]},
    {"nom": "AMDIE — Agence Développement Investissements", "sigle": "AMDIE","cat": "EPA",
     "urls": ["https://www.amdie.gov.ma/fr/offres-emploi",
              "https://www.amdie.gov.ma/"]},
    {"nom": "MASEN — Agence Énergie Durable",          "sigle": "MASEN",    "cat": "EPIC",
     "urls": ["https://masen-career.talent-soft.com/accueil.aspx?LCID=1036",
              "https://www.masen.ma/"]},
    {"nom": "ONEE — Office Électricité et Eau",        "sigle": "ONEE",     "cat": "EPIC",
     "urls": ["http://www.onee.ma/fr/recrutement",
              "http://www.onee.ma/"]},
    {"nom": "ONCF — Office Chemins de Fer",            "sigle": "ONCF",     "cat": "EPIC",
     "urls": ["https://www.oncf.ma/fr/Recrutement",
              "https://www.oncf.ma/"]},
    {"nom": "OCP Group",                                "sigle": "OCP",      "cat": "EPIC",
     "urls": ["https://www.ocpgroup.ma/fr/careers",
              "https://www.ocpgroup.ma/"]},
    {"nom": "Royal Air Maroc",                          "sigle": "RAM",      "cat": "EPIC",
     "urls": ["https://www.royalairmaroc.com/ma-fr/A-propos-de-Royal-Air-Maroc/Recrutement",
              "https://www.royalairmaroc.com/"]},
    {"nom": "CIH Bank",                                 "sigle": "CIH",      "cat": "EPIC",
     "urls": ["https://www.cih.co.ma/fr/groupe-cih/recrutement",
              "https://www.cih.co.ma/"]},
    {"nom": "Maroc Telecom (IAM)",                     "sigle": "IAM",      "cat": "EPIC",
     "urls": ["https://www.iam.ma/fr/offres-d-emploi",
              "https://www.iam.ma/"]},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,ar;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MOTS_JOB = [
    # Termes spécifiques emploi — "offre" seul est trop générique (Offre-groupe, Offre commerciale...)
    "concours", "emploi", "recrutement", "candidature",
    "offre d emploi", "offre de recrutement", "offres d emploi",  # "offre" uniquement avec contexte
    "avis de recrutement", "appel a candidature", "appel a candidatures",
    "poste a pourvoir", "postes ouverts", "poste vacant",
    "vacancy", "carrieres", "rejoindre", "nous rejoindre",
    "مباراة", "توظيف", "منصب", "وظيفة",
]

# Segments d'URL qui indiquent clairement un lien NON-emploi
URL_EXCL = [
    "/tarif", "/promo", "/offre-group", "/offre-commerc", "/offre-special",
    "/voyage", "/billet", "/boutique", "/produit", "/service-client",
    "/horaire", "/calendrier", "/carte", "/plan-", "/itineraire",
    "/actualit", "/presse", "/media", "/news", "/commun",
    "/don", "/partenaire", "/sponsor", "/publicite",
]

# ── Filtre diplôme ──────────────────────────────────────────
# Indicateurs Bac+5 ou plus → confirme que le profil est eligible
BAC5_KW = [
    "bac+5", "bac +5", "bac 5", "niveau bac+5", "niveau 5",
    "master", "master 2", "master ii", "master professionnel",
    "ingénieur d état",   # normalisé depuis "ingénieur d'état"
    "ingenieur d etat",
    "doctorat", "phd", "docteur en",
    "grande école", "desa", "dess",
    "bac+6", "bac +6", "bac 6",
    "bac+7", "bac +7",
    "echelle 11", "échelle 11",    # corps public Bac+5 au Maroc
    "corps a+", "attaché principal", "administrateur",
]

# Indicateurs Bac < 5 → exclure sauf si poste managérial senior
BAC_INF_KW = [
    "bac+2", "bac +2", "bac 2", "niveau bac+2",
    "bac+3", "bac +3", "bac 3", "niveau bac+3",
    "bac+4", "bac +4", "bac 4", "niveau bac+4",
    "technicien spécialisé", "technicien specialise",
    "bts", "dut", "deust",
    "echelle 9", "échelle 9",
    "echelle 10", "échelle 10",
    "licence professionnelle",   # Bac+3 uniquement
    "agent contractuel",         # souvent < Bac+5
]

# Mots qui qualifient un poste comme senior → on ne l'exclut pas même si Bac<5 mentionné
SENIOR_KW = [
    "chef de service", "chef de division", "directeur", "responsable",
    "ingénieur", "manager", "coordinateur", "chef de projet",
]

# ══════════════════════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════════════════════

def requete(url: str) -> requests.Response | None:
    """Requête HTTP avec SSL désactivé et timeout."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        r.encoding = "utf-8"
        return r if r.status_code < 400 else None
    except Exception:
        return None

def base_url(url: str) -> str:
    m = re.match(r"https?://[^/]+", url)
    return m.group(0) if m else ""

def absolu(href: str, page_url: str) -> str:
    if href.startswith("http"):
        return href
    return base_url(page_url) + "/" + href.lstrip("/")

def normaliser(texte: str) -> str:
    """
    Normalise un texte pour une comparaison robuste :
    - Minuscules
    - Apostrophes → espace  (d'information → d information)
    - Accents supprimés     (numérique → numerique, systèmes → systemes)
    Ainsi 'numérique' matche 'numerique', 'Bac+5' matche 'bac+5', etc.
    """
    texte = texte.lower()
    texte = re.sub(r"[''`\u2019\-]", " ", texte)          # apostrophes & tirets → espace
    texte = unicodedata.normalize("NFD", texte)             # décompose les accents
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")  # supprime les diacritiques
    return texte

def mot_entier(kw: str, texte: str) -> bool:
    """
    Vérifie que kw apparaît comme mot entier dans texte.
    Empêche 'bi' de matcher 'Kébir', 'si' de matcher 'services', etc.
    Normalise les apostrophes : 'systèmes d'information' = 'systèmes d information'.
    """
    pattern = r"(?<![a-zA-ZÀ-ÿ0-9])" + re.escape(normaliser(kw)) + r"(?![a-zA-ZÀ-ÿ0-9])"
    return bool(re.search(pattern, normaliser(texte), re.IGNORECASE))

# ══════════════════════════════════════════════════════════════
#  FILTRE GÉOGRAPHIQUE — Rabat uniquement
# ══════════════════════════════════════════════════════════════

def est_a_rabat(titre: str, desc: str = "") -> bool:
    """
    True si le poste est à Rabat, ou si aucune ville n'est mentionnée
    (= poste national → inclus par défaut).
    False si une autre ville marocaine est explicitement mentionnée.
    """
    if not VILLE_CIBLE:
        return True
    texte = (titre + " " + desc).lower()
    if VILLE_CIBLE in texte:
        return True
    for ville in AUTRES_VILLES:
        if ville in texte:
            return False
    return True  # pas de ville mentionnée → national → OK

# ══════════════════════════════════════════════════════════════
#  SCORING — mots entiers uniquement
# ══════════════════════════════════════════════════════════════

def scorer(titre: str, desc: str = "") -> int:
    texte = normaliser(titre + " " + desc)

    # 1. Offre clairement hors profil → score nul
    for ex in PROFIL["exclusions"]:
        if ex in texte:
            return 0

    # 2. Filtre diplôme → si niveau explicitement < Bac+5 sans poste senior → exclu
    dip = verifier_diplome(titre, desc)
    if dip["status"] == "exclu":
        return 0

    score = 0

    # 3. Domaine technique (+30)
    for kw in PROFIL["domaine"]:
        if mot_entier(kw, texte):
            score += 30

    # 4. Outils / compétences (+15)
    for kw in PROFIL["outils"]:
        if mot_entier(kw, texte):
            score += 15

    # 5. Niveau managérial précis (+25)
    for kw in PROFIL["managerial"]:
        if mot_entier(kw, texte):
            score += 25

    # 6. Management générique (+10)
    for kw in PROFIL["management_gen"]:
        if mot_entier(kw, texte):
            score += 10

    # 7. Bonus si Bac+5 explicitement confirmé (+15)
    if dip["status"] == "ok":
        score += 15

    return min(score, 100)

def est_pertinent(titre: str, desc: str = "") -> bool:
    texte = (titre + " " + desc).lower()
    all_kw = PROFIL["domaine"] + PROFIL["outils"] + PROFIL["managerial"]
    return any(mot_entier(kw, texte) for kw in all_kw)

def est_lien_job(texte: str, href: str) -> bool:
    # 1. Rejeter les URL clairement non-emploi
    href_lower = href.lower()
    if any(excl in href_lower for excl in URL_EXCL):
        return False
    # 2. Normaliser avant comparaison (accents + apostrophes)
    combined = normaliser(texte + " " + href)
    return any(m in combined for m in MOTS_JOB)

def verifier_diplome(titre: str, desc: str = "") -> dict:
    """
    Vérifie si le niveau de diplôme requis correspond à Bac+5.
    Retourne un dict avec : status, label, color, badge HTML.

    status :
      "ok"       → Bac+5 ou plus explicitement mentionné → éligible
      "exclu"    → Bac < 5 mentionné sans mention Bac+5 ET pas senior → non éligible
      "senior"   → poste managérial senior → probablement Bac+5 même non précisé
      "inconnu"  → aucune info de diplôme → à vérifier manuellement
    """
    texte     = normaliser(titre + " " + desc)
    has_bac5  = any(mot_entier(kw, texte) for kw in BAC5_KW)
    has_inf   = any(mot_entier(kw, texte) for kw in BAC_INF_KW)
    is_senior = any(mot_entier(kw, texte) for kw in SENIOR_KW)

    if has_bac5:
        return {
            "status": "ok",
            "label": "Bac+5 confirm&eacute;",
            "color": "#1e8449",
            "bg":    "#d5f5e3",
            "icon":  "&#10003;",    # ✓
        }
    elif has_inf and not is_senior:
        return {
            "status": "exclu",
            "label": "Niveau &lt; Bac+5",
            "color": "#c0392b",
            "bg":    "#fde8e8",
            "icon":  "&#10007;",    # ✗
        }
    elif is_senior:
        return {
            "status": "senior",
            "label": "Senior (v&eacute;rifier)",
            "color": "#1565c0",
            "bg":    "#e8f0fe",
            "icon":  "&#126;",      # ~
        }
    else:
        return {
            "status": "inconnu",
            "label": "&Agrave; v&eacute;rifier",
            "color": "#777",
            "bg":    "#f4f4f4",
            "icon":  "?",
        }

# ══════════════════════════════════════════════════════════════
#  DEADLINE — extraction et filtrage des offres expirées
# ══════════════════════════════════════════════════════════════

_DATE_RE = re.compile(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})')

_DEADLINE_KW = [
    "date limite", "avant le", "jusqu au", "jusqu'au", "cloture", "clôture",
    "depot des candidatures", "dépôt des candidatures", "date de cloture",
    "dernier delai", "date butoir", "آخر أجل", "الإيداع", "تاريخ الإغلاق",
]

def extraire_deadline(titre: str, desc: str = ""):
    """
    Tente d'extraire la date limite d'un titre/description.
    Retourne un objet date ou None si non trouvé.
    """
    texte_n = normaliser(titre + " " + desc)

    # 1. Chercher un mot-clé deadline puis une date dans les 80 chars suivants
    for kw in _DEADLINE_KW:
        idx = texte_n.find(normaliser(kw))
        if idx != -1:
            m = _DATE_RE.search(texte_n[idx: idx + 80])
            if m:
                try:
                    j, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    if a < 100:
                        a += 2000
                    if 1 <= mo <= 12 and 1 <= j <= 31:
                        return date(a, mo, j)
                except (ValueError, OverflowError):
                    pass

    # 2. Date isolée dans le titre seul (souvent = deadline sur les agrégateurs)
    m = _DATE_RE.search(normaliser(titre))
    if m:
        try:
            j, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if a < 100:
                a += 2000
            today = date.today()
            if 1 <= mo <= 12 and 1 <= j <= 31:
                d = date(a, mo, j)
                # On ne garde que les dates plausibles (±2 ans)
                if date(today.year - 1, 1, 1) <= d <= date(today.year + 2, 12, 31):
                    return d
        except (ValueError, OverflowError):
            pass

    return None

def est_expire(p: dict) -> bool:
    """True si la date limite est connue ET déjà dépassée."""
    dl = p.get("deadline")
    if dl is None:
        return False
    return dl < date.today()

def afficher_deadline(p: dict) -> str:
    """Cellule HTML pour la colonne Délai."""
    dl = p.get("deadline")
    if dl is None:
        return '<span style="color:#ccc;font-size:11px">—</span>'
    today = date.today()
    jours = (dl - today).days
    if jours < 0:
        return f'<span style="color:#c0392b;font-weight:700;font-size:11px">Expiré ({dl.strftime("%d/%m")})</span>'
    elif jours == 0:
        return f'<span style="color:#c0392b;font-weight:800;font-size:11px">⚠ Aujourd\'hui!</span>'
    elif jours <= 3:
        return f'<span style="color:#e74c3c;font-weight:700;font-size:11px">⚠ {dl.strftime("%d/%m")} ({jours}j)</span>'
    elif jours <= 7:
        return f'<span style="color:#e67e22;font-weight:700;font-size:11px">{dl.strftime("%d/%m")} ({jours}j)</span>'
    else:
        return f'<span style="color:#27ae60;font-size:11px">{dl.strftime("%d/%m/%Y")} ({jours}j)</span>'

# ══════════════════════════════════════════════════════════════
#  CACHE — détection des nouvelles annonces
# ══════════════════════════════════════════════════════════════

RAPPORT_DIR = Path(__file__).parent / "rapports"
CACHE_FILE  = RAPPORT_DIR / "seen_posts.json"
LOG_FILE    = RAPPORT_DIR / "errors.log"

def charger_cache() -> dict:
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def sauver_cache(cache: dict):
    RAPPORT_DIR.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def log_err(msg: str):
    RAPPORT_DIR.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}\n")

def cle_cache(titre: str) -> str:
    return re.sub(r"\s+", " ", titre.lower().strip())[:80]

def marquer_nouveaux(postes: list, cache: dict) -> tuple:
    aujourd_hui = datetime.now().strftime("%Y-%m-%d")
    for p in postes:
        cle = cle_cache(p["titre"])
        p["nouveau"] = cle not in cache
        if p["nouveau"]:
            cache[cle] = aujourd_hui
    return postes, cache

# ══════════════════════════════════════════════════════════════
#  SCRAPERS — AGRÉGATEURS
# ══════════════════════════════════════════════════════════════

def poste(titre, lien, source, date_pub=None) -> dict:
    return {
        "titre":    titre,
        "lien":     lien,
        "source":   source,
        "date":     date_pub or datetime.now().strftime("%d/%m/%Y"),
        "score":    scorer(titre),
        "diplome":  verifier_diplome(titre),
        "etab":     None,
        "nouveau":  False,
        "deadline": extraire_deadline(titre),
    }

def scraper_concoursdemaroc() -> list:
    postes = []
    for url in [
        "https://www.concoursdemaroc.com/",
        "https://www.concoursdemaroc.com/category/concours-maroc/",
        "https://www.concoursdemaroc.com/category/emploi-maroc/",
    ]:
        r = requete(url)
        if not r:
            log_err(f"ConcoursDuMaroc inaccessible : {url}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for art in soup.find_all("article"):
            titre_el = art.find(["h2", "h3", "h1"])
            lien_el  = art.find("a", href=True)
            if not titre_el or not lien_el:
                continue
            titre    = titre_el.get_text(strip=True)
            lien     = absolu(lien_el["href"], url)
            date_el  = art.find(["time", "span"], class_=re.compile(r"date|time|post"))
            date_str = date_el.get_text(strip=True) if date_el else "—"
            if est_a_rabat(titre) and scorer(titre) >= SCORE_MIN_AGR:
                postes.append(poste(titre, lien, "ConcoursDuMaroc", date_pub=date_str))
    return postes


def scraper_rekrute() -> list:
    postes = []
    # Filtre : secteur public (s=3) + Rabat (ville=Rabat) + tri par date
    for page in range(1, 4):
        url = f"https://www.rekrute.com/offres.html?s=3&p={page}&o=1&ville=Rabat"
        r   = requete(url)
        if not r:
            # Fallback sans filtre ville
            url = f"https://www.rekrute.com/offres.html?s=3&p={page}&o=1"
            r   = requete(url)
        if not r:
            log_err(f"Rekrute inaccessible p{page}")
            continue
        soup  = BeautifulSoup(r.text, "html.parser")
        items = soup.find_all("li", class_=re.compile(r"^post-"))
        if not items:
            items = soup.find_all("div", class_=re.compile(r"offer|job|result|item"))
        for item in items:
            lien_el  = item.find("a", href=re.compile(r"/recrutement/|/offre"))
            if not lien_el:
                lien_el = item.find("a", href=True)
            if not lien_el:
                continue
            titre_el = item.find(["h2", "h3", "h4", "strong"])
            titre    = (titre_el.get_text(strip=True) if titre_el
                        else lien_el.get_text(strip=True))
            if len(titre) < 5:
                continue
            lien = absolu(lien_el.get("href", ""), "https://www.rekrute.com")
            sc   = scorer(titre)
            if est_a_rabat(titre) and sc >= SCORE_MIN_AGR:
                postes.append(poste(titre, lien, "Rekrute (public)"))
    return postes


def scraper_mmsp() -> list:
    """MMSP — Ministère Modernisation, source officielle des concours nationaux."""
    postes = []
    for url, nom in [
        ("https://www.mmsp.gov.ma/fr/concours.aspx", "MMSP"),
        ("http://www.emploi-public.ma/",              "EmploiPublicMA"),
    ]:
        r = requete(url)
        if not r:
            log_err(f"{nom} inaccessible")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            titre = a.get_text(strip=True)
            href  = absolu(a["href"], url)
            if len(titre) < 10 or titre in seen:
                continue
            seen.add(titre)
            sc = scorer(titre)
            if est_a_rabat(titre) and sc >= SCORE_MIN_AGR:
                postes.append(poste(titre, href, nom))
    return postes


def scraper_marocannonces() -> list:
    postes = []
    for url in [
        "https://www.marocannonces.com/categorie/offres-emploi/b-informatique.html",
        "https://www.marocannonces.com/categorie/offres-emploi/b-secteur-public.html",
    ]:
        r = requete(url)
        if not r:
            log_err(f"MarocAnnonces inaccessible : {url}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.find_all(["li", "div"], class_=re.compile(r"ann|offer|item|result")):
            titre_el = item.find(["h2", "h3", "h4", "strong", "a"])
            lien_el  = item.find("a", href=True)
            if not titre_el or not lien_el:
                continue
            titre = titre_el.get_text(strip=True)
            lien  = absolu(lien_el["href"], url)
            sc    = scorer(titre)
            if est_a_rabat(titre) and sc >= SCORE_MIN_AGR:
                postes.append(poste(titre, lien, "MarocAnnonces"))
    return postes


def scraper_indeed() -> list:
    postes = []
    queries = [
        f"chef+de+service+{VILLE_CIBLE}+maroc",
        f"data+analyst+secteur+public+{VILLE_CIBLE}",
        f"responsable+informatique+{VILLE_CIBLE}+administration",
        f"ingenieur+systemes+information+{VILLE_CIBLE}+public",
    ]
    for q in queries:
        r = requete(f"https://ma.indeed.com/jobs?q={q}&sort=date")
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("div", class_=re.compile(r"job_seen|jobCard|result")):
            titre_el = card.find(["h2", "h3"], class_=re.compile(r"title|jobTitle"))
            lien_el  = card.find("a", href=True)
            if not titre_el:
                continue
            titre = titre_el.get_text(strip=True)
            href  = absolu(lien_el.get("href", ""), "https://ma.indeed.com") if lien_el else ""
            sc    = scorer(titre)
            if est_a_rabat(titre) and sc >= SCORE_MIN_AGR:
                postes.append(poste(titre, href, "Indeed MA"))
    return postes

# ══════════════════════════════════════════════════════════════
#  SCRAPER — ÉTABLISSEMENTS DIRECTS
# ══════════════════════════════════════════════════════════════

def scraper_etablissement(etab: dict) -> dict:
    postes_trouves = []
    url_visitee    = etab["urls"][0]
    statut         = "erreur"

    for url in etab["urls"]:
        r = requete(url)
        if not r:
            log_err(f"{etab['sigle']} inaccessible : {url}")
            continue

        statut      = "vide"
        url_visitee = url
        soup        = BeautifulSoup(r.text, "html.parser")
        seen        = set()

        # Liens job
        for a in soup.find_all("a", href=True):
            texte = a.get_text(strip=True)
            href  = absolu(a["href"], url)
            if len(texte) < 6 or texte in seen:
                continue
            if not est_lien_job(texte, a["href"]):
                continue
            seen.add(texte)
            postes_trouves.append({
                "titre":    texte,
                "lien":     href,
                "source":   etab["sigle"],
                "date":     datetime.now().strftime("%d/%m/%Y"),
                "score":    scorer(texte),
                "diplome":  verifier_diplome(texte),
                "etab":     etab["sigle"],
                "nouveau":  False,
                "deadline": extraire_deadline(texte),
            })

        # PDFs emploi/concours
        for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
            texte = a.get_text(strip=True) or a["href"].split("/")[-1]
            href  = absolu(a["href"], url)
            if not est_lien_job(texte, a["href"]) or texte in seen:
                continue
            seen.add(texte)
            postes_trouves.append({
                "titre":    f"[PDF] {texte}",
                "lien":     href,
                "source":   etab["sigle"],
                "date":     datetime.now().strftime("%d/%m/%Y"),
                "score":    scorer(texte),
                "diplome":  verifier_diplome(texte),
                "etab":     etab["sigle"],
                "nouveau":  False,
                "deadline": extraire_deadline(texte),
            })

        if postes_trouves:
            statut = "ok"
            break   # On a trouvé, pas besoin de l'URL suivante

    # Exclure les posts hors profil (score=0 = exclu par diplôme ou mots d'exclusion)
    # et trier par score décroissant
    postes_trouves = sorted(
        [p for p in postes_trouves if p["score"] > 0],
        key=lambda x: x["score"],
        reverse=True,
    )
    if not postes_trouves:
        statut = "vide"

    return {
        "etab":        etab,
        "statut":      statut,
        "postes":      postes_trouves,
        "url_visitee": url_visitee,
    }

# ══════════════════════════════════════════════════════════════
#  RAPPORT HTML
# ══════════════════════════════════════════════════════════════

def couleur_score(s: int) -> str:
    return "#1e8449" if s >= 40 else "#ca6f1e" if s >= 25 else "#888"

def badge_diplome(p: dict) -> str:
    dip = p.get("diplome") or verifier_diplome(p["titre"])
    return (f'<span style="background:{dip["bg"]};color:{dip["color"]};'
            f'padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;white-space:nowrap">'
            f'{dip["icon"]} {dip["label"]}</span>')

def lignes(liste: list) -> str:
    if not liste:
        return '<tr><td colspan="6" style="color:#bbb;text-align:center;padding:16px">Aucun résultat</td></tr>'
    rows = ""
    for p in liste:
        badge_new  = '<span class="badge-new">NOUVEAU</span> ' if p.get("nouveau") else ""
        score_html = (f'<span style="color:{couleur_score(p["score"])};font-weight:700">'
                      f'{p["score"]}%</span>' if p["score"] else '<span style="color:#ccc">—</span>')
        rows += f"""
        <tr>
          <td>{badge_new}<a href="{p['lien']}" target="_blank">{p['titre']}</a></td>
          <td><span class="src">{p['source']}</span></td>
          <td style="text-align:center">{score_html}</td>
          <td style="text-align:center">{badge_diplome(p)}</td>
          <td style="text-align:center;white-space:nowrap">{afficher_deadline(p)}</td>
          <td style="color:#999;font-size:12px;white-space:nowrap">{p['date']}</td>
        </tr>"""
    return rows

def dashboard(resultats: list) -> str:
    rows = ""
    for res in resultats:
        e      = res["etab"]
        nb     = len(res["postes"])
        url    = res["url_visitee"] or e["urls"][0]
        cat_c  = {"Ministère": ("#1a237e","#e8eaf6"), "EPA": ("#004d40","#e0f2f1"),
                  "EPIC": ("#e65100","#fff3e0")}.get(e["cat"], ("#333","#f5f5f5"))
        icone  = "🟢" if res["statut"]=="ok" and nb>0 else ("🔴" if res["statut"]=="erreur" else "⚫")
        info   = f"{nb} lien(s) emploi" if nb>0 else ("Site inaccessible" if res["statut"]=="erreur" else "Aucune offre détectée")
        rows += f"""
        <tr>
          <td><b>{e['sigle']}</b></td>
          <td>{e['nom']}</td>
          <td><span style="background:{cat_c[1]};color:{cat_c[0]};padding:2px 8px;
              border-radius:4px;font-size:11px;font-weight:700">{e['cat']}</span></td>
          <td>{icone} {info}</td>
          <td><a href="{url}" target="_blank" style="font-size:12px;color:#1565c0">Voir →</a></td>
        </tr>"""
    return rows

def _cle_tri_deadline(p: dict):
    """Tri : deadline connue la plus proche d'abord, puis pas de deadline (score décroissant)."""
    dl = p.get("deadline")
    # Tuple (a, b) : a=0 si deadline connue (tri par date), a=1 sinon (tri par score inversé)
    if dl is not None:
        return (0, dl, -p["score"])
    return (1, date(9999, 12, 31), -p["score"])

def generer_rapport(postes_agr, resultats_etabs, stats_agr) -> str:
    postes_etabs = [p for r in resultats_etabs for p in r["postes"]]
    tous_brut = postes_agr + postes_etabs

    # Déduplication
    seen_c, uniq = set(), []
    for p in tous_brut:
        cle = cle_cache(p["titre"])
        if cle not in seen_c:
            seen_c.add(cle)
            uniq.append(p)

    # Filtrer les offres dont la deadline est déjà passée
    nb_expires_rapport = sum(1 for p in uniq if est_expire(p))
    uniq = [p for p in uniq if not est_expire(p)]

    # Tri principal : deadline (urgents d'abord), puis score décroissant
    tries    = sorted(uniq, key=_cle_tri_deadline)
    haute    = [p for p in tries if p["score"] >= 40]
    moyenne  = [p for p in tries if 25 <= p["score"] < 40]
    # Nouveaux triés par deadline/score aussi
    nouveaux = sorted([p for p in tries if p.get("nouveau")], key=_cle_tri_deadline)
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    kw_pills = "".join(f'<span class="kw">{kw}</span>' for kw in PROFIL["domaine"][:8])
    agr_rows = "".join(
        f"<tr><td>{s}</td><td style='text-align:center'><b>{n}</b></td></tr>"
        for s, n in stats_agr.items()
    )
    etabs_avec_offres = "".join(f"""
    <div class="section">
      <h2>📋 {r['etab']['nom']}
        <span class="pill" style="background:#f0f4ff;color:#1a237e">{r['etab']['sigle']}</span>
        <span class="pill pill-g">{len(r['postes'])} lien(s)</span>
      </h2>
      <table>
        <tr><th>Lien trouvé</th><th>Source</th><th>Score</th><th>Niveau diplôme</th><th>Délai</th><th>Date pub.</th></tr>
        {lignes(r['postes'])}
      </table>
    </div>""" for r in resultats_etabs if r["postes"])

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Veille Concours Maroc — {date_str}</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Tahoma,sans-serif;background:#eef1f7;color:#2c3e50;line-height:1.5}}
  .hero{{background:linear-gradient(135deg,#1a237e 0%,#1565c0 100%);color:white;padding:36px 48px}}
  .hero h1{{font-size:22px;font-weight:800}}
  .hero p{{opacity:.75;font-size:14px;margin-top:6px}}
  .wrap{{max-width:1180px;margin:0 auto;padding:26px 22px}}
  .cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:22px}}
  .card{{background:white;border-radius:12px;padding:18px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.07)}}
  .card .num{{font-size:38px;font-weight:800;line-height:1}}
  .card .lbl{{font-size:11px;color:#888;margin-top:5px}}
  .profil{{background:#e8f4fd;border-left:4px solid #1565c0;border-radius:8px;padding:13px 18px;margin-bottom:22px;font-size:13px}}
  .kw{{display:inline-block;background:#1565c0;color:white;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;margin:2px}}
  .section{{background:white;border-radius:12px;padding:22px;box-shadow:0 2px 10px rgba(0,0,0,.07);margin-bottom:20px}}
  .section h2{{font-size:16px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:10px}}
  .pill{{font-size:12px;padding:3px 11px;border-radius:20px;font-weight:700}}
  .pill-g{{background:#d5f5e3;color:#1e8449}}
  .pill-o{{background:#fdebd0;color:#ca6f1e}}
  .pill-b{{background:#d6eaf8;color:#1565c0}}
  .pill-r{{background:#fde8e8;color:#c0392b}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px}}
  th{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:#777;padding:9px 12px;border-bottom:2px solid #eee;text-align:left}}
  td{{padding:11px 12px;border-bottom:1px solid #f4f4f4;vertical-align:middle}}
  tr:last-child td{{border-bottom:none}}
  td a{{color:#1565c0;text-decoration:none;font-weight:500}}
  td a:hover{{text-decoration:underline}}
  .src{{background:#e8eaf6;color:#3949ab;padding:2px 8px;border-radius:5px;font-size:11px;font-weight:700;white-space:nowrap}}
  .badge-new{{background:#e74c3c;color:white;font-size:10px;font-weight:800;padding:2px 7px;border-radius:20px;vertical-align:middle;margin-right:4px}}
  .footer{{text-align:center;color:#bbb;font-size:12px;padding:22px}}
  @media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}}.hero{{padding:24px}}}}
</style>
</head>
<body>
<div class="hero">
  <h1>Veille Concours Maroc — {PROFIL['nom']}</h1>
  <p>{date_str} &nbsp;·&nbsp; Filtre : {VILLE_CIBLE.title() if VILLE_CIBLE else "Tout le Maroc"} &nbsp;·&nbsp;
     5 agrégateurs + {len(ETABLISSEMENTS)} établissements directs</p>
</div>
<div class="wrap">
  <div class="profil">
    <strong>Profil : {PROFIL['diplome']}</strong><br>
    Domaines cibles : {kw_pills}
  </div>
  <div class="cards">
    <div class="card"><div class="num" style="color:#c0392b">{len(nouveaux)}</div>
      <div class="lbl">Nouvelles<br>annonces</div></div>
    <div class="card"><div class="num" style="color:#1e8449">{len(haute)}</div>
      <div class="lbl">Haute<br>compatibilité ≥40%</div></div>
    <div class="card"><div class="num" style="color:#ca6f1e">{len(moyenne)}</div>
      <div class="lbl">Compatibilité<br>moyenne 25–40%</div></div>
    <div class="card"><div class="num" style="color:#1565c0">{sum(1 for r in resultats_etabs if r['postes'])}</div>
      <div class="lbl">Établissements<br>avec offres</div></div>
    <div class="card"><div class="num" style="color:#555">{len(tries)}</div>
      <div class="lbl">Total actifs<br>analysés</div></div>
    <div class="card"><div class="num" style="color:#bbb">{nb_expires_rapport}</div>
      <div class="lbl">Offres expirées<br>filtrées</div></div>
  </div>

  <div class="section">
    <h2>🔴 Nouvelles annonces <span class="pill pill-r">{len(nouveaux)}</span></h2>
    <table><tr><th>Poste</th><th>Source</th><th>Score</th><th>Niveau diplôme</th><th>Délai</th><th>Date pub.</th></tr>
    {lignes(nouveaux) if nouveaux else
     '<tr><td colspan="6" style="color:#aaa;text-align:center;padding:16px">Aucune nouvelle annonce — tout est déjà connu.</td></tr>'}
    </table>
  </div>

  <div class="section">
    <h2>★ Haute compatibilité ≥ 40% <span class="pill pill-g">{len(haute)}</span></h2>
    <table><tr><th>Poste</th><th>Source</th><th>Score</th><th>Niveau diplôme</th><th>Délai</th><th>Date pub.</th></tr>
    {lignes(haute)}</table>
  </div>

  <div class="section">
    <h2>Compatibilité moyenne 25–40% <span class="pill pill-o">{len(moyenne)}</span></h2>
    <table><tr><th>Poste</th><th>Source</th><th>Score</th><th>Niveau diplôme</th><th>Délai</th><th>Date pub.</th></tr>
    {lignes(moyenne)}</table>
  </div>

  <div class="section">
    <h2>🏛️ Dashboard — {len(ETABLISSEMENTS)} établissements vérifiés
      <span class="pill pill-b">{datetime.now().strftime("%d/%m/%Y")}</span>
    </h2>
    <p style="font-size:13px;color:#777;margin-bottom:14px">
      🟢 Liens emploi détectés &nbsp;|&nbsp; ⚫ Aucune offre &nbsp;|&nbsp; 🔴 Site inaccessible aujourd'hui
    </p>
    <table>
      <tr><th>Sigle</th><th>Établissement</th><th>Type</th><th>Statut</th><th>Site</th></tr>
      {dashboard(resultats_etabs)}
    </table>
  </div>

  {etabs_avec_offres}

  <div class="section">
    <h2>🌐 Détail agrégateurs</h2>
    <table style="max-width:500px">
      <tr><th>Site</th><th style="text-align:center">Résultats filtrés</th></tr>
      {agr_rows}
    </table>
    <p style="font-size:12px;color:#aaa;margin-top:12px">
      Score minimum affiché : {SCORE_MIN_AGR}% &nbsp;|&nbsp;
      Filtre ville : {VILLE_CIBLE.title() if VILLE_CIBLE else "désactivé"} &nbsp;|&nbsp;
      Erreurs détaillées → <code>rapports/errors.log</code>
    </p>
  </div>
</div>
<div class="footer">Concours Watcher v1.3 — {date_str} — Hamza Bayahia</div>
</body></html>"""

# ══════════════════════════════════════════════════════════════
#  EMAIL — récap optionnel (variables d'env EMAIL_TO/FROM/PASSWORD)
# ══════════════════════════════════════════════════════════════

def envoyer_email(nb_new: int, nb_total: int, nb_expires: int, url_rapport: str):
    """
    Envoie un email récapitulatif.
    Variables d'env requises : EMAIL_TO, EMAIL_FROM, EMAIL_PASSWORD (mot de passe app Gmail).
    Si absentes, aucun email n'est envoyé (pas d'erreur).
    """
    to_addr   = os.environ.get("EMAIL_TO", "")
    from_addr = os.environ.get("EMAIL_FROM", "")
    password  = os.environ.get("EMAIL_PASSWORD", "")
    if not all([to_addr, from_addr, password]):
        print("  ℹ  Email non configuré — variables EMAIL_TO/FROM/PASSWORD manquantes")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (f"[Concours Maroc] {nb_new} nouvelle(s) — "
                          f"{datetime.now().strftime('%d/%m/%Y')}")
        msg["From"] = from_addr
        msg["To"]   = to_addr
        corps_html = f"""
<h2 style="color:#1a237e">Veille Concours Maroc — {datetime.now().strftime('%d/%m/%Y')}</h2>
<ul>
  <li>🔴 Nouvelles annonces : <strong>{nb_new}</strong></li>
  <li>✅ Offres actives affichées : <strong>{nb_total}</strong></li>
  <li>⛔ Offres expirées filtrées : <strong>{nb_expires}</strong></li>
</ul>
<p><a href="{url_rapport}" style="color:#1565c0">→ Voir le rapport complet</a></p>
<hr><p style="color:#aaa;font-size:12px">Concours Watcher — Hamza Bayahia</p>"""
        msg.attach(MIMEText(corps_html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(from_addr, password)
            srv.sendmail(from_addr, to_addr, msg.as_string())
        print(f"  ✅ Email envoyé à {to_addr}")
    except Exception as e:
        print(f"  ❌ Erreur email : {e}")

# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

SCRAPERS_AGR = [
    ("concoursdemaroc.com",       scraper_concoursdemaroc),
    ("rekrute.com (Rabat/public)",scraper_rekrute),
    ("MMSP / emploi-public.ma",   scraper_mmsp),
    ("marocannonces.com",         scraper_marocannonces),
    ("indeed.ma",                 scraper_indeed),
]

def main():
    RAPPORT_DIR.mkdir(exist_ok=True)
    # Vide le log d'erreurs du jour
    LOG_FILE.write_text(f"=== {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n", encoding="utf-8")

    print("\n" + "═"*62)
    print("  CONCOURS MAROC WATCHER v1.3 — Hamza Bayahia")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  Filtre géographique : {VILLE_CIBLE.title() if VILLE_CIBLE else 'désactivé'}")
    print(f"  Score minimum agrégateurs : {SCORE_MIN_AGR}%")
    print("═"*62)

    cache = charger_cache()

    # ── Agrégateurs
    print("\n── AGRÉGATEURS ──────────────────────────────────────────")
    postes_agr, stats_agr = [], {}
    for i, (nom, fn) in enumerate(SCRAPERS_AGR, 1):
        print(f"[{i}/{len(SCRAPERS_AGR)}] {nom}...", end=" ", flush=True)
        try:
            res = fn()
            print(f"→ {len(res)} résultats")
            postes_agr.extend(res)
            stats_agr[nom] = len(res)
        except Exception as e:
            print(f"→ ERREUR")
            log_err(f"{nom}: {e}")
            stats_agr[nom] = 0

    # ── Établissements directs
    print(f"\n── {len(ETABLISSEMENTS)} ÉTABLISSEMENTS ─────────────────────────────")
    resultats_etabs = []
    for etab in ETABLISSEMENTS:
        print(f"  ▸ {etab['sigle']:10s} {etab['nom'][:44]:<44}", end=" ", flush=True)
        res = scraper_etablissement(etab)
        nb  = len(res["postes"])
        print(f"{'🟢' if nb>0 else ('🔴' if res['statut']=='erreur' else '⚫')} {nb} lien(s)")
        resultats_etabs.append(res)

    # ── Cache nouveau
    tous_brut = postes_agr + [p for r in resultats_etabs for p in r["postes"]]
    tous_brut, cache = marquer_nouveaux(tous_brut, cache)
    sauver_cache(cache)

    # Réinjecter flags nouveau dans résultats etabs
    flags = {cle_cache(p["titre"]): p.get("nouveau", False) for p in tous_brut}
    for res in resultats_etabs:
        for p in res["postes"]:
            p["nouveau"] = flags.get(cle_cache(p["titre"]), False)

    # Filtrer les offres expirées APRÈS avoir mis à jour le cache
    # (on les marque quand même "vues" pour ne pas les re-notifier si elles réapparaissent)
    nb_expires = sum(1 for p in tous_brut if est_expire(p))
    tous_actifs = [p for p in tous_brut if not est_expire(p)]

    # ── Rapport
    date_f   = datetime.now().strftime("%Y-%m-%d_%H-%M")
    contenu  = generer_rapport(postes_agr, resultats_etabs, stats_agr)
    chemin   = RAPPORT_DIR / f"rapport_{date_f}.html"
    chemin.write_text(contenu, encoding="utf-8")

    # ── GitHub Pages : toujours écraser docs/index.html avec le dernier rapport
    docs_dir = Path(__file__).parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / "index.html").write_text(contenu, encoding="utf-8")

    nb_new = sum(1 for p in tous_actifs if p.get("nouveau"))
    print(f"\n{'═'*62}")
    print(f"  Nouvelles annonces  : {nb_new}")
    print(f"  Total actifs        : {len(tous_actifs)}")
    print(f"  Offres expirées     : {nb_expires} (filtrées)")
    print(f"  Rapport local       : {chemin}")
    print(f"  Rapport web (Pages) : docs/index.html")
    print(f"  Erreurs             : rapports/errors.log")
    print("═"*62 + "\n")

    # ── Email récap (optionnel)
    pages_url = os.environ.get("GITHUB_PAGES_URL", chemin.as_uri())
    envoyer_email(nb_new, len(tous_actifs), nb_expires, pages_url)

    webbrowser.open(chemin.as_uri())

if __name__ == "__main__":
    main()
