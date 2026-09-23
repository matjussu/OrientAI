"""Audit de l'étape B-2 : chaque chiffre santé rapproché de son document source verrouillé.

Trois niveaux :
1. **Sources** : chaque extrait recopié dans `src.collect.sante` / `src.collect.sante_universites`
   doit figurer dans le texte du document brut verrouillé (`pdftotext -layout`, espaces réduits,
   apostrophes et tirets typographiques ramenés à leur forme simple). Chaque nombre d'une
   capacité doit figurer dans les extraits de son document, ou être une somme déclarée
   (`somme_de`) dont l'audit refait le calcul. Un document sans couche texte exploitable
   (`LECTURE_VISUELLE`) rend NON MESURÉ, jamais vert.
2. **Corpus** : chaque fiche PASS/LAS porte `sante` avec les valeurs de la table (le pipeline a
   recopié ce que l'audit vient de vérifier), et son texte les écrit avec leur portée.
3. **Contrôle positif** : `--saboter <levier>` casse une valeur par levier explicite ; l'audit doit
   rougir (code de sortie 1). Leviers : `sies` (taux national de médecine PASS), `capacite` (places
   PASS de médecine à Lille), `somme` (total LAS de médecine à Nantes), `extrait` (une ligne
   d'extrait de Bordeaux), `corpus` (valeur recopiée sur une fiche).

Usage :
    python -m src.eval.donnee.audit_sante [--corpus data/processed/formations_etape_b2.json] [--saboter LEVIER]
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from src.collect import sante, sante_universites
from src.collect.sources_officielles import RACINE, chemin_verifie

LEVIERS = ("sies", "capacite", "somme", "extrait", "corpus")
_CLES_NOMBRE = ("total", "PASS", "LAS", "passerelles", "autres")


def normaliser(texte: str) -> str:
    texte = texte.replace("\u2019", "'").replace("\u2018", "'").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", texte).strip()


@lru_cache(maxsize=None)
def texte_source(source_id: str) -> str:
    """Texte normalisé d'un document verrouillé (contrôle d'empreinte compris)."""
    chemin = chemin_verifie(source_id)
    try:
        sortie = subprocess.run(["pdftotext", "-layout", str(chemin), "-"], capture_output=True, check=True).stdout
    except FileNotFoundError as exc:  # pragma: no cover - dépend du poste
        raise RuntimeError("pdftotext (poppler-utils) est requis par l'audit santé") from exc
    return normaliser(sortie.decode("utf-8", errors="replace"))


def _present(extrait: str, texte: str) -> bool:
    return normaliser(extrait) in texte


def _nombres(d: dict) -> list[int]:
    out = []
    for v in d.values():
        if isinstance(v, dict):
            out.extend(_nombres(v))
        elif isinstance(v, int) and not isinstance(v, bool):
            out.append(v)
    return out


def _chemin(filiere: dict, nom: str):
    """Valeur d'une ligne additionnée : chemin dans `detail` (« a > b »), sinon clé de la filière."""
    noeud = filiere.get("detail") or {}
    for morceau in nom.split(" > "):
        if not isinstance(noeud, dict) or morceau not in noeud:
            noeud = None
            break
        noeud = noeud[morceau]
    if isinstance(noeud, int):
        return noeud
    return filiere.get(nom) if isinstance(filiere.get(nom), int) else None


# ── 1. sources ──────────────────────────────────────────────────────────────────────────────
def auditer_sies(lignes: dict, extraits_texte: tuple[str, ...], texte: str | None = None) -> list[str]:
    texte = texte_source(sante.SIES_SOURCE_ID) if texte is None else texte
    ecarts = []
    for cle, (ligne, (pass_, las)) in lignes.items():
        if not _present(ligne, texte):
            ecarts.append(f"sies:{cle}: ligne absente du PDF : {ligne!r}")
            continue
        # Les deux dernières colonnes de la ligne sont PASS 2022 et L.AS 2022.
        nombres = re.findall(r"\d+,\d", ligne)
        attendu = [f"{pass_:.1f}".replace(".", ","), f"{las:.1f}".replace(".", ",")]
        if nombres[-2:] != attendu:
            ecarts.append(f"sies:{cle}: valeurs {attendu} != colonnes PASS/L.AS 2022 {nombres[-2:]}")
    for extrait in extraits_texte:
        if not _present(extrait, texte):
            ecarts.append(f"sies: extrait absent du PDF : {extrait!r}")
    return ecarts


def auditer_capacites(c: sante.Capacites, extraits_autres: dict[str, tuple[str, ...]],
                      lecture_visuelle: set[str], lire=None) -> tuple[list[str], list[str]]:
    """(écarts, sources non mesurées) d'une université."""
    ecarts, non_mesure = [], []
    par_source: dict[str, list[tuple[str, dict]]] = {}
    for nom, f in c.par_filiere.items():
        par_source.setdefault(f.get("source_id", c.source_id), []).append((nom, f))
    for source_id, filieres in par_source.items():
        extraits = c.extraits if source_id == c.source_id else extraits_autres.get(source_id, ())
        if not extraits:
            ecarts.append(f"{c.universite}: {source_id} sans extrait")
            continue
        if source_id in lecture_visuelle:
            non_mesure.append(source_id)
        else:
            texte = (lire or texte_source)(source_id)
            ecarts += [f"{c.universite}: extrait absent de {source_id} : {e!r}" for e in extraits if not _present(e, texte)]
        mots = set(re.findall(r"\d+", " ".join(extraits)))
        for nom, f in filieres:
            sommes = f.get("somme_de") or {}
            for cle in _CLES_NOMBRE:
                if cle not in f or f[cle] is None:
                    continue
                if cle in sommes:
                    parts = [_chemin(f, n) for n in sommes[cle]]
                    if None in parts:
                        ecarts.append(f"{c.universite}:{nom}:{cle}: ligne additionnée introuvable {sommes[cle]}")
                    elif sum(parts) != f[cle]:
                        ecarts.append(f"{c.universite}:{nom}:{cle}: {f[cle]} != somme publiée {sum(parts)}")
                elif str(f[cle]) not in mots:
                    ecarts.append(f"{c.universite}:{nom}:{cle}: {f[cle]} absent des extraits de {source_id}")
            for n in _nombres(f.get("detail") or {}):
                if str(n) not in mots:
                    ecarts.append(f"{c.universite}:{nom}:detail: {n} absent des extraits de {source_id}")
    return ecarts, sorted(set(non_mesure))


def auditer_sources(recherches=None, lignes=None, extraits_autres=None) -> dict:
    recherches = sante_universites.RECHERCHES if recherches is None else recherches
    lignes = sante.SIES_LIGNES if lignes is None else lignes
    extraits_autres = sante_universites.EXTRAITS_AUTRES_SOURCES if extraits_autres is None else extraits_autres
    ecarts = auditer_sies(lignes, sante.SIES_EXTRAITS_TEXTE)
    non_mesure, valeurs = [], 0
    manquantes = [u for u in sante.PANEL if u not in recherches]
    ecarts += [f"panel: {u} sans recherche" for u in manquantes]
    for r in recherches.values():
        if r.capacites is None:
            if not r.urls:
                ecarts.append(f"{r.universite}: non disponible sans page consultée")
            continue
        e, nm = auditer_capacites(r.capacites, extraits_autres, sante_universites.LECTURE_VISUELLE)
        ecarts += e
        non_mesure += nm
        valeurs += sum(1 for f in r.capacites.par_filiere.values() for k in _CLES_NOMBRE if f.get(k) is not None)
    return {"ecarts": ecarts, "non_mesure": sorted(set(non_mesure)), "valeurs_capacites": valeurs,
            "lignes_sies": len(lignes)}


# ── 2. corpus ───────────────────────────────────────────────────────────────────────────────
def auditer_corpus(corpus: list[dict], fiche_to_text) -> dict:
    recherches = sante_universites.RECHERCHES
    ecarts, fiches, compte = [], 0, {"capacites": 0, "passage_universite": 0}
    for f in corpus:
        if not sante.CalculSante.concernee(f):
            continue
        fiches += 1
        s = f.get("sante") or {}
        voie = sante.VOIE[f["fili_code"]]
        nat = (s.get("passage_national") or {}).get("valeur") or {}
        if nat != sante.passage_national(voie):
            ecarts.append(f"{f['cod_aff_form']}: passage_national différent de la table SIES")
        cap = s.get("capacites_universite") or {}
        u = sante.universite_de(f.get("etablissement") or "")
        attendu = recherches.get(u).capacites if u in recherches else None
        if cap.get("statut") == "disponible":
            compte["capacites"] += 1
            if attendu is None or cap["valeur"]["par_filiere"] != {k: attendu.par_filiere.get(k) for k in sante.FILIERES_MMOPK}:
                ecarts.append(f"{f['cod_aff_form']}: capacités différentes de la table ({u})")
        elif attendu is not None:
            ecarts.append(f"{f['cod_aff_form']}: capacités publiées par {u} mais non disponibles sur la fiche")
        if (s.get("passage_universite") or {}).get("statut") == "disponible":
            compte["passage_universite"] += 1
        texte = fiche_to_text(f)
        taux = sante.SIES_LIGNES["ensemble"][1][0 if voie == "PASS" else 1]
        if f"{taux}".replace(".", ",") + " %" not in texte:
            ecarts.append(f"{f['cod_aff_form']}: taux national {taux} non écrit")
    return {"fiches": fiches, "ecarts": ecarts, **compte}


# ── 3. contrôle positif ─────────────────────────────────────────────────────────────────────
def saboter(levier: str):
    """(recherches, lignes SIES, extraits autres, corpus_mutateur) cassés par le levier."""
    recherches = dict(sante_universites.RECHERCHES)
    lignes = dict(sante.SIES_LIGNES)
    autres = dict(sante_universites.EXTRAITS_AUTRES_SOURCES)
    mutateur = None
    if levier == "sies":
        ligne, (p, l) = lignes["medecine"]
        lignes["medecine"] = (ligne, (round(p + 0.1, 1), l))
    elif levier in ("capacite", "somme", "extrait"):
        u = {"capacite": "Université de Lille", "somme": "Nantes Université", "extrait": "Université de Bordeaux"}[levier]
        r = recherches[u]
        c = r.capacites
        pf = copy.deepcopy(c.par_filiere)
        extraits = c.extraits
        if levier == "capacite":
            pf["medecine"]["PASS"] += 1
        elif levier == "somme":
            pf["medecine"]["LAS"] += 1
        else:
            extraits = tuple(e.replace("Médecine 425", "Médecine 426") for e in extraits)
        recherches[u] = dataclasses.replace(r, capacites=dataclasses.replace(c, par_filiere=pf, extraits=extraits))
    elif levier == "corpus":
        def mutateur(corpus):
            for f in corpus:
                if sante.CalculSante.concernee(f) and f["sante"]["passage_national"]["statut"] == "disponible":
                    f["sante"]["passage_national"]["valeur"]["admis_mmopk_1_ou_2_ans_pct"] += 1
                    return
    else:
        raise ValueError(f"levier inconnu : {levier} (connus : {', '.join(LEVIERS)})")
    return recherches, lignes, autres, mutateur


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=RACINE / "data/processed/formations_etape_b2.json")
    ap.add_argument("--saboter", choices=LEVIERS)
    ap.add_argument("--sortie", type=Path, default=None, help="rapport JSON (suffixé par le levier si sabotage)")
    args = ap.parse_args(argv)

    recherches, lignes, autres, mutateur = (None, None, None, None)
    if args.saboter:
        recherches, lignes, autres, mutateur = saboter(args.saboter)
    rapport = {"sources": auditer_sources(recherches, lignes, autres)}
    if args.corpus.exists():
        from src.eval.donnee.texte import charger_fiche_to_text
        corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
        if mutateur:
            mutateur(corpus)
        rapport["corpus"] = auditer_corpus(corpus, charger_fiche_to_text(None))
    else:
        rapport["corpus"] = {"absent": str(args.corpus)}
    ecarts = rapport["sources"]["ecarts"] + rapport["corpus"].get("ecarts", [])
    rapport["verdict"] = "ROUGE" if ecarts else ("VERT, sauf NON MESURÉ : " + ", ".join(rapport["sources"]["non_mesure"])
                                                if rapport["sources"]["non_mesure"] else "VERT")
    rapport["saboter"] = args.saboter
    texte = json.dumps(rapport, ensure_ascii=False, indent=2)
    if args.sortie:
        sortie = args.sortie.with_name(f"{args.sortie.stem}.sabote-{args.saboter}{args.sortie.suffix}") if args.saboter else args.sortie
        sortie.write_text(texte + "\n", encoding="utf-8")
    print(texte)
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
