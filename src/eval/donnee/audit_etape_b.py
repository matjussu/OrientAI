"""Audit d'exactitude de l'étape B-1 : fiches tirées au hasard, chaque nouvelle valeur comparée à sa source.

Le témoin ne partage pas son instrument avec le pipeline :
- Onisep : le dump JSON du jeu Idéo-Actions, retéléchargé au moment de l'audit (le pipeline lit le
  CSV verrouillé) ;
- Parcoursup apprentissage, InserSup : l'API du portail data.enseignementsup-recherche, ligne par ligne ;
- InserJeunes : l'API du portail data.education.gouv.fr ;
- droits d'inscription : le PDF du tableau ministériel 2026-2027, retéléchargé et relu (pdftotext).

Pour chaque fiche et chaque champ (`cout`, `alternance`, `insertion`) :
- une valeur `disponible` doit être égale à la ligne source, et écrite dans le texte lu par le modèle ;
- une valeur `non_disponible` dont la raison affirme un fait vérifiable est vérifiée elle aussi
  (« aucune formation de ce lieu dans le jeu Onisep », « coûts différents », « aucune formation en
  apprentissage du même diplôme au même lieu »).
Tout écart fait échouer l'audit (code de sortie 1).

Contrôle positif : `--sabotage cout|alternance|insertion` altère en mémoire la valeur audités
(montant +1, capacité +1, taux +1) avant l'audit ; l'audit DOIT alors échouer. Le résultat d'un run
saboté est écrit sous un nom suffixé par le levier, jamais par-dessus l'audit honnête.

Usage :
    python -m src.eval.donnee.audit_etape_b --corpus data/processed/formations_etape_b1.json
        [--n 50] [--graine 20260923] [--sortie results/donnee_etape_b/audit_b1.json] [--sabotage cout]
        [--parmi insertion_disponible|alternance_existe|cout_onisep]   # tirage ciblé, en complément
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

from src.eval.donnee.texte import charger_fiche_to_text

ESR = "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets"
DEPP = "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets"
ONISEP_JSON = "https://api.opendata.onisep.fr/downloads/605344579a7d7/605344579a7d7.json"
TABLEAU_PDF = "https://www.univ-reims.fr/media-files/65970/i02-droits-inscription-2025-2026.pdf"
DOMAINES_INFO = {"informatique", "cyber", "data_ia"}
REGLES_MATHS = {"M01", "M02", "M03"}
SOURCES = ("parcoursup", "parcoursup_apprentissage")


def verticale(fiche: dict) -> str | None:
    """Même partition que l'audit de l'étape A (`audit_officiel.verticale`)."""
    if fiche.get("domaine") in DOMAINES_INFO:
        return "informatique"
    if fiche.get("domaine") == "sante":
        return "sante"
    if fiche.get("domaine_regle") in REGLES_MATHS:
        return "maths"
    return None


# Tirages ciblés, en COMPLÉMENT du tirage au hasard : un champ rarement disponible (insertion : 5 fiches
# sur 50 au tirage du 23/09/2026) n'est pas audité par un tirage uniforme.
CIBLES = {
    "tout": lambda f: True,
    "insertion_disponible": lambda f: (f.get("insertion") or {}).get("statut") == "disponible",
    "alternance_existe": lambda f: bool(((f.get("alternance") or {}).get("valeur") or {}).get("formations")),
    "cout_onisep": lambda f: str((f.get("cout") or {}).get("rattachement")).startswith("onisep")
    and f["cout"]["statut"] == "disponible",
}


def tirer(corpus: list[dict], n: int, graine: int, parmi: str = "tout") -> list[dict]:
    par_dom: dict[str, list[dict]] = {"informatique": [], "sante": [], "maths": []}
    cible = CIBLES[parmi]
    for f in corpus:
        if f.get("source") in SOURCES and (v := verticale(f)) and cible(f):
            par_dom[v].append(f)
    rng = random.Random(graine)
    tirage = []
    for i, dom in enumerate(par_dom):
        k = n // 3 + (1 if i < n % 3 else 0)
        tirage.extend(rng.sample(par_dom[dom], min(k, len(par_dom[dom]))))
    return tirage


def _get(url: str, insecure: bool = False) -> bytes:
    ctx = ssl._create_unverified_context() if insecure else None  # certificat de l'université invalide
    for essai in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120, context=ctx) as rep:
                return rep.read()
        except Exception:  # noqa: BLE001 : réseau, on retente puis on laisse remonter
            if essai == 3:
                raise
            time.sleep(2 * (essai + 1))
    raise RuntimeError("inatteignable")


def _records(base: str, jeu: str, where: str) -> list[dict]:
    url = f"{base}/{jeu}/records?limit=100&where={urllib.parse.quote(where)}"
    return json.loads(_get(url))["results"]


def _q(v: str) -> str:
    return '"' + str(v).replace('"', '\\"') + '"'


def _nombre(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if not s or s.lower() == "nd":
        return None
    return float(s)


class Temoins:
    """Sources lues au moment de l'audit, indépendamment du pipeline."""

    def __init__(self) -> None:
        self.onisep = {l["action_de_formation_af_identifiant_onisep"]: l for l in json.loads(_get(ONISEP_JSON))}
        self.onisep_par_uai: dict[str, list[dict]] = {}
        for l in self.onisep.values():
            self.onisep_par_uai.setdefault(l.get("ens_code_uai") or "", []).append(l)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
            fh.write(_get(TABLEAU_PDF, insecure=True))
            fh.flush()
            self.tableau = subprocess.run(["pdftotext", "-layout", fh.name, "-"], capture_output=True,
                                          text=True, check=True).stdout

    def droits_tableau(self) -> dict[str, int]:
        """Montants lus dans le tableau : CPGE de lycée public et groupe du cycle de licence."""
        t = self.tableau
        cpge = re.search(r"classe préparatoire aux grandes écoles d'un lycée public\s+(\d+)\s?€", t)
        licence = re.search(r"\nLicence\s+(\d+)\s?€", t)
        return {"cpge": int(cpge.group(1)) if cpge else -1, "licence": int(licence.group(1)) if licence else -1,
                "but_dans_le_groupe": int("Bachelor universitaire de technologie (BUT)" in t)}


def auditer_cout(fiche: dict, texte: str, t: Temoins) -> list[str]:
    cout = fiche["cout"]
    ecarts = []
    if cout["statut"] == "disponible":
        v = cout["valeur"]
        if cout["rattachement"] == "constante_type_statut":
            droits = t.droits_tableau()
            attendu = {"tableau_droits_2026_2027": droits["cpge"] if fiche.get("fili_code") == "CPGE" else droits["licence"],
                       "service_public_f36520": 0}[cout["source"]["id"]]
            if v["droits_inscription_eur"] != attendu:
                ecarts.append(f"droits {v['droits_inscription_eur']} != tableau {attendu}")
            if fiche.get("fili_code") == "BUT" and not droits["but_dans_le_groupe"]:
                ecarts.append("BUT absent du groupe cycle de licence du tableau")
        else:
            ligne = t.onisep.get(v.get("onisep_action"))
            if ligne is None:
                return [f"ligne Onisep {v.get('onisep_action')} introuvable dans le dump JSON"]
            if (ligne.get("ens_code_uai") or "") != fiche.get("cod_uai"):
                ecarts.append(f"UAI Onisep {ligne.get('ens_code_uai')} != fiche {fiche.get('cod_uai')}")
            brut = " ".join((ligne.get("af_cout_scolarite") or "").split())
            if brut != v["texte_source"]:
                ecarts.append(f"texte coût « {v['texte_source']} » != Onisep « {brut} »")
            nombres = {int(re.sub(r"\D", "", m)) for m in re.findall(r"\d[\d  ]*", brut)}
            for m in (v.get("scolarite_total_eur"), v.get("scolarite_annuel_eur"), *(v.get("fourchette_eur") or [])):
                if m is not None and m not in nombres:
                    ecarts.append(f"montant {m} absent du texte Onisep")
        for m in (v.get("droits_inscription_eur"), v.get("scolarite_total_eur")):
            if m and f"{m} euros" not in texte:
                ecarts.append(f"montant {m} non écrit dans le texte")
        return ecarts
    raison = cout.get("raison") or ""
    lignes = t.onisep_par_uai.get(fiche.get("cod_uai") or "", [])
    if "aucune formation de ce lieu" in raison and lignes:
        ecarts.append(f"« aucune formation Onisep à ce lieu » mais {len(lignes)} lignes à cet UAI")
    if "coûts différents" in raison:
        couts = {" ".join((l.get("af_cout_scolarite") or "").split()) for l in lignes} - {""}
        if len(couts) < 2:
            ecarts.append("« coûts différents » mais moins de deux coûts à cet UAI")
    if "non disponible" not in texte.split("Coût", 1)[-1][:40]:
        ecarts.append("coût non disponible non dit dans le texte")
    return ecarts


def auditer_alternance(fiche: dict, texte: str) -> list[str]:
    alt = fiche.get("alternance")
    if fiche.get("source") == "parcoursup_apprentissage":
        ligne = _records(ESR, "fr-esr-parcoursup-apprentissage", f"session={_q('2025')} and cod_aff_form={_q(fiche['cod_aff_form'])}")
        if len(ligne) != 1:
            return [f"formation d'apprentissage {fiche['cod_aff_form']} : {len(ligne)} lignes officielles"]
        a, o = fiche["apprentissage"], ligne[0]
        return [f"{k} {a[k]} != officiel {o[c]}" for k, c in (("capacite", "capa_fin"), ("candidats", "voe_tot"),
                ("propositions", "prop_tot"), ("voeux_recherche_contrat", "nb_rech_con")) if a[k] != o[c]]
    ecarts = []
    formations = alt["valeur"]["formations"]
    for f in formations:
        ligne = _records(ESR, "fr-esr-parcoursup-apprentissage", f"session={_q('2025')} and cod_aff_form={_q(f['cod_aff_form'])}")
        if len(ligne) != 1:
            ecarts.append(f"apprentissage {f['cod_aff_form']} introuvable")
            continue
        o = ligne[0]
        if f["capacite"] != o["capa_fin"]:
            ecarts.append(f"capacité {f['capacite']} != officielle {o['capa_fin']}")
        if f["rattachee_par"] == "uai" and o["cod_uai"] != fiche.get("cod_uai"):
            ecarts.append(f"rattachée par l'UAI mais UAI {o['cod_uai']} != {fiche.get('cod_uai')}")
        if f["cod_aff_form"] and f.get("etablissement") and f["etablissement"] not in texte:
            ecarts.append("formation d'apprentissage rattachée non écrite dans le texte")
    if not formations:
        # Même diplôme, même UAI : l'API ne doit rien rendre (le cas « même commune » n'est pas
        # interrogeable sans le référentiel des communes ; il est couvert par les tests).
        spec = fiche.get("filiere_detaillee") or ""
        memes = _records(
            ESR, "fr-esr-parcoursup-apprentissage",
            f"session={_q('2025')} and cod_uai={_q(fiche.get('cod_uai'))} and form_lib_voe_acc={_q(fiche.get('form_lib_voe_acc'))}",
        )
        memes = [o for o in memes if re.sub(r"\s*-\s*en apprentissage\s*$", "", o.get("fil_lib_voe_acc") or "", flags=re.I).lower() == spec.lower()]
        if memes:
            ecarts.append(f"« pas d'apprentissage » mais {len(memes)} formation(s) du même diplôme au même UAI")
    return ecarts


def auditer_insertion(fiche: dict, texte: str) -> list[str]:
    ins = fiche["insertion"]
    if ins["statut"] != "disponible":
        return [] if "Insertion professionnelle : non disponible" in texte else ["insertion non disponible non dite"]
    v = ins["valeur"]
    ecarts = []
    for ligne in v["lignes"]:
        p = ligne["perimetre"]
        if v["dispositif"] == "InserSup":
            # `promo` est une LISTE dans l'API (["2023", "2024"] pour une promotion cumulée), une chaîne
            # « 2023,2024 » dans l'export CSV lu par le pipeline : on interroge chaque année, puis on
            # garde la ligne dont la liste est exactement celle de la fiche.
            promos = v["promotion"].split(",")
            where = (f"diplome={_q(p['code_diplome_sise'])} and uo_lib={_q(p['etablissement'])} and "
                     + " and ".join(f"promo={_q(a)}" for a in promos)
                     + " and genre=\"ensemble\" and nationalite=\"ensemble\" and "
                     "regime_inscription=\"ensemble\" and obtention_diplome=\"diplômé\"")
            officiel = [o for o in _records(ESR, "fr-esr-insersup", where) if sorted(o.get("promo") or []) == sorted(promos)]
            if len(officiel) != 1:
                ecarts.append(f"InserSup {p['diplome']} : {len(officiel)} lignes officielles")
                continue
            o = officiel[0]
            for cle, col in (("taux_emploi_salarie_fr_6m", "tx_sortants_en_emploi_sal_fr_6"),
                             ("taux_emploi_salarie_fr_12m", "tx_sortants_en_emploi_sal_fr_12"),
                             ("taux_emploi_salarie_fr_18m", "tx_sortants_en_emploi_sal_fr_18"),
                             ("taux_emploi_stable_12m", "tx_sortants_en_emploi_stable_12")):
                if ligne["indicateurs"][cle] != _nombre(o.get(col)):
                    ecarts.append(f"{cle} {ligne['indicateurs'][cle]} != officiel {o.get(col)}")
        else:
            code = p["code_formation_mefstat11"]
            officiel = _records(DEPP, "fr-en-inserjeunes-lycee_pro-formation-fine",
                                f"uai={_q(fiche.get('cod_uai'))} and code_formation_mefstat11={_q(code)} and annee={_q(v['promotion'])}")
            if len(officiel) != 1:
                ecarts.append(f"InserJeunes {code} : {len(officiel)} lignes officielles")
                continue
            o = officiel[0]
            for cle, col in (("taux_emploi_6m", "taux_emploi_6_mois"), ("taux_emploi_12m", "taux_emploi_12_mois"),
                             ("taux_poursuite_etudes", "taux_poursuite_etudes")):
                if ligne["indicateurs"][cle] != _nombre(o.get(col)):
                    ecarts.append(f"{cle} {ligne['indicateurs'][cle]} != officiel {o.get(col)}")
        # Le taux d'emploi stable est gardé dans la donnée (comparé ci-dessus) mais pas écrit dans
        # le texte : sans définition publiée, on ne l'écrit pas (`texte_parcoursup`, DEFINITIONS_INSERTION).
        ecrits = {k: x for k, x in ligne["indicateurs"].items() if k != "taux_emploi_stable_12m"}
        for val in ecrits.values():
            if val is not None and val <= 100 and (str(val).rstrip("0").rstrip(".").replace(".", ",") + " %") not in texte \
                    and f"{int(val)} %" not in texte:
                ecarts.append(f"taux {val} non écrit dans le texte")
    return ecarts


def saboter(fiche: dict, levier: str) -> None:
    """Altère la valeur que l'audit doit contrôler (contrôle positif)."""
    if levier == "cout" and fiche["cout"]["statut"] == "disponible":
        v = fiche["cout"]["valeur"]
        cle = next((k for k in ("droits_inscription_eur", "scolarite_total_eur", "scolarite_annuel_eur")
                    if v.get(k) is not None), None)
        if cle:
            v[cle] += 1
        elif v.get("fourchette_eur"):  # coût publié en fourchette seulement
            v["fourchette_eur"][0] += 1
    elif levier == "alternance" and fiche.get("source") == "parcoursup_apprentissage":
        fiche["apprentissage"]["candidats"] = (fiche["apprentissage"]["candidats"] or 0) + 1
    elif levier == "alternance" and fiche["alternance"]["valeur"]["formations"]:
        f = fiche["alternance"]["valeur"]["formations"][0]
        f["capacite"] = (f["capacite"] or 0) + 1
    elif levier == "insertion" and fiche["insertion"]["statut"] == "disponible":
        # Première ligne qui porte un taux : une ligne toute « non diffusée » n'a rien à saboter.
        for ligne in fiche["insertion"]["valeur"]["lignes"]:
            cle = next((k for k, x in ligne["indicateurs"].items() if x is not None), None)
            if cle:
                ligne["indicateurs"][cle] += 1
                break


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--graine", type=int, default=20260923)
    ap.add_argument("--sortie", type=Path, default=Path("results/donnee_etape_b/audit_b1.json"))
    ap.add_argument("--sabotage", choices=("cout", "alternance", "insertion"))
    ap.add_argument("--parmi", choices=tuple(CIBLES), default="tout")
    args = ap.parse_args(argv)
    if args.parmi != "tout":
        args.sortie = args.sortie.with_name(f"{args.sortie.stem}_{args.parmi}{args.sortie.suffix}")
    if args.sabotage:  # un run saboté n'écrase jamais l'audit honnête
        args.sortie = args.sortie.with_name(f"{args.sortie.stem}_sabotage_{args.sabotage}{args.sortie.suffix}")

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    tirage = tirer(corpus, args.n, args.graine, args.parmi)
    fiche_to_text = charger_fiche_to_text(None)
    temoins = Temoins()
    resultats = []
    for fiche in tirage:
        if args.sabotage:
            saboter(fiche, args.sabotage)
        texte = fiche_to_text(fiche)
        ecarts = {
            "cout": auditer_cout(fiche, texte, temoins),
            "alternance": auditer_alternance(fiche, texte),
            "insertion": auditer_insertion(fiche, texte),
        }
        resultats.append({
            "cod_aff_form": str(fiche["cod_aff_form"]), "source": fiche["source"], "domaine": verticale(fiche),
            "nom": fiche.get("nom"), "etablissement": fiche.get("etablissement"),
            "statuts": {c: (fiche.get(c) or {}).get("statut") for c in ("cout", "alternance", "insertion")},
            "rattachements": {c: (fiche.get(c) or {}).get("rattachement") for c in ("cout", "alternance", "insertion")},
            "ecarts": {c: e for c, e in ecarts.items() if e},
        })
    en_ecart = [r for r in resultats if r["ecarts"]]
    sortie = {
        "genere_le": dt.datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "corpus": str(args.corpus), "n": len(resultats), "graine": args.graine, "sabotage": args.sabotage,
        "parmi": args.parmi,
        "temoins": {"onisep": ONISEP_JSON, "tableau": TABLEAU_PDF, "apprentissage_insersup": ESR, "inserjeunes": DEPP},
        "droits_lus_dans_le_tableau": temoins.droits_tableau(),
        "par_statut": {c: dict(Counter(r["statuts"][c] for r in resultats)) for c in ("cout", "alternance", "insertion")},
        "fiches_en_ecart": len(en_ecart),
        "resultats": resultats,
    }
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(sortie, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in sortie.items() if k != "resultats"}, ensure_ascii=False, indent=2))
    for r in en_ecart:
        print(r["cod_aff_form"], r["ecarts"])
    return 1 if en_ecart else 0


if __name__ == "__main__":
    sys.exit(main())
