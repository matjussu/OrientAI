"""Les outils du cerveau v2 (CONTRAT-etape3, sections 3 et 4) : enveloppes de `src/base_c/outils.py` + 3 nouveaux.

Chaque outil = un modèle Pydantic (`extra="forbid"`) : son schéma JSON est la description envoyée au modèle, et il
valide ce que le modèle renvoie. Une valeur hors liste lève une erreur qui nomme les valeurs admises les plus proches.
`src/base_c/outils.py` n'est pas modifié.

Chaque exécution rend un `Resultat` : le texte que voit le modèle (format C du banc E, `src/eval/format_d.py`), et
les valeurs chiffrées de ce texte, structurées (valeur, unité, fiche, clé, source), que le vérificateur consulte.

Levier de falsification (règle 9) : ORIENTIA_SABOTAGE_V2=essentiel_tout fait rendre toute la fiche par défaut.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.base_c import outils as bc
from src.eval.format_d import INSERTION_RENDUE, Formats
from src.v2.profil import MettreAJourProfil

SIGLES = {k: v for k, v in json.loads((Path(__file__).with_name("sigles.json")).read_text(encoding="utf-8")).items()
          if not k.startswith("_")}

# Essentiel de `lire_fiche` (CONTRAT-etape3 section 4, choix C1 et C2 de Matteo du 25/09, Telegram 10783). Mesure :
# `python -m src.eval.essentiel_fiche`, qui importe cette constante.
ESSENTIEL = frozenset({
    "taux_acces", "places", "capacite_accueil", "repartition_admis_bac_general", "repartition_admis_bac_techno",
    "repartition_admis_bac_pro", "candidats_ont_postule",
    "passage_mmopk_1_ou_2_ans_national", "passage_pass_las_ensemble_national", "sante.reforme_2027",
    "insertion",
})
# Notions comparées par défaut par `comparer` : les chiffres de l'essentiel.
COMPARER_DEFAUT = ("taux_acces", "places", "capacite_accueil", "repartition_admis_bac_general",
                   "repartition_admis_bac_techno", "repartition_admis_bac_pro", "candidats_ont_postule")
UNITE_VERIF = {"%": "pct", "EUR": "eur", "places": "places"}
INSERTION_UNITE = {"%": "pct", "euros": "eur"}   # unités de `format_d.INSERTION_RENDUE` vérifiables
AUTRES_MAX = 12
SABOTAGES = ("essentiel_tout",)

TypeFormation = Literal["pass", "las", "licence", "but", "bts", "cpge", "cupge", "ifsi", "diplome_sante",
                        "ecole_ingenieur", "titre_pro"]


def notion(cle: str) -> str:
    return cle.split("@", 1)[0]


def sabotage() -> str | None:
    s = os.environ.get("ORIENTIA_SABOTAGE_V2") or None
    return s if s in SABOTAGES else None


# ── Schémas des outils ─────────────────────────────────────────────────────────────────────
class _Outil(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PresDe(_Outil):
    commune: str = Field(max_length=80, description="nom de la commune (ou son code INSEE) ; inutile d'appeler "
                                                    "trouver_commune avant")
    departement: str | None = Field(None, max_length=3, description="code du département, pour une commune homonyme")
    rayon_km: float = Field(gt=0, le=300)


class Tri(_Outil):
    champ: str = Field(description="taux_acces, places, candidats_ont_postule, distance... (liste dans l'erreur)")
    sens: Literal["asc", "desc"] = "desc"


class ChercherFormations(_Outil):
    """Formations post-bac (Parcoursup et apprentissage) qui passent TOUS les filtres. Plusieurs types et plusieurs
    filières se combinent dans un seul appel. Rend le nombre total, si la liste est tronquée, et combien de formations
    sont écartées faute de valeur."""
    types: list[TypeFormation] | None = Field(None, description="« licence » inclut les LAS")
    filieres: list[str] | None = Field(None, description="noms de filière, ex. « Informatique », « Services "
                                       "informatiques aux organisations » ; un nom inconnu renvoie les noms proches, "
                                       "inutile d'appeler lister_valeurs avant")
    intitule_contient: str | None = Field(None, max_length=80)
    apprentissage: bool | None = None
    statut: Literal["public", "prive"] | None = None
    communes: list[str] | None = Field(None, max_length=20, description="noms de communes (ou codes INSEE)")
    departements: list[str] | None = Field(None, max_length=20, description="codes de département, ex. 63")
    regions: list[str] | None = Field(None, max_length=18)
    pres_de: PresDe | None = None
    taux_acces_min: float | None = Field(None, ge=0, le=100, description="taux d'accès >= cette valeur")
    taux_acces_max: float | None = Field(None, ge=0, le=100, description="taux d'accès < cette valeur")
    places_min: float | None = Field(None, ge=0)
    part_bac_techno_min: float | None = Field(None, ge=0, le=100, description="part des admis néo-bacheliers techno >=")
    part_bac_pro_min: float | None = Field(None, ge=0, le=100, description="part des admis néo-bacheliers pro >=")
    session: Literal["2023", "2024", "2025"] = "2025"
    tri: Tri | None = None
    limite: int = Field(20, ge=1, le=50)


class ChercherMasters(_Outil):
    """Masters MonMaster (informatique et maths) qui passent tous les filtres."""
    mention_contient: str | None = Field(None, max_length=80)
    secteurs: list[str] | None = None
    regions_academiques: list[str] | None = None
    departements: list[str] | None = Field(None, max_length=20)
    pres_de: PresDe | None = None
    alternance: bool | None = None
    capacite_min: float | None = Field(None, ge=0)
    tri: Tri | None = None
    limite: int = Field(20, ge=1, le=50)


class TrouverCommune(_Outil):
    """Résout un nom de commune ; plusieurs homonymes = plusieurs candidats."""
    nom: str = Field(min_length=1, max_length=80)
    departement: str | None = Field(None, max_length=3)


class ListerValeurs(_Outil):
    """Valeurs exactes admises par un filtre, avec le nombre de formations."""
    champ: Literal["type", "filiere", "region", "departement", "region_academique", "secteur_master"]
    types: list[TypeFormation] | None = None


class LireFiche(_Outil):
    """Chiffres d'une formation, chacun avec sa source, son année et la raison d'un « non disponible ». Par défaut
    l'essentiel (taux d'accès, places, répartition des admis par bac, candidats, insertion) ; detail=true pour tout."""
    id: str = Field(max_length=40, description="identifiant de la fiche, ex. psup:7596")
    detail: bool = False


class TrouverFormation(_Outil):
    """Retrouve une formation NOMMÉE par l'élève (« le BUT info de Lens », « MP2I à Clemenceau », « l'IUT Lyon 1 »).
    Rend au plus 10 candidats avec leur identifiant, à lire ensuite avec lire_fiche."""
    texte: str = Field(min_length=2, max_length=200)
    commune: str | None = Field(None, max_length=80)
    types: list[TypeFormation] | None = Field(None, max_length=11)


class Comparer(_Outil):
    """2 à 5 formations côte à côte : mêmes chiffres, mêmes années, chacun sourcé."""
    ids: list[str] = Field(min_length=2, max_length=5)
    champs: list[str] | None = Field(None, max_length=15, description="notions à comparer ; défaut : l'essentiel")


SCHEMAS: dict[str, type[BaseModel]] = {
    "chercher_formations": ChercherFormations, "chercher_masters": ChercherMasters,
    "trouver_formation": TrouverFormation, "lire_fiche": LireFiche, "comparer": Comparer,
    "trouver_commune": TrouverCommune, "lister_valeurs": ListerValeurs, "mettre_a_jour_profil": MettreAJourProfil,
}


def catalogue() -> list[dict]:
    """Description envoyée au modèle, tirée des schémas Pydantic."""
    return [{"type": "function", "function": {"name": nom, "description": (m.__doc__ or "").strip(),
                                              "parameters": m.model_json_schema()}}
            for nom, m in SCHEMAS.items()]


# ── Résultat d'un appel ────────────────────────────────────────────────────────────────────
@dataclass
class Resultat:
    texte: str
    valeurs: list[dict] = field(default_factory=list)   # {valeur, unite (pct|eur|places), id, cle, source_id}
    ids: list[str] = field(default_factory=list)        # formations rendues
    meta: dict = field(default_factory=dict)
    erreur: str | None = None


def _erreur_validation(e: ValidationError, schema: type[BaseModel]) -> str:
    morceaux = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        attendues = (err.get("ctx") or {}).get("expected")
        if attendues and isinstance(err.get("input"), str):
            admises = re.findall(r"'([^']+)'", attendues)
            proches = difflib.get_close_matches(err["input"], admises, n=5, cutoff=0.4)
            msg += f" ; valeurs proches : {proches}" if proches else ""
        if err["type"] == "extra_forbidden":
            proches = difflib.get_close_matches(str(err["loc"][-1]), list(schema.model_fields), n=3, cutoff=0.5)
            msg = f"paramètre inconnu ; paramètres admis proches : {proches or sorted(schema.model_fields)}"
        morceaux.append(f"{loc} : {msg}")
    return "paramètres invalides : " + " | ".join(morceaux)


# ── Normalisation pour trouver_formation ───────────────────────────────────────────────────
_VIDES = {"le", "la", "les", "de", "du", "des", "d", "l", "un", "une", "a", "au", "aux", "en", "et", "ou", "pour",
          "sur", "dans", "the", "of", "site", "campus"}


def normaliser(texte: str) -> str:
    s = (texte or "").replace("œ", "oe").replace("Œ", "OE").lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\b(?:[a-z]\.){2,}[a-z]?\.?", lambda m: m.group(0).replace(".", ""), s)  # I.U.T. -> iut
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", s)  # lyon1 -> lyon 1
    return re.sub(r"\s+", " ", s).strip()


def termes(texte: str) -> list[list[list[str]]]:
    """Termes de la requête ; chaque terme = ses lectures (sigle déplié), chaque lecture = une suite de mots."""
    out = []
    for mot in normaliser(texte).split():
        if mot in _VIDES:
            continue
        lectures = [lec.split() for lec in SIGLES.get(mot, [])] or [[mot]]
        if [mot] not in lectures and mot not in SIGLES:
            lectures.append([mot])
        out.append(lectures)
    return out


# ── Les outils ─────────────────────────────────────────────────────────────────────────────
class Outils:
    """Une connexion SQLite par fil (sqlite3 ne partage pas une connexion entre fils)."""

    def __init__(self, chemin_base: Path | str = bc.BASE_DEFAUT):
        self.chemin = Path(chemin_base)
        self._local = threading.local()
        b = bc.Base.ouvrir(self.chemin)
        self.notions_base = {r[0] for r in b.con.execute("SELECT champ FROM champ")}
        self.libelles = {r[0]: r[1] for r in b.con.execute("SELECT champ, libelle FROM champ")}
        self.index = self._indexer(b)
        b.fermer()

    # connexions
    @property
    def base(self) -> bc.Base:
        if getattr(self._local, "base", None) is None:
            self._local.base = bc.Base.ouvrir(self.chemin)
            self._local.formats = Formats(self._local.base, [], sabotage="")
        return self._local.base

    @property
    def formats(self) -> Formats:
        self.base  # noqa: B018 - ouvre la connexion du fil
        return self._local.formats

    @staticmethod
    def _indexer(b: bc.Base) -> list[dict]:
        lieux: dict[str, list[dict]] = {}
        for r in b.con.execute("SELECT id, commune, code_insee FROM lieu ORDER BY id, rang"):
            lieux.setdefault(r["id"], []).append(dict(r))
        out = []
        for f in b.con.execute("SELECT id, intitule, etablissement, filiere, specialite, type, type_libelle, espace "
                               "FROM formation ORDER BY id"):
            ls = lieux.get(f["id"], [])
            botte = " ".join(filter(None, [f["intitule"], f["etablissement"], f["filiere"], f["specialite"], f["type"],
                                           f["type_libelle"], *[x["commune"] for x in ls]]))
            out.append({"id": f["id"], "intitule": f["intitule"], "etablissement": f["etablissement"],
                        "type": f["type"], "espace": f["espace"], "commune": (ls or [{}])[0].get("commune"),
                        "codes_insee": {x["code_insee"] for x in ls}, "mots": set(normaliser(botte).split()),
                        "etab_norm": normaliser(f["etablissement"] or "")})
        return out

    # exécution
    def executer(self, nom: str, arguments: str | dict | None, etat=None) -> Resultat:
        if nom not in SCHEMAS:
            proches = difflib.get_close_matches(nom, list(SCHEMAS), n=3, cutoff=0.4)
            return Resultat(texte=f"erreur : outil {nom!r} inconnu ; outils proches : {proches}", erreur="outil_inconnu")
        schema = SCHEMAS[nom]
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
            if isinstance(args, str):   # arguments encodés deux fois (palier 0, F-R01, 7e appel)
                args = json.loads(args)
            params = schema.model_validate(_objets_decodes(args, schema))
        except ValueError as e:
            texte = (_erreur_validation(e, schema) if isinstance(e, ValidationError)
                     else "erreur : arguments illisibles (JSON attendu)")
            return Resultat(texte=f"erreur : {texte}", erreur="parametres_invalides")
        try:
            return getattr(self, nom)(params, etat)
        except bc.FiltreInvalide as e:
            return Resultat(texte=f"erreur : {e}", erreur="filtre_invalide")

    # résolution de communes (noms ou codes INSEE)
    def _commune(self, nom: str, departement: str | None = None) -> str:
        if re.fullmatch(r"\d[\dAB]\d{3}", nom.strip()):
            return nom.strip()
        cands = bc.trouver_commune(self.base, nom, departement)
        if len(cands) == 1:
            return cands[0]["code_insee"]
        if not cands:
            cles = [r[0] for r in self.base.con.execute("SELECT DISTINCT nom FROM commune")]
            proches = difflib.get_close_matches(nom, cles, n=5, cutoff=0.7)
            raise bc.FiltreInvalide(f"commune {nom!r} introuvable ; communes proches : {proches}")
        liste = ", ".join(f"{c['nom']} ({c['code_departement']}, {c['code_insee']})" for c in cands)
        raise bc.FiltreInvalide(f"commune {nom!r} homonyme : {liste} ; préciser le département ou le code INSEE")

    def _rendu_recherche(self, res: dict) -> Resultat:
        f = self.formats
        ap = res["filtres_appliques"]
        entete = [f"Filtres appliqués : {json.dumps(ap, ensure_ascii=False)}",
                  f"{res['nb_resultats']} formation(s) trouvée(s)"
                  + (f", liste tronquée aux {res['limite']} premières" if res["tronque"] else "")
                  + (f" ; {res['ecartees_non_disponible']} écartée(s) faute de valeur publiée"
                     if res["ecartees_non_disponible"] else "")]
        sources: list[str] = []
        lignes, valeurs, ids = [], [], []
        for it in res["resultats"]:
            ids.append(it["id"])
            dist = f" | {str(it['distance_km']).replace('.', ',')} km" if it.get("distance_km") is not None else ""
            chiffres = [f._ligne_champ(ch, ent, sources, avec_definition=False)[2:]
                        for ch, ent in f._par_champ(it["valeurs"]).items()]
            lignes.append(f"- [{it['id']}] {it['intitule']} | {it['etablissement']} | {it['commune']}{dist}"
                          + (" : " + " ; ".join(chiffres) if chiffres else ""))
            valeurs += _valeurs_structurees(it["id"], it["valeurs"])
        texte = "\n".join(entete + lignes + ([f._legende(sources)] if sources else []))
        meta = {k: res[k] for k in ("nb_resultats", "tronque", "limite", "ecartees_non_disponible")} | {"filtres": ap}
        return Resultat(texte=texte, valeurs=valeurs, ids=ids, meta=meta)

    def _pres_de(self, p: PresDe | None) -> dict | None:
        return None if p is None else {"code_insee": self._commune(p.commune, p.departement), "rayon_km": p.rayon_km}

    def chercher_formations(self, p: ChercherFormations, etat=None) -> Resultat:
        res = bc.chercher_formations(
            self.base, types=p.types, filieres=p.filieres, intitule_contient=p.intitule_contient,
            apprentissage=p.apprentissage, statut=p.statut,
            communes=[self._commune(c) for c in p.communes] if p.communes else None, departements=p.departements,
            regions=p.regions, pres_de=self._pres_de(p.pres_de), taux_acces_min=p.taux_acces_min,
            taux_acces_max=p.taux_acces_max, places_min=p.places_min, part_bac_techno_min=p.part_bac_techno_min,
            part_bac_pro_min=p.part_bac_pro_min, session=p.session, tri=p.tri.model_dump() if p.tri else None,
            limite=p.limite)
        return self._rendu_recherche(res)

    def chercher_masters(self, p: ChercherMasters, etat=None) -> Resultat:
        res = bc.chercher_masters(
            self.base, mention_contient=p.mention_contient, secteurs=p.secteurs,
            regions_academiques=p.regions_academiques, departements=p.departements, pres_de=self._pres_de(p.pres_de),
            alternance=p.alternance, capacite_min=p.capacite_min, tri=p.tri.model_dump() if p.tri else None,
            limite=p.limite)
        return self._rendu_recherche(res)

    def trouver_commune(self, p: TrouverCommune, etat=None) -> Resultat:
        c = bc.trouver_commune(self.base, p.nom, p.departement)
        if not c:
            return Resultat(texte=f"aucune commune nommée {p.nom!r}", meta={"nb": 0})
        return Resultat(texte="\n".join(f"- {x['nom']} : code INSEE {x['code_insee']}, département "
                                        f"{x['code_departement']}, {x['region']}" for x in c), meta={"nb": len(c)})

    def lister_valeurs(self, p: ListerValeurs, etat=None) -> Resultat:
        v = bc.lister_valeurs(self.base, p.champ, p.types)
        return Resultat(texte=f"{p.champ} : " + " ; ".join(f"{x} ({n})" for x, n in v), meta={"nb": len(v)})

    def lire_fiche(self, p: LireFiche, etat=None) -> Resultat:
        f = self.formats
        fiche = bc.lire_fiche(self.base, p.id.strip().strip("[]"))
        tout = fiche["valeurs"]
        detail = p.detail or sabotage() == "essentiel_tout"
        gardees = tout if detail else {k: v for k, v in tout.items() if notion(k) in ESSENTIEL}
        sources: list[str] = []
        lignes = [f._entete(fiche)]
        for champ, entrees in f._par_champ(gardees).items():
            lignes.append(f._ligne_champ(champ, entrees, sources, avec_definition=True))
        valeurs = _valeurs_structurees(fiche["formation"]["id"], gardees)
        if detail or "insertion" in gardees:
            for lg in fiche["insertion"]:
                chiffres = [f"{lib} {_fr(lg[col])} {u}" for col, lib, u in INSERTION_RENDUE if lg.get(col) is not None]
                if chiffres:
                    lignes.append(f"- Insertion ({lg['dispositif']}, promotion {lg['promotion']}, {lg['diplome']}, "
                                  f"{lg['etablissement']}, {f._renvoi(sources, lg['source_id'])}) : "
                                  + " ; ".join(chiffres))
                valeurs += [{"valeur": float(lg[col]), "unite": INSERTION_UNITE[u],
                             "id": fiche["formation"]["id"], "cle": f"insertion.{col}", "source_id": lg["source_id"]}
                            for col, _, u in INSERTION_RENDUE if lg.get(col) is not None and u in INSERTION_UNITE]
        if detail:
            for al in fiche["alternance_liens"]:
                cap = f", {_fr(al['capacite'])} places" if al.get("capacite") is not None else ""
                lignes.append(f"- Existe en apprentissage : {al['etablissement']}, {al['commune']}{cap} "
                              f"({al['id_apprentissage']})")
                if al.get("capacite") is not None:
                    valeurs.append({"valeur": float(al["capacite"]), "unite": "places", "id": al["id_apprentissage"],
                                    "cle": "alternance_lien.capacite", "source_id": None})
        else:
            autres = sorted({notion(k) for k in tout} - ESSENTIEL - {"cout"})
            if autres:
                noms = [self.libelles.get(n) or n for n in autres]
                reste = f", et {len(noms) - AUTRES_MAX} autres" if len(noms) > AUTRES_MAX else ""
                lignes.append(f"- {len(noms)} autres chiffres sur cette fiche (lire_fiche avec detail=true), dont : "
                              + ", ".join(noms[:AUTRES_MAX]) + reste)
        lignes.append(f._legende(sources))
        return Resultat(texte="\n".join(lignes), valeurs=valeurs, ids=[fiche["formation"]["id"]],
                        meta={"detail": detail, "valeurs_rendues": len(gardees), "valeurs_fiche": len(tout)})

    def trouver_formation(self, p: TrouverFormation, etat=None) -> Resultat:
        ts = termes(p.texte)
        if not ts:
            raise bc.FiltreInvalide("texte sans mot utile : donner l'intitulé, l'établissement ou la ville")
        codes = None
        if p.commune:
            cands = bc.trouver_commune(self.base, p.commune)
            if not cands and not re.fullmatch(r"\d[\dAB]\d{3}", p.commune.strip()):
                self._commune(p.commune)  # lève l'erreur avec les communes proches
            codes = {c["code_insee"] for c in cands} or {p.commune.strip()}
        types = set(bc._deplier_types(p.types)) if p.types else None
        cands = []
        for f in self.index:
            if types and f["type"] not in types:
                continue
            if codes is not None and not (f["codes_insee"] & codes):
                continue
            trouves = [t for t in ts if any(all(m in f["mots"] for m in lec) for lec in t)]
            if trouves:
                cands.append((len(trouves) / len(ts), f, trouves))
        cands.sort(key=lambda x: (-x[0], x[1]["id"]))
        garde = cands[:10]
        out = [{"id": f["id"], "intitule": f["intitule"], "etablissement": f["etablissement"], "commune": f["commune"],
                "type": f["type"], "score": round(s, 2),
                "termes_trouves": [" / ".join(" ".join(lec) for lec in t) for t in tr]} for s, f, tr in garde]
        meta = {"requete_normalisee": normaliser(p.texte), "nb_candidats": len(cands), "tronque": len(cands) > 10}
        if not out:
            etabs = sorted({f["etablissement"] for f in self.index})
            proches = difflib.get_close_matches(p.texte, etabs, n=5, cutoff=0.3)
            return Resultat(texte=f"aucune formation ne correspond à {p.texte!r} ; établissements proches : {proches}",
                            meta=meta)
        lignes = [f"{len(cands)} candidat(s)" + (", les 10 plus proches" if len(cands) > 10 else "")
                  + " (à lire avec lire_fiche) :"]
        lignes += [f"- [{c['id']}] {c['intitule']} | {c['etablissement']} | {c['commune']} (score {c['score']})"
                   for c in out]
        return Resultat(texte="\n".join(lignes), ids=[c["id"] for c in out], meta=meta | {"candidats": out})

    def comparer(self, p: Comparer, etat=None) -> Resultat:
        ids = [i.strip().strip("[]") for i in p.ids]
        if len(set(ids)) != len(ids):
            raise bc.FiltreInvalide("identifiants en double")
        champs = list(p.champs or COMPARER_DEFAUT)
        for c in champs:
            if c not in self.notions_base:
                proches = difflib.get_close_matches(c, sorted(self.notions_base), n=5, cutoff=0.5)
                raise bc.FiltreInvalide(f"champ {c!r} inconnu ; champs proches : {proches}")
        fiches = {}
        for i in ids:
            try:
                fiches[i] = bc.lire_fiche(self.base, i)
            except bc.FiltreInvalide:
                raise bc.FiltreInvalide(f"formation {i!r} inconnue ; la retrouver avec trouver_formation") from None
        f = self.formats
        sources: list[str] = []
        lignes = ["Formations comparées :"] + [
            f"- [{i}] {fi['formation']['intitule']} | {fi['formation']['etablissement']} | "
            f"{(fi['lieux'] or [{}])[0].get('commune')}" for i, fi in fiches.items()]
        valeurs = []
        for c in champs:
            cles = sorted({k for fi in fiches.values() for k in fi["valeurs"] if notion(k) == c},
                          key=lambda k: -int(k.partition("@")[2] or 0))
            for cle in cles:
                session = cle.partition("@")[2]
                morceaux = []
                for i, fi in fiches.items():
                    v = fi["valeurs"].get(cle)
                    if v is None:
                        a_la_notion = any(notion(k) == c for k in fi["valeurs"])
                        morceaux.append(f"[{i}] " + ("non publié pour cette session" if a_la_notion
                                                     else "sans objet pour cette formation"))
                    elif v["statut"] != "disponible":
                        morceaux.append(f"[{i}] non disponible ({v.get('raison')})")
                    else:
                        morceaux.append(f"[{i}] {f._valeur_lisible(v)} ({v.get('millesime')}, "
                                        f"{f._renvoi(sources, v.get('source_id'))})")
                        valeurs += _valeurs_structurees(i, {cle: v})
                titre = (self.libelles.get(c) or c) + (f", session {session}" if session else "")
                lignes.append(f"- {titre} : " + " ; ".join(morceaux))
        lignes.append(f._legende(sources))
        return Resultat(texte="\n".join(lignes), valeurs=valeurs, ids=ids, meta={"champs": champs})

    def mettre_a_jour_profil(self, p: MettreAJourProfil, etat=None) -> Resultat:
        code = self._commune(p.commune) if p.commune else None
        if etat is not None:
            etat.profil = etat.profil.fusionner(p, code)
            profil = etat.profil.pour_le_modele()
        else:
            profil = p.model_dump(exclude_none=True)
        return Resultat(texte="Profil enregistré : " + json.dumps(profil, ensure_ascii=False), meta={"profil": profil})


def _objets_decodes(args: dict, schema: type[BaseModel]) -> dict:
    """GLM 5.3 envoie parfois un paramètre objet ou liste sous forme de chaîne JSON (« pres_de »: "{\"commune\": ...}",
    constaté au palier 0 du 25/09 : 4 appels refusés de suite sur F-R01). Une chaîne qui se lit comme un objet ou une
    liste JSON, pour un paramètre qui n'est pas une chaîne, est décodée ; tout le reste passe tel quel à Pydantic."""
    if not isinstance(args, dict):
        return args
    out = dict(args)
    for k, v in args.items():
        champ = schema.model_fields.get(k)
        if champ is None or not isinstance(v, str) or v.strip()[:1] not in ("{", "["):
            continue
        if champ.annotation in (str, str | None):
            continue
        try:
            out[k] = json.loads(v)
        except ValueError:
            pass
    return out


def _fr(v) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v}".replace(".", ",")


def _valeurs_structurees(id_: str, valeurs: dict) -> list[dict]:
    """Valeurs chiffrées vérifiables (pct, eur, places) d'un dictionnaire de valeurs rendu au modèle."""
    out = []
    for cle, v in valeurs.items():
        u = UNITE_VERIF.get(v.get("unite"))
        if u and v.get("statut") == "disponible" and isinstance(v.get("valeur"), (int, float)) \
                and not isinstance(v.get("valeur"), bool):
            out.append({"valeur": float(v["valeur"]), "unite": u, "id": id_, "cle": cle, "source_id": v.get("source_id")})
    return out
