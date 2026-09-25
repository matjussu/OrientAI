"""Étape 3, phase A : quelles notions de `lire_fiche` portent les chiffres attendus des bancs. Zéro appel d'API.

    python -m src.eval.essentiel_fiche [--sortie results/cerveau_etape3/essentiel_fiche.json]

Pour chaque chiffre attendu du banc vertical dont la fiche est dans la base C (`results/banc_e/exposition.json`,
`cible_par_attendu`), on rattache le champ du banc à la notion de la base C qui le porte (table `CORRESPONDANCE`,
écrite à la main d'après les deux vocabulaires) et on lit la fiche par `lire_fiche` (ce que le modèle voit
aujourd'hui, filtre « montré au modèle » de #189 compris). Chaque attendu reçoit un statut :

- `egal` : la notion est rendue et sa valeur égale l'attendu (tolérance du critère 1, `critere_d.TOLERANCE`) ;
- `ecart` : la notion est rendue avec une autre valeur (cas attendu : le banc vient de l'open data, la base montre la
  page publique depuis #189, ex. places 117 contre 109) ;
- `masque` : la base a la notion pour cette fiche, mais `lire_fiche` ne la montre pas au modèle (filtre de #189) ;
- `absent` : ni la fiche rendue ni la base n'ont la notion (raison du « non disponible » gardée quand elle existe).

L'« essentiel » se mesure sur `egal` + `ecart` : un chiffre rendu, même d'une autre définition, est un chiffre que le
modèle doit voir pour répondre à la question. La part cumulée par notion est publiée dans l'ordre décroissant.

Le banc lot 0 (`src/eval/battery/battery.json`) ne porte aucun chiffre attendu : il est compté (0), pas mesuré.

Contrôles : zéro attendu rendable fait échouer le script. Les notions de la table inconnues de toute la base sont
publiées (`controle_table`) : un candidat de la table qui n'existe nulle part ne peut rien couvrir.
Contrôle de la table, par la valeur : pour chaque attendu, les champs de la fiche de valeur égale (toutes notions) sont
relevés ; la part des attendus `egal` sur la notion de la table, rapportée à ceux qui ont au moins un champ égal, dit
si la table pointe au bon endroit. Témoin de hasard (comme le critère 1) : les mêmes attendus confrontés à la fiche
d'un AUTRE attendu (graine 7), pour savoir ce que vaut une égalité de valeur seule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from src.base_c import outils
from src.eval import critere_d as cd
from src.eval.multiversion.lanceur import BANCS, charger_banc

RACINE = Path(__file__).resolve().parents[2]
EXPOSITION = RACINE / "results/banc_e/exposition.json"
UNITE_BASE = {"pct": {"%"}, "places": {"places"}, "effectif": {"candidats", "voeux", "propositions"}, "eur": {"EUR"}}
INSERTION_UNITE = {"taux_": "pct", "salaire_": "eur", "effectif_": "effectif"}

# Champ du banc -> notions de la base C qui le portent, par ordre de préférence (la première rendue gagne).
# « insertion » = le bloc InserSup/InserJeunes de la fiche (lignes `insertion`), pas un chiffre isolé.
CORRESPONDANCE = {
    "taux_acces_parcoursup_2025": ["taux_acces@2025"],
    "admission.historique.2023.taux_acces": ["taux_acces@2023"],
    "admission.historique.2024.taux_acces": ["taux_acces@2024"],
    "nombre_places": ["places@2025"],
    "capacite": ["capacite_accueil@2025", "capacite_accueil@2026", "capacite_campagne_2025"],
    "profil_admis.bac_type_pct.techno": ["repartition_admis_bac_techno@2025", "part_acces_techno@2025"],
    "profil_admis.bac_type_pct.pro": ["repartition_admis_bac_pro@2025", "part_acces_pro@2025"],
    "profil_admis.neobacheliers_pct": ["part_neobacheliers@2025"],
    "profil_admis.mentions_pct.tb": ["part_mention_tb@2025"],
    "profil_admis.mentions_pct.sans": ["part_mention_sans_mention@2025"],
    "admission.volumes.voeux_totaux": ["candidats_ont_postule@2025", "voeux_totaux@2025"],
    "admission.volumes.voeux_phase_principale": ["candidats_ont_postule@2025", "voeux_phase_principale@2025"],
    "admission.historique.2023.voeux_totaux": ["voeux_phase_principale@2023"],
    "admission.volumes.classes_phase_principale": ["candidats_classes@2025"],
    "propositions_totales": ["candidats_ont_pu_recevoir_une_proposition@2025", "propositions_total@2025"],
    "n_candidats_pp": ["candidats_pp_open_data@2025", "candidatures_campagne_precedente@2025"],
    "insertion_pro.salaire_median_embauche": ["insertion"],
    "insertion_pro.taux_emploi_12m": ["insertion"],
    "taux.passage_l2_1an_pct": ["taux_passage_l2@2025"],
    "taux.obtention_3ans_pct": ["taux_obtention_3ans@2025"],
}


# Proposition « essentiel par défaut » soumise à Matteo (CONTRAT-etape3, section 4) : notions gardées, toutes sessions
# montrées. Les notions de santé nationales viennent du gate F (F-HSAN-02 : chiffre national dit national), pas du banc.
ESSENTIEL = {
    "taux_acces", "places", "capacite_accueil", "repartition_admis_bac_general", "repartition_admis_bac_techno",
    "repartition_admis_bac_pro", "candidats_ont_postule",
    "passage_mmopk_1_ou_2_ans_national", "passage_pass_las_ensemble_national", "sante.reforme_2027",
}


def notion(cle: str) -> str:
    return cle.split("@", 1)[0]


def chiffres_rendus(fiche: dict) -> dict[str, tuple[float, str]]:
    """Tous les chiffres rendus par `lire_fiche`, clé -> (valeur, famille d'unité du critère 1)."""
    out = {}
    for cle, v in fiche["valeurs"].items():
        if not isinstance(v["valeur"], (int, float)) or v["statut"] != "disponible":
            continue
        fam = next((f for f, us in UNITE_BASE.items() if v["unite"] in us), None)
        if fam:
            out[cle] = (float(v["valeur"]), fam)
    for ligne in fiche["insertion"]:
        for k, val in ligne.items():
            fam = next((f for p, f in INSERTION_UNITE.items() if k.startswith(p)), None)
            if fam and isinstance(val, (int, float)):
                out[f"insertion.{k}"] = (float(val), fam)
    return out


def _egal(attendu: dict, val: float, fam: str) -> bool:
    u = cd.UNITE_ATTENDU[attendu["unite"]]
    return fam == u and abs(val - float(attendu["valeur"])) <= cd.TOLERANCE[u]


def statut(attendu: dict, fiche: dict, rendus: dict, brutes: set[str]) -> tuple[str, str | None, list]:
    """(statut, notion retenue, valeurs de la notion) pour un attendu sur sa fiche."""
    for cle in CORRESPONDANCE[attendu["champ"]]:
        if cle == "insertion":
            vals = [(v, f) for k, (v, f) in rendus.items() if k.startswith("insertion.")]
            if vals:
                return ("egal" if any(_egal(attendu, v, f) for v, f in vals) else "ecart"), cle, [v for v, _ in vals]
            continue
        if cle in rendus:
            v, f = rendus[cle]
            return ("egal" if _egal(attendu, v, f) else "ecart"), cle, [v]
    masquees = [c for c in CORRESPONDANCE[attendu["champ"]] if c in brutes]
    if masquees:
        return "masque", masquees[0], []
    raison = next((fiche["valeurs"][c]["raison"] for c in CORRESPONDANCE[attendu["champ"]]
                   if c in fiche["valeurs"] and fiche["valeurs"][c]["raison"]), None)
    return "absent", None, [raison] if raison else []


def mesurer() -> dict:
    items, banc_sha = charger_banc("vertical")
    expo = json.loads(EXPOSITION.read_text(encoding="utf-8"))
    if not banc_sha.startswith(expo["banc_sha256"][:12]):
        raise SystemExit(f"exposition faite sur un autre banc ({expo['banc_sha256'][:12]} contre {banc_sha[:12]})")
    base = outils.Base.ouvrir()
    notions_base = {r[0] for r in base.con.execute("SELECT DISTINCT champ FROM valeur")}
    inconnues = sorted({notion(c) for cs in CORRESPONDANCE.values() for c in cs if c != "insertion"} - notions_base)
    fiches, rendus, brutes, lignes = {}, {}, {}, []
    for item in items:
        cibles = expo["conversations"][item["id"]]["cible_par_attendu"]
        for a, cible in zip(item["attendus"]["chiffres"], cibles):
            ligne = {"conversation": item["id"], "champ_banc": a["champ"], "source_banc": a["source"],
                     "valeur": a["valeur"], "unite": a["unite"], "fiche": cible}
            if cible is not None:
                if cible not in fiches:
                    fiches[cible] = outils.lire_fiche(base, cible)
                    rendus[cible] = chiffres_rendus(fiches[cible])
                    brutes[cible] = {outils._cle(r["champ"], r["session"]) for r in base.con.execute(
                        "SELECT champ, session FROM valeur WHERE id = ? AND statut = 'disponible'", (cible,))}
                st, cle, vals = statut(a, fiches[cible], rendus[cible], brutes[cible])
                ligne |= {"statut": st, "notion": cle, "valeurs_base": vals,
                          "champs_de_valeur_egale": sorted(k for k, (v, f) in rendus[cible].items() if _egal(a, v, f))}
            lignes.append(ligne)
    base.fermer()

    rendables = [l for l in lignes if l["fiche"] is not None]
    if not rendables:
        raise SystemExit("zéro attendu rendable : le banc ou l'exposition ne correspond pas")

    rendus_ok = [l for l in rendables if l["statut"] in ("egal", "ecart")]
    par_notion = Counter(notion(l["notion"]) for l in rendus_ok)
    classement, cumul = [], 0
    for n, k in par_notion.most_common():
        cumul += k
        classement.append({"notion": n, "attendus": k, "cumul": cumul,
                           "part_cumulee_des_rendables": round(cumul / len(rendables), 4),
                           "part_cumulee_des_rendus": round(cumul / len(rendus_ok), 4)})

    # Contrôle de la table par la valeur, et témoin de hasard sur une autre fiche.
    avec_egal = [l for l in rendables if l["champs_de_valeur_egale"]]
    table_confirmee = sum(l["statut"] == "egal" for l in avec_egal)
    rng = random.Random(7)
    hasard = 0
    for l in rendables:
        autre = rng.choice([c for c in rendus if c != l["fiche"]])
        hasard += any(_egal(l, v, f) for v, f in rendus[autre].values())

    tailles = [len(fiches[c]["valeurs"]) for c in fiches]
    couverts_essentiel = sum(notion(l["notion"]) in ESSENTIEL for l in rendus_ok)
    # Taille sur toute la base : chiffres rendus aujourd'hui contre chiffres gardés par l'essentiel, par espace.
    base = outils.Base.ouvrir()
    tailles_base = defaultdict(lambda: {"aujourd_hui": [], "essentiel": []})
    for (id_, esp) in base.con.execute("SELECT id, espace FROM formation").fetchall():
        vals = outils.lire_fiche(base, id_)["valeurs"]
        tailles_base[esp]["aujourd_hui"].append(len(vals))
        tailles_base[esp]["essentiel"].append(sum(notion(k) in ESSENTIEL for k in vals))
    base.fermer()
    return {
        "commande": "python -m src.eval.essentiel_fiche",
        "banc_vertical": {"chemin": str(BANCS["vertical"]), "sha256": banc_sha},
        "banc_lot0": {"chemin": str(BANCS["lot0"].relative_to(RACINE)), "attendus_chiffres": sum(
            len((i.get("attendus") or {}).get("chiffres", [])) for i in json.loads(BANCS["lot0"].read_text())["items"])},
        "exposition": {"chemin": str(EXPOSITION.relative_to(RACINE)), "base_sha256_a_l_epoque": expo["base_sha256"]},
        "base": {"chemin": str(Path(outils.BASE_DEFAUT).relative_to(RACINE)),
                 "sha256": hashlib.sha256(Path(outils.BASE_DEFAUT).read_bytes()).hexdigest()},
        "attendus": len(lignes), "hors_base_c": len(lignes) - len(rendables), "rendables": len(rendables),
        "statuts": dict(Counter(l["statut"] for l in rendables)),
        "absents_par_champ_banc": dict(Counter(l["champ_banc"] for l in rendables if l["statut"] == "absent")),
        "masques_par_champ_banc": dict(Counter(f'{l["champ_banc"]} -> {l["notion"]}' for l in rendables
                                               if l["statut"] == "masque")),
        "ecarts_par_champ_banc": dict(Counter(l["champ_banc"] for l in rendables if l["statut"] == "ecart")),
        "classement_notions": classement,
        "essentiel_propose": {"notions": sorted(ESSENTIEL),
                              "attendus_rendus_couverts": couverts_essentiel, "attendus_rendus": len(rendus_ok),
                              "part_des_rendus": round(couverts_essentiel / len(rendus_ok), 4),
                              "part_des_rendables": round(couverts_essentiel / len(rendables), 4),
                              "valeurs_par_fiche_toute_la_base": {
                                  esp: {k: {"mediane": statistics.median(v), "max": max(v)} for k, v in t.items()}
                                  | {"fiches": len(t["essentiel"])} for esp, t in sorted(tailles_base.items())}},
        "controle_table": {"attendus_avec_un_champ_de_valeur_egale": len(avec_egal),
                           "dont_egal_sur_la_notion_de_la_table": table_confirmee,
                           "notions_de_la_table_inconnues_de_la_base": inconnues,
                           "temoin_hasard_egalite_sur_une_autre_fiche": hasard},
        "valeurs_par_fiche_lire_fiche": {"fiches": len(tailles), "mediane": statistics.median(tailles),
                                         "min": min(tailles), "max": max(tailles)},
        "lignes": lignes,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sortie", type=Path, default=RACINE / "results/cerveau_etape3/essentiel_fiche.json")
    a = ap.parse_args(argv)
    r = mesurer()
    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    a.sortie.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k not in ("lignes",)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
