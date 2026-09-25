"""Contrôle « concordance page publique » (contrat results/concordance/CONTRAT.md §5), bloquant, 100 % des formations.

    python -m src.eval.concordance [--base data/processed/base_etape_c.sqlite] [--sortie results/concordance]

Compare, pour chaque formation de la base, ce que voit le modèle (`lire_fiche`, après le filtre « montré au
modèle ») à ce que la page publique affiche, relu dans le cache du relevé. Indépendant du constructeur : le texte
des pages est extrait par `html.parser` (bibliothèque standard), avec des motifs écrits ici ; les réponses de l'API
MonMaster sont lues directement ; la liste des doublons interdits est écrite ici, pas lue dans la table `champ`.
Sans cette indépendance, le contrôle comparerait la base à elle-même.

Chaque formation tombe dans exactement une case : `concordante`, ou un écart résiduel d'une cause du catalogue
`CAUSES`. Un écart hors catalogue, ou un doublon montré au modèle, fait échouer le contrôle (code de sortie 1).

Leviers de falsification (règle 9), à lancer par `--temoins` qui les joue dans le même run que le passage normal :
- base construite avec `ORIENTIA_SABOTAGE_C=concordance_valeur` (un chiffre de page +1) ;
- `ORIENTIA_SABOTAGE_CONCORDANCE=doublon` (un champ non montré remis dans la sortie de `lire_fiche`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
CACHE = RACINE / "data/raw/pages_publiques"
MANIFESTE = RACINE / "results/concordance/manifeste_releve.json"

# Doublons qui ne doivent jamais sortir vers le modèle (contrat §2 et §4), écrits ici indépendamment de la table.
DOUBLONS = {
    "psup": {"admis_bilan_final", "propositions_envoyees_bilan_final", "voeux_toutes_phases_bilan_final",
             "part_bac_general_neobacheliers_bilan_final", "part_bac_techno_neobacheliers_bilan_final",
             "part_bac_pro_neobacheliers_bilan_final", "classes_phase_principale", "places_open_data",
             "voeux_phase_principale@2025", "places_annee_en_cours", "voeux_confirmes_annee_en_cours"},
    "psup_app": {"places_annee_en_cours"},
    "mm": {"capacite_campagne_2025", "candidats_pp_open_data", "candidats_pc_open_data",
           "rang_dernier_appele_pp_open_data"},
}
CAUSES = {
    "page_introuvable": "la page publique n'a pas pu être relevée (statut HTTP au manifeste)",
    "page_sans_bloc_acces": "la page n'affiche pas le bloc des chiffres d'accès (ex. formation en apprentissage, ou nouvelle)",
    "page_vide": "la page répond sans aucun contenu de formation : formation absente de la session en cours (établi le 25/09 "
                 "par la cartographie ESR 2026, results/concordance/pages_vides.json) ; le modèle doit la voir « absente »",
    "master_sans_fiche_annee_en_cours": "le master n'a pas de fiche MonMaster de la campagne en cours",
}


class _Texte(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.morceaux, self._saut = [], 0

    def handle_starttag(self, tag, attrs):
        self._saut += tag in ("script", "style")

    def handle_endtag(self, tag):
        self._saut -= tag in ("script", "style") and self._saut > 0

    def handle_data(self, data):
        if not self._saut and data.strip():
            self.morceaux.append(data.strip())


def texte(h: str) -> str:
    p = _Texte()
    p.feed(h)
    return re.sub(r"\s+", " ", " ".join(p.morceaux))


def _entier(s: str) -> int:
    return int("".join(ch for ch in s if ch.isdigit()))


_NB = r"(?<![0-9])([0-9]{1,3}(?:[\s \xa0][0-9]{3})+|[0-9]+)"
# notion -> (clé vue par le modèle, motif sur le texte de la page)
PAGE_PSUP = {
    "places_offertes": ("places@2025", _NB + r"\s+places offertes par la formation en 2025"),
    "postule": ("candidats_ont_postule@2025", _NB + r"\s+candidats ont postulé à cette formation"),
    "classes": ("candidats_classes@2025", r"a classé\s+" + _NB + r"\s+candidats"),
    "proposition": ("candidats_ont_pu_recevoir_une_proposition@2025", _NB + r"\s+candidats ont pu recevoir une proposition d.admission"),
    "integrer": ("candidats_ont_choisi_d_integrer@2025", _NB + r"\s+candidats ont choisi d.intégrer cette formation"),
}
REPARTITION = {"Bac général": "repartition_admis_bac_general@2025", "Bac technologique": "repartition_admis_bac_techno@2025",
               "Bac professionnel": "repartition_admis_bac_pro@2025", "Autres diplômes": "repartition_admis_autres@2025"}


def chiffres_page_psup(h: str) -> dict[str, int]:
    t = texte(h)
    out = {}
    for _, (cle, motif) in PAGE_PSUP.items():
        m = re.search(motif, t)
        if m:
            out[cle] = _entier(m.group(1))
    m = re.search(r"Répartition par type de bac des\s+" + _NB + r"\s+candidats admis", t)
    if m:
        suite = t[m.end():m.end() + 300]
        for lib, cle in REPARTITION.items():
            r = re.search(re.escape(lib) + r"\s+([0-9]+)\s*%", suite)
            if r:
                out[cle] = int(r.group(1))
    return out


def _pourcent(x: float) -> int:
    """Pourcentage entier affiché (demi supérieur, vu sur le rendu réel du 25/09 : 0,125 -> 13 %), calculé en
    millièmes entiers depuis l'écriture décimale de l'API, sans flottant."""
    entier, _, dec = f"{x:.6f}".partition(".")
    milliemes = int(entier) * 1000 + int(dec[:3])
    return (milliemes + 5) // 10


def chiffres_page_mm(contenu: list[dict], ifc: str) -> dict[str, int] | None:
    fiche = [x for x in contenu if x.get("ifc") == ifc]
    if not fiche:
        return None
    f = fiche[0]
    ind = f.get("indicateursAnneeDerniere") or {}
    out = {}
    if f.get("col") is not None:
        out["capacite_accueil@2026"] = f["col"]
    for cle_api, cle in (("nbCandidaturesConfirmees", "candidatures_campagne_precedente@2025"),
                         ("rangDernierAppele", "rang_dernier_appele@2025")):
        if ind.get(cle_api) is not None:
            out[cle] = ind[cle_api]
    for cle_api, cle in (("tauxAcces", "taux_acces@2025"), ("tauxClasseeCandidature", "taux_candidatures_classees@2025"),
                         ("tauxPropositionAdmissionClassee", "taux_propositions_parmi_classes@2025")):
        if ind.get(cle_api) is not None:
            out[cle] = _pourcent(ind[cle_api])
    return out


def controler(base_chemin: Path) -> dict:
    from src.base_c.outils import Base, lire_fiche
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))["manifeste"]
    base = Base.ouvrir(base_chemin)
    formations = [dict(r) for r in base.con.execute("SELECT id, espace, identifiant_source, uai FROM formation ORDER BY id")]
    cases, ecarts, doublons, compares, places_od = Counter(), [], [], 0, []
    for f in formations:
        vue = lire_fiche(base, f["id"])["valeurs"]
        for cle in vue:
            if cle in DOUBLONS[f["espace"]] or cle.partition("@")[0] in DOUBLONS[f["espace"]]:
                doublons.append({"id": f["id"], "cle": cle})
        if f["espace"] == "mm":
            nom = f"mm/{f['uai']}_{f['identifiant_source'][:8]}.json"
        else:
            nom = f"psup/{f['identifiant_source']}.html"
        e = manifeste.get(nom)
        if not e or not e.get("sha256"):
            cases["page_introuvable"] += 1
            ecarts.append({"id": f["id"], "cause": "page_introuvable", "statut": (e or {}).get("statut")})
            continue
        corps = (CACHE / nom).read_bytes()
        if f["espace"] == "mm":
            page = chiffres_page_mm(json.loads(corps).get("content", []), f["identifiant_source"])
            if page is None:
                marque = (vue.get("fiche_publique_annee_en_cours@2026") or {}).get("valeur")
                cause = "master_sans_fiche_annee_en_cours" if marque == "absente" else "ecart_inexplique"
                cases[cause] += 1
                ecarts.append({"id": f["id"], "cause": cause, "marque": marque})
                continue
        else:
            h = corps.decode("utf-8", errors="replace")
            page = chiffres_page_psup(h)
            if not page:
                cause = "page_sans_bloc_acces" if re.search(r"[0-9]+\s+places en 20[0-9]{2}", texte(h)) else "page_vide"
                marque = (vue.get("fiche_publique_annee_en_cours@2026") or {}).get("valeur")
                if cause == "page_vide" and marque != "absente":
                    cause = "ecart_inexplique"  # une formation absente présentée comme actuelle
                cases[cause] += 1
                ecarts.append({"id": f["id"], "cause": cause})
                continue
        if f["espace"] == "psup" and "places@2025" in page:
            od = base.con.execute("SELECT valeur_num FROM valeur WHERE id = ? AND champ = 'places_open_data' "
                                  "AND session = '2025'", (f["id"],)).fetchone()
            if od and od[0] is not None and od[0] != page["places@2025"]:
                places_od.append({"id": f["id"], "page": page["places@2025"], "open_data_capa_fin": od[0]})
        diff = []
        for cle, v_page in page.items():
            compares += 1
            v = vue.get(cle)
            v_modele = v["valeur"] if v and v["statut"] == "disponible" else None
            if v_modele != v_page:
                diff.append({"cle": cle, "page": v_page, "modele": v_modele})
        if diff:
            cases["ecart_inexplique"] += 1
            ecarts.append({"id": f["id"], "cause": "ecart_inexplique", "chiffres": diff})
        else:
            cases["concordante"] += 1
    base.fermer()
    n = len(formations)
    return {"formations": n, "chiffres_compares": compares, "cases": dict(cases),
            "couverture": sum(cases.values()) / n if n else 0.0,
            "doublons_montres": doublons, "ecarts": ecarts,
            # Ajout A du contrat : places 2025, la page est montrée ; l'open data (capa_fin) diffère ici.
            "places_page_contre_open_data": places_od,
            "vert": n > 0 and sum(cases.values()) == n and not cases.get("ecart_inexplique") and not doublons}


def compte_vus(base_chemin: Path, filtre: bool = True) -> dict:
    """Chiffres (valeurs numériques disponibles) que le modèle voit par fiche, par espace, et la liste des champs.
    `filtre=False` : toutes les valeurs de la base (ce que `lire_fiche` rendait avant le 25/09). Les lignes
    d'insertion, inchangées par ce lot, sont comptées à part."""
    import sqlite3
    import statistics
    con = sqlite3.connect(f"file:{base_chemin}?mode=ro", uri=True)
    cols = {r[1] for r in con.execute("PRAGMA table_info(champ)")}
    regles = (dict(con.execute("SELECT champ, montre_au_modele FROM champ")) if filtre and "montre_au_modele" in cols
              else None)
    from src.base_c import montre_au_modele
    par_fiche, champs = {}, {}
    for id_, esp, champ, session in con.execute(
            "SELECT v.id, f.espace, v.champ, v.session FROM valeur v JOIN formation f ON f.id = v.id "
            "WHERE v.statut = 'disponible' AND v.valeur_num IS NOT NULL"):
        if regles is not None and not montre_au_modele(regles.get(champ, "0"), esp, session):
            continue
        par_fiche.setdefault((esp, id_), 0)
        par_fiche[(esp, id_)] += 1
        champs.setdefault(esp, set()).add(champ)
    ins = dict(con.execute("SELECT id, COUNT(*) FROM insertion_ligne GROUP BY id"))
    con.close()
    out = {}
    for esp in sorted({e for e, _ in par_fiche}):
        n = [v for (e, _), v in par_fiche.items() if e == esp]
        out[esp] = {"fiches": len(n), "mediane": statistics.median(n), "min": min(n), "max": max(n),
                    "champs": sorted(champs[esp])}
    out["lignes_insertion_par_fiche_mediane"] = statistics.median(ins.values()) if ins else 0
    return out


def temoins(base_chemin: Path) -> dict:
    """Les deux leviers, joués dans des sous-processus : chacun doit faire rougir le contrôle."""
    out = {}
    sabotee = base_chemin.with_name(base_chemin.stem + ".sabote-concordance_valeur.sqlite")
    env = {**os.environ, "ORIENTIA_SABOTAGE_C": "concordance_valeur"}
    if not sabotee.exists():
        subprocess.run([sys.executable, "-m", "src.collect.base_etape_c"], cwd=RACINE, env=env, check=True,
                       capture_output=True)
    for nom, base, env_ctrl in (("valeur", sabotee, {}),
                                ("doublon", base_chemin, {"ORIENTIA_SABOTAGE_CONCORDANCE": "doublon"})):
        r = subprocess.run([sys.executable, "-m", "src.eval.concordance", "--base", str(base), "--sans-temoins",
                            "--sortie", str(RACINE / "results/concordance/temoins" / nom)],
                           cwd=RACINE, env={**os.environ, **env_ctrl}, capture_output=True, text=True)
        out[nom] = {"code_sortie": r.returncode, "rougit": r.returncode == 1}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=RACINE / "data/processed/base_etape_c.sqlite")
    ap.add_argument("--sortie", type=Path, default=RACINE / "results/concordance")
    ap.add_argument("--sans-temoins", action="store_true")
    ap.add_argument("--pages-vides", action="store_true", help="établit la cause des pages vides (réseau, lecture seule)")
    a = ap.parse_args(argv)
    if a.pages_vides:
        r = etablir_pages_vides(a.sortie)
        print(json.dumps({k: v for k, v in r.items() if k not in ("codes", "relecture")}, ensure_ascii=False))
        return 0 if r["etabli"] else 1
    r = controler(a.base)
    avant = RACINE.parent / "OrientIA/data/processed/base_etape_c.sqlite"
    r["chiffres_vus_par_le_modele"] = {"apres": compte_vus(a.base),
                                       "avant": compte_vus(avant, filtre=False) if avant.exists() else None,
                                       "avant_source": str(avant)}
    if not a.sans_temoins:
        r["temoins"] = temoins(a.base)
        r["vert"] = r["vert"] and all(t["rougit"] for t in r["temoins"].values())
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "ecarts.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k not in ("ecarts", "doublons_montres")} |
                     {"doublons_montres": len(r["doublons_montres"])}, ensure_ascii=False))
    return 0 if r["vert"] else 1



def etablir_pages_vides(sortie: Path, n_temoins: int = 20) -> dict:
    """Cause des pages Parcoursup vides (contrat §12, demande de Jarvis) : chaque page vide est relue une fois (si
    elle revient pleine, c'est un défaut de relevé) puis cherchée dans la cartographie ESR 2025 et 2026 ; un témoin
    de pages pleines, tirées avec une graine fixe, doit être dans la cartographie 2026. Écrit `pages_vides.json`."""
    import random
    import time
    import urllib.parse
    import urllib.request
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))["manifeste"]
    vides, pleines = [], []
    for nom, e in sorted(manifeste.items()):
        if not nom.startswith("psup/") or not e.get("sha256"):
            continue
        h = (CACHE / nom).read_bytes().decode("utf-8", errors="replace")
        (pleines if chiffres_page_psup(h) or re.search(r"[0-9]+\s+places en 20[0-9]{2}", texte(h)) else vides).append(nom[5:-5])
    url_esr = ("https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets/"
               "fr-esr-cartographie_formations_parcoursup/records")

    def presents(annee: str, codes: list[str]) -> set[str]:
        vus = set()
        for i in range(0, len(codes), 50):
            q = urllib.parse.urlencode({"where": f'annee="{annee}" and gta in ({",".join(chr(34) + c + chr(34) for c in codes[i:i + 50])})',
                                        "select": "gta", "limit": 100})
            r = urllib.request.urlopen(urllib.request.Request(f"{url_esr}?{q}", headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
            vus |= {x["gta"] for x in json.load(r)["results"]}
            time.sleep(1.5)
        return vus

    relues = {}
    from src.collect.pages_publiques import URL_PSUP
    for code in vides:
        time.sleep(1.5)
        h = urllib.request.urlopen(urllib.request.Request(URL_PSUP.format(code), headers={"User-Agent": "Mozilla/5.0"}),
                                   timeout=30).read().decode("utf-8", errors="replace")
        relues[code] = {"caracteres_texte": len(texte(h)), "pleine_a_la_relecture": bool(chiffres_page_psup(h))}
    temoins = sorted(random.Random("pages-vides-2026-09-25").sample(pleines, min(n_temoins, len(pleines))))
    r = {"pages_vides": len(vides), "codes": vides, "relecture": relues,
         "dans_cartographie_2026": sorted(presents("2026", vides)), "dans_cartographie_2025": sorted(presents("2025", vides)),
         "temoin_pages_pleines": {"codes": temoins, "dans_cartographie_2026": sorted(presents("2026", temoins))}}
    r["etabli"] = (not r["dans_cartographie_2026"] and not any(x["pleine_a_la_relecture"] for x in relues.values())
                   and len(r["temoin_pages_pleines"]["dans_cartographie_2026"]) == len(temoins))
    (sortie / "pages_vides.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return r


if __name__ == "__main__":
    sys.exit(main())
