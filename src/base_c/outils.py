"""Fonctions à filtres fermés sur la base de l'étape C (contrat §8, bornes de la v0.1).

Le modèle n'écrit jamais de SQL : il appelle ces fonctions, dont chaque filtre est typé et borné.
Chaque résultat renvoie les filtres effectivement appliqués (normalisés), pour que l'écran de Matteo
affiche « filtres traduits ».

Bornes, fixées une fois pour toutes :
- `*_min` inclusif (>=), `*_max` strict (<), comparés sur la valeur publiée, sans arrondi ;
- `pres_de` : distance <= rayon, en km non arrondis (l'arrondi à 0,1 km ne sert qu'à l'affichage) ;
- une formation dont le chiffre filtré est « non disponible » ne passe pas le filtre, et elle est
  comptée dans `ecartees_non_disponible`.
"""
from __future__ import annotations

import difflib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.base_c import SANS_SESSION, haversine_km
from src.collect.communes import cle_nom

BASE_DEFAUT = Path(__file__).resolve().parents[2] / "data/processed/base_etape_c.sqlite"

TYPES = ("pass", "las", "licence", "but", "bts", "cpge", "cupge", "ifsi", "diplome_sante",
         "ecole_ingenieur", "titre_pro", "master", "autre")
# « licence » inclut la LAS : une LAS est une licence avec option accès santé (règle du gate C).
DEPLIAGE_TYPES = {"licence": ("licence", "las")}
TRIS_POSTBAC = ("taux_acces", "places", "voeux_totaux", "part_bac_general", "part_bac_techno", "part_bac_pro", "distance")
TRIS_MASTERS = ("capacite", "candidats_pp", "acceptes_total", "distance")
LIMITE_MAX = 50
RAYON_MAX_KM = 300.0
CHAMPS_DEFAUT_POSTBAC = ("taux_acces", "places")
CHAMPS_DEFAUT_MASTERS = ("capacite", "candidats_pp")


class FiltreInvalide(ValueError):
    """Un filtre hors de la liste fermée : l'erreur nomme les valeurs admises les plus proches."""


@dataclass
class Base:
    con: sqlite3.Connection

    @classmethod
    def ouvrir(cls, chemin: Path | str = BASE_DEFAUT) -> "Base":
        uri = f"file:{Path(chemin)}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        return cls(con)

    def fermer(self) -> None:
        self.con.close()


# ── Communes et valeurs admises ────────────────────────────────────────────────────────────
def trouver_commune(base: Base, nom: str, departement: str | None = None) -> list[dict]:
    """Communes dont le nom correspond. Plusieurs candidats = au modèle de choisir ou de demander."""
    sql = "SELECT code_insee, nom, code_departement, region FROM commune WHERE cle = ?"
    args: list = [cle_nom(nom)]
    if departement:
        sql += " AND code_departement = ?"
        args.append(departement)
    return [dict(r) for r in base.con.execute(sql + " ORDER BY code_insee", args)]


def lister_valeurs(base: Base, champ: str, types: list[str] | None = None) -> list[tuple[str, int]]:
    """Valeurs exactes admises par un filtre, avec le nombre de formations."""
    colonnes = {"type": "f.type", "filiere": "f.filiere", "region": "l.region", "departement": "l.code_departement",
                "region_academique": "f.region_academique", "secteur_master": "f.domaine_regle"}
    if champ not in colonnes:
        raise FiltreInvalide(f"champ {champ!r} inconnu ; admis : {', '.join(colonnes)}")
    col = colonnes[champ]
    sql = f"SELECT {col} AS v, COUNT(DISTINCT f.id) AS n FROM formation f JOIN lieu l ON l.id = f.id WHERE {col} IS NOT NULL"
    args: list = []
    if types:
        tt = _deplier_types(types)
        sql += f" AND f.type IN ({','.join('?' * len(tt))})"
        args += tt
    return [(r["v"], r["n"]) for r in base.con.execute(sql + f" GROUP BY {col} ORDER BY {col}", args)]


def _deplier_types(types: list[str]) -> list[str]:
    for t in types:
        if t not in TYPES:
            raise FiltreInvalide(f"type {t!r} inconnu ; admis : {', '.join(TYPES)}")
    return sorted({x for t in types for x in DEPLIAGE_TYPES.get(t, (t,))})


def _verifier_liste(base: Base, champ: str, demandees: list[str], types: list[str] | None = None) -> None:
    admises = {v for v, _ in lister_valeurs(base, champ, types)}
    for d in demandees:
        if d not in admises:
            proches = difflib.get_close_matches(d, sorted(admises), n=5, cutoff=0.5)
            raise FiltreInvalide(f"{champ} {d!r} inconnu ; valeurs proches : {proches}")


# ── Recherche ──────────────────────────────────────────────────────────────────────────────
def _centre(base: Base, code_insee: str) -> tuple[float, float, str]:
    r = base.con.execute("SELECT lat, lon, nom FROM commune WHERE code_insee = ?", (code_insee,)).fetchone()
    if r is None or r["lat"] is None:
        raise FiltreInvalide(f"commune {code_insee!r} inconnue ou sans centre ; utiliser trouver_commune")
    return r["lat"], r["lon"], r["nom"]


def _valeurs(base: Base, ids: list[str], champs: list[tuple[str, str]]) -> dict[str, dict[str, dict]]:
    """{id: {"champ@session" ou "champ": {valeur, unite, statut, raison, portee, source_id, millesime, identifiant}}}"""
    out: dict[str, dict[str, dict]] = {i: {} for i in ids}
    if not ids or not champs:
        return out
    for i in range(0, len(ids), 500):
        lot = ids[i:i + 500]
        for champ, session in champs:
            sql = (f"SELECT * FROM valeur WHERE id IN ({','.join('?' * len(lot))}) AND champ = ?"
                   + ("" if session is None else " AND session = ?"))
            args = [*lot, champ] + ([] if session is None else [session])
            for r in base.con.execute(sql, args):
                cle = champ if r["session"] == SANS_SESSION else f"{champ}@{r['session']}"
                out[r["id"]][cle] = {
                    "valeur": r["valeur_num"] if r["valeur_num"] is not None else r["valeur_texte"],
                    "unite": r["unite"], "statut": r["statut"], "raison": r["raison"], "portee": r["portee"],
                    "source_id": r["source_id"], "millesime": r["millesime"], "identifiant": r["identifiant_source"],
                }
    return out


def _parse_champ(base: Base, texte: str, session_defaut: str) -> tuple[str, str | None]:
    """« taux_acces@2023 » -> ("taux_acces", "2023") ; « taux_acces » -> session par défaut si le champ en a."""
    nom, _, s = texte.partition("@")
    r = base.con.execute("SELECT sessions FROM champ WHERE champ = ?", (nom,)).fetchone()
    if r is None:
        raise FiltreInvalide(f"champ {nom!r} inconnu")
    if r["sessions"] == SANS_SESSION:
        return nom, SANS_SESSION
    return nom, s or session_defaut


def _cle(champ: str, session: str | None) -> str:
    return champ if session in (None, SANS_SESSION) else f"{champ}@{session}"


def _rechercher(base: Base, *, espaces: tuple[str, ...], types, filieres, intitule_contient, apprentissage, statut,
                communes, departements, regions, regions_academiques, pres_de, seuils, session, champs, tri, limite,
                champs_defaut, tris_admis, secteurs=None) -> dict:
    if limite < 1 or limite > LIMITE_MAX:
        raise FiltreInvalide(f"limite {limite} hors de [1, {LIMITE_MAX}]")
    appliques: dict = {"session": session}
    sql = ["SELECT f.* FROM formation f WHERE f.espace IN (%s)" % ",".join("?" * len(espaces))]
    args: list = list(espaces)
    if types:
        tt = _deplier_types(types)
        sql.append(f"AND f.type IN ({','.join('?' * len(tt))})")
        args += tt
        appliques["types"] = tt
    if filieres:
        _verifier_liste(base, "filiere", filieres)
        sql.append(f"AND f.filiere IN ({','.join('?' * len(filieres))})")
        args += filieres
        appliques["filieres"] = list(filieres)
    if apprentissage is not None:
        sql.append("AND f.apprentissage = ?")
        args.append(1 if apprentissage else 0)
        appliques["apprentissage"] = bool(apprentissage)
    if statut is not None:
        if statut not in ("public", "prive"):
            raise FiltreInvalide("statut : « public » ou « prive »")
        sql.append("AND f.statut = ?")
        args.append("Public" if statut == "public" else "Privé")
        appliques["statut"] = statut
    if secteurs:
        sql.append(f"AND f.domaine_regle IN ({','.join('?' * len(secteurs))})")
        args += [f"MM:{x}" for x in secteurs]
        appliques["secteurs"] = list(secteurs)
    if regions_academiques:
        _verifier_liste(base, "region_academique", regions_academiques)
        sql.append(f"AND f.region_academique IN ({','.join('?' * len(regions_academiques))})")
        args += regions_academiques
        appliques["regions_academiques"] = list(regions_academiques)
    for nom_filtre, col, liste in (("communes", "code_insee", communes), ("departements", "code_departement", departements),
                                   ("regions", "region", regions)):
        if liste:
            if nom_filtre == "regions":
                _verifier_liste(base, "region", liste)
            sql.append(f"AND EXISTS (SELECT 1 FROM lieu l WHERE l.id = f.id AND l.{col} IN ({','.join('?' * len(liste))}))")
            args += list(liste)
            appliques[nom_filtre] = list(liste)
    lignes = [dict(r) for r in base.con.execute(" ".join(sql) + " ORDER BY f.id", args)]

    if intitule_contient:
        motif = cle_nom(intitule_contient)
        lignes = [r for r in lignes if motif in cle_nom(r["intitule"] or "")]
        appliques["intitule_contient"] = intitule_contient

    distances: dict[str, float | None] = {}
    if pres_de:
        rayon = float(pres_de["rayon_km"])
        if rayon <= 0 or rayon > RAYON_MAX_KM:
            raise FiltreInvalide(f"rayon {rayon} hors de ]0, {RAYON_MAX_KM}]")
        lat0, lon0, nom0 = _centre(base, pres_de["code_insee"])
        appliques["pres_de"] = {"code_insee": pres_de["code_insee"], "commune": nom0, "rayon_km": rayon,
                                "mesure": "à vol d'oiseau, jusqu'au centre de la commune"}
        gardees = []
        for r in lignes:
            d = [haversine_km(l["lat"], l["lon"], lat0, lon0)
                 for l in base.con.execute("SELECT lat, lon FROM lieu WHERE id = ? AND lat IS NOT NULL", (r["id"],))]
            distances[r["id"]] = min(d) if d else None
            if d and min(d) <= rayon:
                gardees.append(r)
        lignes = gardees

    # Seuils : *_min inclusif, *_max strict, valeur publiée sans arrondi.
    ecartees = 0
    champs_seuils = sorted({c for c, _, _ in seuils})
    vals = _valeurs(base, [r["id"] for r in lignes], [(c, session) for c in champs_seuils])
    for champ, sens, borne in seuils:
        appliques[f"{champ}_{sens}"] = borne
        gardees = []
        for r in lignes:
            v = vals[r["id"]].get(_cle(champ, session))
            if v is None or v["statut"] != "disponible":
                ecartees += 1
                continue
            if (sens == "min" and v["valeur"] >= borne) or (sens == "max" and v["valeur"] < borne):
                gardees.append(r)
        lignes = gardees

    demandes = [_parse_champ(base, c, session) for c in (champs or [])]
    defaut = [(c, session) for c in champs_defaut]
    a_rendre = list(dict.fromkeys(defaut + demandes + [(c, session) for c in champs_seuils]))
    if tri and tri["champ"] != "distance":
        a_rendre.append((tri["champ"], session))
        a_rendre = list(dict.fromkeys(a_rendre))
    vals = _valeurs(base, [r["id"] for r in lignes], a_rendre)

    if tri:
        if tri["champ"] not in tris_admis or tri.get("sens", "desc") not in ("asc", "desc"):
            raise FiltreInvalide(f"tri {tri!r} ; champs admis : {', '.join(tris_admis)}, sens asc ou desc")
        if tri["champ"] == "distance" and not pres_de:
            raise FiltreInvalide("tri par distance sans pres_de")
        desc = tri.get("sens", "desc") == "desc"

        def cle_tri(r):
            if tri["champ"] == "distance":
                v = distances.get(r["id"])
            else:
                x = vals[r["id"]].get(_cle(tri["champ"], session))
                v = x["valeur"] if x and x["statut"] == "disponible" else None
            # Non disponible toujours en dernier ; ex aequo départagés par l'identifiant.
            return (v is None, -(v or 0) if desc else (v or 0), r["id"])
        lignes.sort(key=cle_tri)
        appliques["tri"] = {"champ": tri["champ"], "sens": "desc" if desc else "asc"}
    elif pres_de:
        lignes.sort(key=lambda r: (distances.get(r["id"]) is None, distances.get(r["id"]) or 0, r["id"]))

    total = len(lignes)
    lignes = lignes[:limite]
    ids = [r["id"] for r in lignes]
    lieux = {i: [dict(l) for l in base.con.execute("SELECT commune, code_insee, code_departement, region, precision_geo "
                                                   "FROM lieu WHERE id = ? ORDER BY rang", (i,))] for i in ids}
    resultats = []
    for r in lignes:
        item = {"id": r["id"], "intitule": r["intitule"], "etablissement": r["etablissement"], "type": r["type"],
                "filiere": r["filiere"], "apprentissage": bool(r["apprentissage"]),
                "commune": (lieux[r["id"]] or [{}])[0].get("commune"), "lieux": lieux[r["id"]],
                "lien_officiel": r["lien_officiel"], "valeurs": vals[r["id"]]}
        if pres_de:
            item["distance_km"] = round(distances[r["id"]], 1) if distances.get(r["id"]) is not None else None
        resultats.append(item)
    sources_ids = sorted({v["source_id"] for x in resultats for v in x["valeurs"].values() if v["source_id"]})
    sources = {r["source_id"]: {"libelle": r["libelle"], "url": r["url"]}
               for r in base.con.execute(f"SELECT * FROM source WHERE source_id IN ({','.join('?' * len(sources_ids))})", sources_ids)}
    return {"filtres_appliques": appliques, "nb_resultats": total, "tronque": total > limite, "limite": limite,
            "ecartees_non_disponible": ecartees, "resultats": resultats, "sources": sources}


def chercher_formations(base: Base, *, types: list[str] | None = None, filieres: list[str] | None = None,
                        intitule_contient: str | None = None, apprentissage: bool | None = None,
                        statut: str | None = None, communes: list[str] | None = None,
                        departements: list[str] | None = None, regions: list[str] | None = None,
                        pres_de: dict | None = None,
                        taux_acces_min: float | None = None,   # >= (inclusif)
                        taux_acces_max: float | None = None,   # <  (strict)
                        places_min: float | None = None,       # >=
                        part_bac_techno_min: float | None = None,  # >=, part parmi les admis néo-bacheliers
                        part_bac_pro_min: float | None = None,     # >=, idem
                        session: str = "2025", champs: list[str] | None = None, tri: dict | None = None,
                        limite: int = 20) -> dict:
    """Formations post-bac (Parcoursup et apprentissage) qui passent tous les filtres."""
    if session not in ("2023", "2024", "2025"):
        raise FiltreInvalide("session : 2023, 2024 ou 2025")
    seuils = [(c, s, b) for c, s, b in (("taux_acces", "min", taux_acces_min), ("taux_acces", "max", taux_acces_max),
                                         ("places", "min", places_min), ("part_bac_techno", "min", part_bac_techno_min),
                                         ("part_bac_pro", "min", part_bac_pro_min)) if b is not None]
    return _rechercher(base, espaces=("psup", "psup_app"), types=types, filieres=filieres,
                       intitule_contient=intitule_contient, apprentissage=apprentissage, statut=statut,
                       communes=communes, departements=departements, regions=regions, regions_academiques=None,
                       pres_de=pres_de, seuils=seuils, session=session, champs=champs, tri=tri, limite=limite,
                       champs_defaut=CHAMPS_DEFAUT_POSTBAC, tris_admis=TRIS_POSTBAC)


def chercher_masters(base: Base, *, mention_contient: str | None = None, secteurs: list[str] | None = None,
                     regions_academiques: list[str] | None = None, departements: list[str] | None = None,
                     pres_de: dict | None = None, alternance: bool | None = None,
                     capacite_min: float | None = None,  # >=
                     champs: list[str] | None = None, tri: dict | None = None, limite: int = 20) -> dict:
    """Masters MonMaster 2025 (informatique et maths) qui passent tous les filtres."""
    res = _rechercher(base, espaces=("mm",), types=None, filieres=None, intitule_contient=mention_contient,
                      apprentissage=alternance, statut=None, communes=None, departements=departements, regions=None,
                      regions_academiques=regions_academiques, pres_de=pres_de,
                      seuils=[("capacite", "min", capacite_min)] if capacite_min is not None else [],
                      session="2025", champs=champs, tri=tri, limite=limite,
                      champs_defaut=CHAMPS_DEFAUT_MASTERS, tris_admis=TRIS_MASTERS, secteurs=secteurs)
    if "apprentissage" in res["filtres_appliques"]:
        res["filtres_appliques"]["alternance"] = res["filtres_appliques"].pop("apprentissage")
    if "intitule_contient" in res["filtres_appliques"]:
        res["filtres_appliques"]["mention_contient"] = res["filtres_appliques"].pop("intitule_contient")
    return res


def lire_fiche(base: Base, id_: str) -> dict:
    """Tout ce que la base sait d'une formation, chaque chiffre avec sa source, sa portée et sa raison."""
    f = base.con.execute("SELECT * FROM formation WHERE id = ?", (id_,)).fetchone()
    if f is None:
        raise FiltreInvalide(f"formation {id_!r} inconnue")
    valeurs = {}
    for r in base.con.execute("SELECT * FROM valeur WHERE id = ? ORDER BY champ, session", (id_,)):
        valeurs[_cle(r["champ"], r["session"])] = {
            "valeur": r["valeur_num"] if r["valeur_num"] is not None else r["valeur_texte"], "unite": r["unite"],
            "statut": r["statut"], "raison": r["raison"], "portee": r["portee"], "source_id": r["source_id"],
            "millesime": r["millesime"], "identifiant": r["identifiant_source"], "rattachement": r["rattachement"]}
    sids = sorted({v["source_id"] for v in valeurs.values() if v["source_id"]})
    return {
        "formation": dict(f),
        "lieux": [dict(r) for r in base.con.execute("SELECT * FROM lieu WHERE id = ? ORDER BY rang", (id_,))],
        "valeurs": valeurs,
        "insertion": [dict(r) for r in base.con.execute("SELECT * FROM insertion_ligne WHERE id = ? ORDER BY rang", (id_,))],
        "alternance_liens": [dict(r) for r in base.con.execute("SELECT * FROM alternance_lien WHERE id = ?", (id_,))],
        "sources": {r["source_id"]: dict(r) for r in base.con.execute(
            f"SELECT * FROM source WHERE source_id IN ({','.join('?' * len(sids))})", sids)},
    }
