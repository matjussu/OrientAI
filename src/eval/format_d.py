"""Étape D : les trois formats de fiche joués au banc (protocole results/donnee_etape_d/PROTOCOLE.md).

- A : `fiche_to_text` du corpus B-2, ce que le modèle lit aujourd'hui (référence) ;
- B : carte structurée générée depuis la base C, chaque chiffre avec son libellé, son unité, son
  millésime, sa source et une définition courte ;
- C : carte courte (au plus 7 chiffres clés) + l'outil `lire_fiche`, qui rend la carte B.

Deux contrôles de contenu : `controle_b_contre_base` (chaque valeur de la base sur la ligne de son champ)
et `controle_a_dans_b` (chaque chiffre de A retrouvé dans B, par couple valeur et unité ; les écarts
que la base C ne peut pas porter sont classés par motif). Leviers : ORIENTIA_SABOTAGE_D=carte_b_valeur | carte_b_manque.
"""
from __future__ import annotations

import json
import os
import re

from src.base_c.outils import Base, lire_fiche

SABOTAGES_D = {
    "carte_b_valeur": "une valeur de la carte B modifiée (+1) : taux d'accès 2025 de psup:7596",
    "carte_b_manque": "un champ retiré de la carte B : places 2025 de psup:7596",
}

# Colonnes d'insertion_ligne rendues, avec leur libellé (noms officiels, contrat C v1.4 section 7).
# Le taux d'emploi stable n'est pas rendu : InserSup ne publie pas sa définition (contrat B, section 0).
INSERTION_RENDUE = (
    ("taux_emploi_salarie_fr_6m", "taux d'emploi salarié en France à 6 mois", "%"),
    ("taux_emploi_salarie_fr_12m", "taux d'emploi salarié en France à 12 mois", "%"),
    ("taux_emploi_salarie_fr_18m", "taux d'emploi salarié en France à 18 mois", "%"),
    ("taux_emploi_6m", "taux d'emploi à 6 mois", "%"),
    ("taux_emploi_12m", "taux d'emploi à 12 mois", "%"),
    ("taux_poursuite_etudes", "poursuite d'études", "%"),
    ("salaire_median_net_12m_eur", "salaire médian net à 12 mois", "euros"),
    ("effectif_sortants", "diplômés sortis des études, suivis à 12 mois", "diplômés"),
    ("effectif_poursuivants", "diplômés qui poursuivent", "diplômés"),
)

# Carte courte C : champs retenus, dans l'ordre, au plus 7 (règle écrite avant le run, protocole §4).
COURTE_POSTBAC = ("taux_acces@2025", "places@2025", "cout.droits_inscription_eur", "cout.scolarite_annuel_eur",
                  "alternance", "passage_mmopk_1_ou_2_ans_national")
COURTE_MASTER = ("capacite@2025", "candidats_pp@2025", "alternance")
MAX_COURTE = 7

_URL = re.compile(r"https?://\S+")


def _fmt(v) -> str:
    """Nombre écrit à la française, sans zéro inutile (64.71 -> 64,71 ; 34.0 -> 34)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    if float(v).is_integer():
        return str(int(v))
    return f"{v}".replace(".", ",")


def _unite(u: str | None) -> str:
    return {"EUR": "euros", "%": "%", None: "", "": ""}.get(u, u or "")


def _definition_courte(champ: dict) -> str:
    d = champ.get("definition") or ""
    if "En clair :" in d:
        return d.split("En clair :", 1)[1].strip()
    return d.split(". ")[0].strip().rstrip(".")


class Formats:
    """Rend les formats A, B et C d'une fiche, identifiée par son id de base C (psup:, psup_app:, mm:)."""

    def __init__(self, base: Base, corpus: list[dict], sabotage: str | None = None):
        from src.rag.embeddings import fiche_to_text
        self.base = base
        self.fiche_to_text = fiche_to_text
        self.sabotage = sabotage if sabotage is not None else (os.environ.get("ORIENTIA_SABOTAGE_D") or None)
        if self.sabotage and self.sabotage not in SABOTAGES_D:
            raise ValueError(f"ORIENTIA_SABOTAGE_D={self.sabotage!r} inconnu ; connus : {', '.join(SABOTAGES_D)}")
        self.champs = {r["champ"]: dict(r) for r in base.con.execute("SELECT * FROM champ")}
        self.sources = {r["source_id"]: dict(r) for r in base.con.execute("SELECT * FROM source")}
        self.corpus = {}
        for f in corpus:
            src = f.get("source")
            if src == "parcoursup":
                self.corpus.setdefault(f"psup:{f.get('cod_aff_form')}", f)
            elif src == "parcoursup_apprentissage":
                self.corpus.setdefault(f"psup_app:{f.get('cod_aff_form')}", f)
            elif src == "monmaster" and isinstance(f.get("id_mon_master"), dict) and f["id_mon_master"].get("ifc"):
                # 405 des 480 masters de la base ont leur fiche au corpus (mesure du 23/09, dette C section 5)
                self.corpus.setdefault(f"mm:{f['id_mon_master']['ifc']}", f)

    def rendable(self, id_: str) -> bool:
        """Une fiche entre dans l'exposition seulement si A (corpus) et B (base) savent la rendre."""
        return id_ in self.corpus and self.base.con.execute(
            "SELECT 1 FROM formation WHERE id = ?", (id_,)).fetchone() is not None

    # ── A
    def texte_a(self, id_: str) -> str:
        return self.fiche_to_text(self.corpus[id_])

    # ── B
    def _valeurs(self, id_: str) -> tuple[dict, dict]:
        f = lire_fiche(self.base, id_)
        valeurs = dict(f["valeurs"])
        if id_ == "psup:7596" and self.sabotage == "carte_b_valeur" and "taux_acces@2025" in valeurs:
            valeurs["taux_acces@2025"] = {**valeurs["taux_acces@2025"], "valeur": valeurs["taux_acces@2025"]["valeur"] + 1}
        if id_ == "psup:7596" and self.sabotage == "carte_b_manque":
            valeurs.pop("places@2025", None)
        return f, valeurs

    def _entete(self, f: dict) -> str:
        form = f["formation"]
        lieu = (f["lieux"] or [{}])[0]
        specialite = form.get("specialite")
        if specialite and specialite.lower() in form["intitule"].lower():
            specialite = None
        morceaux = [form["intitule"], specialite, form.get("etablissement"),
                    f"{lieu.get('commune')} ({lieu.get('departement')})" if lieu.get("commune") else None,
                    form.get("statut"), form.get("selectivite"),
                    "en apprentissage" if form.get("apprentissage") else None]
        lien = f" | fiche officielle : {form['lien_officiel']}" if form.get("lien_officiel") else ""
        return f"[fiche {form['id']}] " + " | ".join(m for m in morceaux if m) + lien

    @staticmethod
    def _valeur_lisible(v: dict) -> str:
        if v.get("unite") == "0/1":
            return "oui" if v["valeur"] else "non"
        return f"{_fmt(v['valeur'])} {_unite(v.get('unite'))}".rstrip()

    def _renvoi(self, sources: list[str], sid: str | None) -> str:
        if not sid:
            return ""
        if sid not in sources:
            sources.append(sid)
        return f"S{sources.index(sid) + 1}"

    def _ligne_champ(self, champ: str, entrees: list[tuple[str, dict]], sources: list[str], avec_definition: bool) -> str:
        """Une ligne par champ : ses sessions, chacune avec son millésime et son renvoi de source."""
        c = self.champs.get(champ, {})
        morceaux = []
        for _, v in entrees:
            quand = v.get("millesime") or ""
            renvoi = self._renvoi(sources, v.get("source_id"))
            if v["statut"] != "disponible":
                morceaux.append(f"non disponible ({quand}{', ' if quand else ''}{v.get('raison')})")
                continue
            portee = f", portée {v['portee']}" if v.get("portee") not in (None, "formation") else ""
            morceaux.append(f"{self._valeur_lisible(v)} ({quand}{portee}, {renvoi})")
        ligne = f"- {c.get('libelle') or champ} : " + " ; ".join(morceaux)
        if avec_definition:
            d, nd = _definition_courte(c), (c.get("ne_dit_pas") or "").strip()
            if d:
                ligne += f". Définition : {d.rstrip('.')}"
            if nd:
                ligne += f". Ne dit pas : {nd.rstrip('.')}"
        return ligne

    def _legende(self, sources: list[str]) -> str:
        return "Sources : " + " ; ".join(
            f"S{i + 1} {(self.sources.get(sid) or {}).get('libelle') or sid}" for i, sid in enumerate(sources))

    def _par_champ(self, valeurs: dict) -> dict[str, list[tuple[str, dict]]]:
        groupes: dict[str, list[tuple[str, dict]]] = {}
        # sessions de la plus récente à la plus ancienne
        for cle in sorted(valeurs, key=lambda k: (k.partition("@")[0], -int(k.partition("@")[2] or 0))):
            champ = cle.partition("@")[0]
            v = valeurs[cle]
            if v["statut"] == "disponible" and v.get("unite") in ("détails", "lignes"):
                continue  # groupe (coût, insertion, santé) : ses détails suivent, le compte seul ne dit rien
            groupes.setdefault(champ, []).append((cle, v))
        return groupes

    def carte_b(self, id_: str) -> str:
        f, valeurs = self._valeurs(id_)
        sources: list[str] = []
        lignes = [self._entete(f)]
        for champ, entrees in self._par_champ(valeurs).items():
            lignes.append(self._ligne_champ(champ, entrees, sources, avec_definition=True))
        for lg in f["insertion"]:
            chiffres = [f"{lib} {_fmt(lg[col])} {u}" for col, lib, u in INSERTION_RENDUE if lg.get(col) is not None]
            if chiffres:
                lignes.append(f"- Insertion ({lg['dispositif']}, promotion {lg['promotion']}, {lg['diplome']}, "
                              f"{lg['etablissement']}, {self._renvoi(sources, lg['source_id'])}) : " + " ; ".join(chiffres))
        for al in f["alternance_liens"]:
            cap = f", {_fmt(al['capacite'])} places" if al.get("capacite") is not None else ""
            lignes.append(f"- Existe en apprentissage : {al['etablissement']}, {al['commune']}{cap} ({al['id_apprentissage']})")
        lignes.append(self._legende(sources))
        return "\n".join(lignes)

    # ── C
    def carte_c(self, id_: str) -> str:
        f, valeurs = self._valeurs(id_)
        groupes = self._par_champ(valeurs)
        sources: list[str] = []
        lignes = [self._entete(f)]
        n = 0
        for cle in (COURTE_MASTER if id_.startswith("mm:") else COURTE_POSTBAC):
            if cle in valeurs and n < MAX_COURTE:
                lignes.append(self._ligne_champ(cle.partition("@")[0], [(cle, valeurs[cle])], sources, avec_definition=False))
                n += 1
        ins = next((lg for lg in f["insertion"] if lg.get("taux_emploi_salarie_fr_12m") is not None
                    or lg.get("taux_emploi_12m") is not None), None)
        if ins and n < MAX_COURTE:
            col = "taux_emploi_salarie_fr_12m" if ins.get("taux_emploi_salarie_fr_12m") is not None else "taux_emploi_12m"
            lib = dict((c, l) for c, l, _ in INSERTION_RENDUE)[col]
            lignes.append(f"- Insertion ({ins['dispositif']}, promotion {ins['promotion']}, "
                          f"{self._renvoi(sources, ins['source_id'])}) : {lib} {_fmt(ins[col])} %")
        lignes.append(self._legende(sources))
        lignes.append(f"(fiche complète avec définitions : lire_fiche(\"{id_}\"))")
        del groupes
        return "\n".join(lignes)


# ── Contrôles de contenu ────────────────────────────────────────────────────────────────────
# 1. B contre la base, champ par champ : chaque valeur disponible (et chaque « non disponible ») de
#    lire_fiche figure sur la ligne de son champ, avec son millésime. Lecture de la base indépendante
#    de `Formats._valeurs`, pour que les leviers ORIENTIA_SABOTAGE_D la fassent rougir.
# 2. A dans B, par couple (valeur, unité) : tout chiffre de A se retrouve dans B. Un nombre de A sans
#    unité se contente de la même valeur. Les écarts que la base C ne peut pas porter sont classés par
#    motif, comptés et publiés ; un écart sans motif est rouge.
_UNITES = {"%": "%", "places": "places", "place": "places", "candidats": "candidats", "euros": "euros",
           "admis": "admis", "propositions": "propositions", "diplômés": "diplômés"}
_COUPLE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,](\d+))?(?![\w])\s*(%|[a-zéèû]+)?", re.IGNORECASE)

# Motifs d'écarts structurels (protocole D §4) : la base C ne porte pas ces chiffres, par construction.
STRUCTURELS = (
    ("niveau", re.compile(r"^(Diplôme visé|Niveau) :"), "niveau du diplôme (bac+N) : pas de champ dans la base C"),
    ("insertion_master", re.compile(r"^Insertion professionnelle \(InserSup"), "insertion des masters non collectée (C, section 2)"),
    ("selectivite_mm", re.compile(r"sélectivité [\d,.]+ ?% admis"), "taux MonMaster calculé, exclu de C (contrôle aucun_taux_calcule_monmaster)"),
    ("definitions", re.compile(r"^Définitions"), "texte des définitions de A (les chiffres qu'il contient ne sont pas des valeurs)"),
    ("ville_cedex", re.compile(r"CEDEX", re.IGNORECASE), "libellé postal de la ville"),
    ("mention_non_renseignee", re.compile(r"mention non renseignée"), "part « mention non renseignée » : pas de champ dans C"),
    ("autres_voies", re.compile(r"autres voies"), "capacités MMOPK « autres voies » : pas de champ dans C"),
    ("precision_capacites", re.compile(r"précision :"), "précision textuelle des capacités MMOPK : pas stockée dans C"),
)


def couples(texte: str) -> list[tuple[float, str, str]]:
    """(valeur, unité, clause) pour chaque nombre ; années 2000 à 2035 et URL écartées."""
    out = []
    for clause in re.split(r" \| |; | — ", _URL.sub(" ", texte or "")):
        for m in _COUPLE.finditer(clause):
            entier = m.group(1).replace(" ", "").replace(" ", "")
            v = float(f"{entier}.{m.group(2)}") if m.group(2) else float(entier)
            if m.group(2) is None and 2000 <= v <= 2035:
                continue
            out.append((v, _UNITES.get((m.group(3) or "").lower(), ""), clause.strip()))
    return out


def nombres(texte: str) -> set[float]:
    return {v for v, _, _ in couples(texte)}


def _motif(clause: str) -> str | None:
    return next((nom for nom, rx, _ in STRUCTURELS if rx.search(clause)), None)


def controle_a_dans_b(formats: Formats, ids: list[str]) -> dict:
    manquants, structurels, compares = {}, {}, 0
    for id_ in ids:
        b = couples(formats.carte_b(id_))
        b_par_valeur = {}
        for v, u, _ in b:
            b_par_valeur.setdefault(v, set()).add(u)
        # La section de A qui porte la clause, pour classer l'écart (« Diplôme visé : bac+3 »).
        sections = formats.texte_a(id_).split(" | ")
        for section in sections:
            for v, u, clause in couples(section):
                compares += 1
                unites_b = b_par_valeur.get(v, set())
                if (u and u in unites_b) or (not u and unites_b):
                    continue
                motif = _motif(section) or _motif(clause)
                if motif:
                    structurels.setdefault(motif, []).append([id_, v])
                else:
                    manquants.setdefault(id_, []).append({"valeur": v, "unite": u, "clause": clause[:160]})
    return {"vert": not manquants and compares > 0, "fiches": len(ids), "chiffres_de_A_compares": compares,
            "ecarts_sans_motif": sum(len(x) for x in manquants.values()), "manquants": manquants,
            "structurels": {m: {"raison": next(r for n, _, r in STRUCTURELS if n == m), "ecarts": len(x),
                                "fiches": len({i for i, _ in x}), "exemples": x[:3]} for m, x in sorted(structurels.items())}}


def controle_b_contre_base(formats: Formats, ids: list[str], carte: str = "b") -> dict:
    """Chaque valeur de la base est sur la ligne de son champ, dans la carte B (ou C pour ses champs)."""
    ecarts, compares = [], 0
    for id_ in ids:
        f = lire_fiche(formats.base, id_)  # lecture indépendante : pas de levier ici
        texte = formats.carte_b(id_) if carte == "b" else formats.carte_c(id_)
        lignes = {}
        for ligne in texte.splitlines():
            if ligne.startswith("- ") and " : " in ligne:
                lib, _, reste = ligne[2:].partition(" : ")
                lignes.setdefault(lib, []).append(reste)
        cles = f["valeurs"]
        if carte == "c":
            courte = COURTE_MASTER if id_.startswith("mm:") else COURTE_POSTBAC
            cles = {k: v for k, v in cles.items() if k in courte}
        for cle, v in cles.items():
            if v["statut"] == "disponible" and v.get("unite") in ("détails", "lignes"):
                continue
            champ = cle.partition("@")[0]
            lib = (formats.champs.get(champ) or {}).get("libelle") or champ
            attendu = (f"{Formats._valeur_lisible(v)} ({v.get('millesime') or ''}" if v["statut"] == "disponible"
                       else f"non disponible ({v.get('millesime') or ''}")
            compares += 1
            if not any(attendu in r for r in lignes.get(lib, [])):
                ecarts.append({"id": id_, "cle": cle, "attendu": attendu, "lignes": lignes.get(lib, [])[:1]})
        if carte == "b":
            for lg in f["insertion"]:
                for col, lib, u in INSERTION_RENDUE:
                    if lg.get(col) is None:
                        continue
                    compares += 1
                    if f"{lib} {_fmt(lg[col])} {u}" not in texte:
                        ecarts.append({"id": id_, "insertion": col, "attendu": lg[col]})
            for al in f["alternance_liens"]:
                compares += 1
                if al["id_apprentissage"] not in texte:
                    ecarts.append({"id": id_, "alternance": al["id_apprentissage"]})
    return {"vert": not ecarts and compares > 0, "carte": carte, "fiches": len(ids), "valeurs_comparees": compares,
            "ecarts": len(ecarts), "exemples": ecarts[:5]}


def main() -> int:
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, default=Path("data/processed/base_etape_c.sqlite"))
    ap.add_argument("--corpus", type=Path, default=Path("data/processed/formations_etape_b2.json"))
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--format", choices=("a", "b", "c"), default="b")
    args = ap.parse_args()
    fm = Formats(Base.ouvrir(args.base), json.loads(args.corpus.read_bytes()))
    for id_ in args.ids:
        print({"a": fm.texte_a, "b": fm.carte_b, "c": fm.carte_c}[args.format](id_), end="\n\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
