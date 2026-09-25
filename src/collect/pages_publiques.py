"""Pages publiques que l'élève consulte : relevé (avec cache) et lecture des chiffres affichés.

Contrat : results/concordance/CONTRAT.md. Deux sources :
- Parcoursup, fiche publique `afficherFicheFormation?g_ta_cod=<code>` (formations et apprentissage) ;
- MonMaster, l'API publique que la fiche appelle elle-même (`POST /api/candidat/mm1/formations`, corps
  `{uai, inm}`), sans authentification.

Relevé : au plus une requête par `PAUSE_S` secondes, séquentiel, reprise sur cache. Chaque fichier du cache est
inscrit dans un manifeste (sha256, date et heure de relevé, statut HTTP). Un échec est inscrit comme tel, jamais
remplacé par autre chose.

Les motifs reprennent les libellés exacts des pages, relevés sur les inventaires de Jarvis du 25/09
(`_orientai-ref/verticale-2026-09/concordance/`). La lecture ne dépend pas du constructeur de la base ; le contrôle
de concordance (`src/eval/concordance.py`) a ses propres motifs, écrits séparément.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

PAUSE_S = 1.5
AGENT = "Mozilla/5.0 (OrientAI-releve/1.0 ; verification de concordance, 1 requete / 1,5 s)"
URL_PSUP = "https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod={}&typeBac=0&originePc=0"
URL_MM = "https://monmaster.gouv.fr/api/candidat/mm1/formations?page=0&size=10000"

# Un nombre de la page : milliers séparés par une espace (« 1 833 ») ou chiffres collés (« 1833 »), jamais précédé
# d'un chiffre. Sans ces bornes, « en 2025 935 candidats » se lisait 2 025 935 (défaut trouvé le 25/09 par le
# contrôle positif contre l'inventaire de Jarvis : 82 pages sur 88).
_N = r"(?<![\d])(\d{1,3}(?:[  \xa0]\d{3})+|\d+)"


def nombre(s: str) -> int:
    return int(re.sub(r"[\s \xa0]", "", s))


def texte_page(h: str) -> str:
    """Texte visible d'une page, une seule ligne, espaces normalisés (même traitement que les inventaires)."""
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", h))
    return " ".join(x.strip() for x in t.split("\n") if x.strip())


# Libellé exact de la page -> (champ, motif). Le groupe 1 est le chiffre ; un groupe 2 éventuel, l'année.
MOTIFS_PSUP = {
    "places_annee_en_cours": (r"N places en AAAA", _N + r" places en (20\d\d)"),
    "voeux_confirmes_annee_en_cours": (r"N vœux confirmés en AAAA", _N + r" vœux confirmés en (20\d\d)"),
    "places_offertes": (r"N places offertes par la formation en AAAA", _N + r" places offertes par la formation en (20\d\d)"),
    "candidats_ont_postule": (r"N candidats ont postulé à cette formation", _N + r" candidats ont postulé à cette formation"),
    "candidats_classes": (r"La formation a classé N candidats", r"La formation a classé " + _N + r" candidats"),
    "candidats_ont_pu_recevoir_une_proposition": (
        r"N candidats ont pu recevoir une proposition d'admission",
        _N + r" candidats ont pu recevoir une proposition d'admission"),
    "candidats_ont_choisi_d_integrer": (
        r"N candidats ont choisi d'intégrer cette formation", _N + r" candidats ont choisi d'intégrer cette formation"),
    "admis_repartition": (
        r"Répartition par type de bac des N candidats admis de cette formation en AAAA",
        r"Répartition par type de bac des " + _N + r" candidats admis de cette formation en (20\d\d)"),
}
REPARTITION = {"repartition_admis_bac_general": "Bac général", "repartition_admis_bac_techno": "Bac technologique",
               "repartition_admis_bac_pro": "Bac professionnel", "repartition_admis_autres": "Autres diplômes"}


def lire_psup(h: str) -> dict:
    """Chiffres affichés par une fiche Parcoursup : {champ: {"valeur", "annee"?, "libelle"}}.

    La répartition par bac n'est lue que dans le bloc qui suit « Répartition par type de bac des N candidats
    admis » : les mêmes mots (« Bac général ») apparaissent plus bas dans le sélecteur de profil, sans chiffre."""
    t = texte_page(h)
    out: dict[str, dict] = {}
    for champ, (libelle, motif) in MOTIFS_PSUP.items():
        m = re.search(motif, t)
        if m:
            out[champ] = {"valeur": nombre(m.group(1)), "libelle": libelle}
            if m.lastindex and m.lastindex >= 2:
                out[champ]["annee"] = int(m.group(2))
    m = re.search(MOTIFS_PSUP["admis_repartition"][1], t)
    if m:
        bloc = t[m.end():m.end() + 300]
        for champ, lib in REPARTITION.items():
            r = re.match(r".*?" + re.escape(lib) + r" (\d+) %", bloc)
            if r:
                out[champ] = {"valeur": int(r.group(1)), "libelle": f"{lib} N %", "annee": out["admis_repartition"]["annee"]}
    return out


# MonMaster : clé de l'API -> (champ, libellé affiché sur la fiche)
CLES_MM = {
    "tauxAcces": ("taux_acces", "Taux d’accès à la formation N %"),
    "rangDernierAppele": ("rang_dernier_appele", "Rang du dernier appelé lors de la campagne précédente N"),
    "nbCandidaturesConfirmees": ("candidatures_campagne_precedente", "Nombre de candidatures lors de la campagne précédente N"),
    "tauxClasseeCandidature": ("taux_candidatures_classees", "Taux de candidats classés N %"),
    "tauxPropositionAdmissionClassee": ("taux_propositions_parmi_classes", "Taux de propositions d’admission parmi les classés N %"),
}


def pourcentage_affiche(fraction: float) -> int:
    """Le pourcentage entier que la fiche affiche : arrondi au demi supérieur, en décimal exact.

    Mesure du 25/09 (rendu réel de deux fiches, _orientai-ref/.../masters/cache/rendu_1501350CJ2XZ.txt et
    rendu_1501637P1WQN.txt) : 0,125 s'affiche 13 %, 0,165 s'affiche 17 %. `round()` de Python arrondit au pair (12)
    et `fraction * 100` en flottant donne 14,4999... pour 0,145 : les deux se trompaient."""
    from decimal import ROUND_HALF_UP, Decimal
    return int((Decimal(str(fraction)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def lire_mm(contenu: list[dict], ifc: str) -> dict | None:
    """Chiffres de la fiche d'un master dans la réponse de l'API, None si le master n'y est pas (pas de fiche de
    la campagne en cours). Les taux de l'API sont des fractions (0.12) ; la fiche les affiche en % entiers."""
    f = next((x for x in contenu if x.get("ifc") == ifc), None)
    if f is None:
        return None
    out = {}
    if f.get("col") is not None:
        out["capacite_accueil"] = {"valeur": f["col"], "libelle": "CAPACITÉ D’ACCUEIL N étudiant(s)"}
    for cle, (champ, libelle) in CLES_MM.items():
        v = (f.get("indicateursAnneeDerniere") or {}).get(cle)
        if v is None:
            continue
        out[champ] = {"valeur": pourcentage_affiche(v) if cle.startswith("taux") else v, "libelle": libelle}
    return out


class Releve:
    """Cache d'un relevé et son manifeste. `manifeste.json` : {fichier: {sha256, releve_le, statut, url}}."""

    def __init__(self, dossier: Path, pause_s: float = PAUSE_S, ouvrir=urllib.request.urlopen, horloge=time):
        self.dossier = Path(dossier)
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.chemin_manifeste = self.dossier / "manifeste.json"
        self.manifeste = json.loads(self.chemin_manifeste.read_text()) if self.chemin_manifeste.exists() else {}
        self.pause_s, self.ouvrir, self.horloge = pause_s, ouvrir, horloge
        self._dernier = float("-inf")  # la première requête n'attend pas

    def _attendre(self) -> None:
        reste = self.pause_s - (self.horloge.monotonic() - self._dernier)
        if reste > 0:
            self.horloge.sleep(reste)
        self._dernier = self.horloge.monotonic()

    def _inscrire(self, nom: str, url: str, corps: bytes | None, statut: int | str) -> None:
        entree = {"url": url, "statut": statut,
                  "releve_le": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if corps is not None:
            (self.dossier / nom).parent.mkdir(parents=True, exist_ok=True)
            (self.dossier / nom).write_bytes(corps)
            entree["sha256"] = hashlib.sha256(corps).hexdigest()
        self.manifeste[nom] = entree
        self.chemin_manifeste.write_text(json.dumps(self.manifeste, ensure_ascii=False, indent=0, sort_keys=True))

    def obtenir(self, nom: str, url: str, donnees: bytes | None = None) -> bytes | None:
        """Le contenu en cache, sinon une requête (après la pause). None si la page a échoué (inscrit)."""
        if nom in self.manifeste and self.manifeste[nom].get("sha256"):
            return (self.dossier / nom).read_bytes()
        self._attendre()
        entetes = {"User-Agent": AGENT}
        if donnees is not None:
            entetes |= {"Content-Type": "application/json", "Accept": "application/json"}
        req = urllib.request.Request(url, data=donnees, headers=entetes, method="POST" if donnees else "GET")
        try:
            corps = self.ouvrir(req, timeout=30).read()
        except urllib.error.HTTPError as e:
            self._inscrire(nom, url, None, e.code)
            return None
        except Exception as e:  # noqa: BLE001 - réseau : inscrit, jamais masqué
            self._inscrire(nom, url, None, f"{type(e).__name__}: {e}"[:200])
            return None
        self._inscrire(nom, url, corps, 200)
        return corps

    def empreinte(self) -> str:
        """sha256 du manifeste canonique (noms, sha256 et statuts ; sans les dates)."""
        canon = {k: [v.get("sha256"), v.get("statut")] for k, v in sorted(self.manifeste.items())}
        return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()


def page_psup(releve: Releve, code: str) -> bytes | None:
    return releve.obtenir(f"psup/{code}.html", URL_PSUP.format(code))


def reponse_mm(releve: Releve, uai: str, inm: str) -> list[dict] | None:
    corps = releve.obtenir(f"mm/{uai}_{inm}.json", URL_MM, json.dumps({"uai": uai, "inm": inm}).encode())
    return None if corps is None else json.loads(corps).get("content", [])
