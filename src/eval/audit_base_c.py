"""Audit de la base de l'étape C (contrat results/donnee_etape_c/CONTRACT.md, section 11).

Code de lecture séparé de celui de la construction : l'audit relit le corpus par les chemins du
catalogue (`chemin_corpus`) et les bruts par les noms officiels (`nom_officiel`), jamais par les
fonctions de `src.collect.base_etape_c`. Chaque contrôle publie ce qu'il a comparé ; un contrôle qui
compare zéro valeur est rouge, pas vert.

- `python -m src.eval.audit_base_c` : audit de la base, écrit results/donnee_etape_c/audit/audit.json.
- `python -m src.eval.audit_base_c --sabotages` : reconstruit la base sous chaque levier
  ORIENTIA_SABOTAGE_C, et exige que le contrôle visé rougisse (sabotages.json).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from src.base_c import SANS_SESSION, haversine_km
from src.collect.sources_officielles import RACINE, chemin_verifie

BASE = RACINE / "data/processed/base_etape_c.sqlite"
CORPUS = RACINE / "data/processed/formations_etape_b2.json"
EXPORT = RACINE / "data/processed/base_etape_c.explorateur.json"
GATE = Path.home() / "projets/_orientai-ref/verticale-2026-09/gate_c/requetes_gate_c.json"
SORTIE = RACINE / "results/donnee_etape_c/audit"

TEMOIN = {"id": "psup:7596", "taux_acces@2025": 34, "places@2025": 96}  # banc vertical, vérifié contre l'API le 23/09

# Contrôle visé par chaque sabotage ; « construction » = la base doit refuser de se construire.
CIBLES = {
    "valeur": "base_contre_corpus", "source": "construction", "portee": "portee_sante",
    "geo": "coordonnees_contre_brut", "perimetre": "couverture_gate", "absent": "completude",
    "insee": "insee_apprentissage", "null_muet": "construction",
}


# ── Lecture indépendante ───────────────────────────────────────────────────────────────────
def lire(obj, chemin: str):
    for m in chemin.split("."):
        if isinstance(obj, list):
            if not m.isdigit() or int(m) >= len(obj):
                return None
            obj = obj[int(m)]
        elif isinstance(obj, dict):
            if m not in obj:
                return None
            obj = obj[m]
        else:
            return None
    return obj


def pour_espace(texte: str, espace: str) -> str | None:
    if not texte:
        return None
    if "=" not in texte:
        return texte
    return dict(p.split("=", 1) for p in texte.split("|")).get(espace)


def nombre(x):
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str) and x.strip() != "":
        try:
            return float(x)
        except ValueError:
            return None
    return None


def egal(a, b) -> bool:
    return a is not None and b is not None and math.isclose(float(a), float(b), rel_tol=0, abs_tol=0)


class Audit:
    def __init__(self, base: Path, corpus: Path | None, gate: Path | None, export: Path | None):
        self.con = sqlite3.connect(f"file:{base}?mode=ro", uri=True)
        self.con.row_factory = sqlite3.Row
        self.corpus = json.loads(corpus.read_bytes()) if corpus else None
        self.gate = json.loads(gate.read_bytes()) if gate and gate.exists() else None
        self.export = export
        self.controles: dict[str, dict] = {}
        self.champs = {r["champ"]: dict(r) for r in self.con.execute("SELECT * FROM champ")}
        self.formations = {r["id"]: dict(r) for r in self.con.execute("SELECT * FROM formation")}
        self.valeurs = {(r["id"], r["champ"], r["session"]): dict(r) for r in self.con.execute("SELECT * FROM valeur")}

    def noter(self, nom: str, vert: bool, compares: int, **details) -> None:
        # Une comparaison sur zéro élément ne prouve rien : elle est rouge (règle 9 de Claudette).
        self.controles[nom] = {"vert": bool(vert) and compares > 0, "compares": compares, **details}

    # 1. Base contre corpus, 100 %, dans les deux sens
    def base_contre_corpus(self) -> None:
        fiches = {}
        for f in self.corpus:
            if f.get("source") == "parcoursup":
                fiches[f"psup:{f['cod_aff_form']}"] = f
            elif f.get("source") == "parcoursup_apprentissage":
                fiches[f"psup_app:{f['cod_aff_form']}"] = f
        ecarts, compares, manquantes_base, orphelines = [], 0, [], []
        attendues = set()
        for fid, form in self.formations.items():
            if form["espace"] == "mm":
                continue
            f = fiches.get(fid)
            if f is None:
                orphelines.append(fid)
                continue
            for nom, c in self.champs.items():
                if form["espace"] not in c["espaces"].split(",") or (c["types"] and form["type"] not in c["types"].split(",")):
                    continue
                ch = pour_espace(c["chemin_corpus"], form["espace"])
                if not ch:
                    continue
                sessions = [SANS_SESSION] if c["sessions"] == SANS_SESSION else (pour_espace(c["sessions"], form["espace"]) or "").split(",")
                for s in sessions:
                    if s == SANS_SESSION and not ch:
                        continue
                    brut = lire(f, ch.replace("{s}", s))
                    cle = (fid, nom, s)
                    b = self.valeurs.get(cle)
                    if c["type_valeur"] == "groupe":
                        env = brut if isinstance(brut, dict) else None
                        statut_corpus = (env or {}).get("statut")
                        if env is None:
                            continue
                        attendues.add(cle)
                        compares += 1
                        if b is None:
                            manquantes_base.append(cle)
                        elif b["statut"] != statut_corpus or (b["statut"] == "non_disponible" and b["raison"] != env.get("raison")):
                            ecarts.append({"cle": cle, "base": [b["statut"], b["raison"]], "corpus": [statut_corpus, env.get("raison")]})
                        continue
                    if c["parent"]:
                        parent = lire(f, pour_espace(self.champs[c["parent"]]["chemin_corpus"], form["espace"]) or "")
                        if not isinstance(parent, dict) or parent.get("statut") != "disponible":
                            continue
                    if c["type_valeur"] == "texte":
                        if brut is None:
                            continue
                        attendues.add(cle)
                        compares += 1
                        if b is None or b["valeur_texte"] != str(brut):
                            ecarts.append({"cle": cle, "base": None if b is None else b["valeur_texte"], "corpus": brut})
                        continue
                    v = nombre(brut)
                    if c["parent"] and v is None:
                        continue
                    attendues.add(cle)
                    compares += 1
                    if b is None:
                        manquantes_base.append(cle)
                    elif v is None:
                        if b["statut"] != "non_disponible":
                            ecarts.append({"cle": cle, "base": b["valeur_num"], "corpus": None})
                    elif not egal(b["valeur_num"], v):
                        ecarts.append({"cle": cle, "base": b["valeur_num"], "corpus": v})
        # Sens base -> corpus : toute valeur post-bac de la base a été vue ci-dessus.
        sans_corpus = [k for k in self.valeurs if k[0].split(":")[0] in ("psup", "psup_app") and k not in attendues]
        self.noter("base_contre_corpus", not ecarts and not manquantes_base and not sans_corpus and not orphelines, compares,
                   ecarts=len(ecarts), exemples=[str(e) for e in ecarts[:5]], manquantes_dans_la_base=len(manquantes_base),
                   exemples_manquantes=[str(m) for m in manquantes_base[:5]],
                   valeurs_base_sans_correspondant_corpus=len(sans_corpus), exemples_sans_corpus=[str(k) for k in sans_corpus[:5]],
                   formations_absentes_du_corpus=len(orphelines))

    # 2. Base contre bruts verrouillés (témoin indépendant du corpus)
    def base_contre_bruts(self) -> None:
        bruts = {s: {r["cod_aff_form"]: r for r in _csv(chemin_verifie(f"parcoursup_{s}"))} for s in ("2023", "2024", "2025")}
        app = {r["cod_aff_form"]: r for r in _csv(chemin_verifie("parcoursup_apprentissage_2025"))}
        mm = {m["ifc"]: m for m in json.loads(chemin_verifie("monmaster_2025").read_bytes())}
        compares, ecarts, presence = 0, [], []
        par_espace_compte = {"psup": 0, "psup_app": 0, "mm": 0}
        for (fid, nom, s), b in self.valeurs.items():
            c = self.champs[nom]
            espace, ident = fid.split(":", 1)
            off = pour_espace(c["nom_officiel"], espace)
            if not off or s == SANS_SESSION:
                continue
            if espace == "psup":
                ligne = bruts[s].get(ident)
            elif espace == "psup_app":
                ligne = app.get(ident)
            else:
                ligne = mm.get(ident)
            if ligne is None:
                if b["statut"] == "disponible" or "absente" not in (b["raison"] or ""):
                    presence.append({"cle": [fid, nom, s], "base": b["statut"], "brut": "ligne absente"})
                continue
            v = nombre(ligne.get(off))
            compares += 1
            par_espace_compte[espace] += 1
            if v is None and b["statut"] == "disponible":
                ecarts.append({"cle": [fid, nom, s], "base": b["valeur_num"], "brut": ligne.get(off)})
            elif v is not None and (b["statut"] != "disponible" or not egal(b["valeur_num"], v)):
                ecarts.append({"cle": [fid, nom, s], "base": b["valeur_num"], "brut": v, "champ_officiel": off})
        self.noter("valeurs_contre_bruts", not ecarts, compares, par_espace=par_espace_compte, ecarts=len(ecarts),
                   exemples=[str(e) for e in ecarts[:5]], ecarts_de_presence=len(presence),
                   exemples_presence=[str(p) for p in presence[:5]])
        # Présence : une formation déclarée absente d'une session l'est vraiment dans le brut.
        self.noter("sessions_absentes_contre_bruts", not presence, compares, ecarts=len(presence))
        # Coordonnées
        geo = {**{f"psup:{k}": r.get("g_olocalisation_des_formations") for k, r in bruts["2025"].items()},
               **{f"psup_app:{k}": r.get("g_olocalisation_des_formations") for k, r in app.items()}}
        cmp_geo, ecarts_geo = 0, []
        for r in self.con.execute("SELECT id, lat, lon FROM lieu WHERE precision_geo = 'formation'"):
            txt = geo.get(r["id"]) or ""
            try:
                la, lo = (float(x) for x in txt.split(","))
            except ValueError:
                ecarts_geo.append({"id": r["id"], "brut": txt})
                continue
            cmp_geo += 1
            if not (egal(r["lat"], la) and egal(r["lon"], lo)):
                ecarts_geo.append({"id": r["id"], "base": [r["lat"], r["lon"]], "brut": [la, lo]})
        self.noter("coordonnees_contre_brut", not ecarts_geo, cmp_geo, ecarts=len(ecarts_geo), exemples=ecarts_geo[:5])

    # 3. Forme
    def forme(self) -> None:
        pct = [(k, v["valeur_num"]) for k, v in self.valeurs.items()
               if v["statut"] == "disponible" and v["unite"] == "%" and not (0 <= float(v["valeur_num"]) <= 100)]
        n_pct = sum(1 for v in self.valeurs.values() if v["statut"] == "disponible" and v["unite"] == "%")
        self.noter("taux_entre_0_et_100", not pct, n_pct, hors_bornes=len(pct), exemples=[str(p) for p in pct[:5]])
        sources = {r["source_id"] for r in self.con.execute("SELECT source_id FROM source")}
        sans = [k for k, v in self.valeurs.items() if v["statut"] == "disponible" and v["source_id"] not in sources]
        n_dispo = sum(1 for v in self.valeurs.values() if v["statut"] == "disponible")
        self.noter("source_de_chaque_chiffre", not sans, n_dispo, sans_source=len(sans))
        sans_url = [s for s in sources if not self.con.execute("SELECT url FROM source WHERE source_id = ?", (s,)).fetchone()[0]]
        self.noter("url_de_chaque_source", True, len(sources), sources_sans_url=sorted(sans_url),
                   note="une source sans URL (fiche concept) est listée, pas jugée")
        # Portée : toute valeur dont le catalogue fixe une portée non « formation » la porte.
        mauvaises, n = [], 0
        for k, v in self.valeurs.items():
            attendue = self.champs[k[1]]["portee"]
            if attendue == "formation":
                continue
            n += 1
            if v["portee"] != attendue:
                mauvaises.append({"cle": k, "base": v["portee"], "attendue": attendue})
        self.noter("portee_sante", not mauvaises, n, ecarts=len(mauvaises), exemples=[str(m) for m in mauvaises[:5]])
        calcule = [c for c in self.champs if "taux_admission" in c]
        self.noter("aucun_taux_calcule_monmaster", not calcule, len(self.champs), champs=calcule)
        zero = self.con.execute("SELECT COUNT(*) FROM lieu WHERE lat = 0 AND lon = 0").fetchone()[0]
        n_lieux = self.con.execute("SELECT COUNT(*) FROM lieu").fetchone()[0]
        self.noter("aucun_lieu_a_zero", zero == 0, n_lieux, lieux_a_zero=zero)

    # 4. Complétude : une ligne par formation x champ applicable x session
    def completude(self) -> None:
        attendues, manquantes, en_trop = set(), [], []
        for fid, form in self.formations.items():
            for nom, c in self.champs.items():
                if c["parent"] or form["espace"] not in c["espaces"].split(","):
                    continue
                if c["types"] and form["type"] not in c["types"].split(","):
                    continue
                if nom == "alternance" and form["espace"] != "psup" and form["espace"] != "mm":
                    continue
                sessions = [SANS_SESSION] if c["sessions"] == SANS_SESSION else (pour_espace(c["sessions"], form["espace"]) or "").split(",")
                for s in sessions:
                    attendues.add((fid, nom, s))
        for k in attendues:
            if k not in self.valeurs:
                manquantes.append(k)
        for k, v in self.valeurs.items():
            if self.champs[k[1]]["parent"]:
                continue
            if k not in attendues:
                en_trop.append(k)
        self.noter("completude", not manquantes and not en_trop, len(attendues), manquantes=len(manquantes),
                   exemples_manquantes=[str(m) for m in manquantes[:5]], en_trop=len(en_trop),
                   exemples_en_trop=[str(m) for m in en_trop[:5]])
        # Un détail n'existe que sous un groupe disponible.
        orphelins = [k for k, v in self.valeurs.items() if self.champs[k[1]]["parent"]
                     and (self.valeurs.get((k[0], self.champs[k[1]]["parent"], SANS_SESSION)) or {}).get("statut") != "disponible"]
        n_det = sum(1 for k in self.valeurs if self.champs[k[1]]["parent"])
        self.noter("details_sous_groupe_disponible", not orphelins, n_det, orphelins=len(orphelins))

    # 5. Géographie
    def geographie(self) -> None:
        # Identités mathématiques de la distance (indépendantes de toute donnée) :
        # 1 degré d'arc = 2*pi*6371/360 km ; pôle - équateur = pi*6371/2 km.
        a = haversine_km(0, 0, 0, 1)
        b = haversine_km(0, 0, 90, 0)
        ok = math.isclose(a, 2 * math.pi * 6371 / 360, rel_tol=1e-12) and math.isclose(b, math.pi * 6371 / 2, rel_tol=1e-12)
        self.noter("distance_identites", ok, 2, un_degre_km=a, pole_equateur_km=b)
        sans = self.con.execute("SELECT COUNT(*) FROM lieu l JOIN formation f ON f.id = l.id "
                                "WHERE f.espace = 'psup_app' AND l.code_insee IS NULL").fetchone()[0]
        n_app = self.con.execute("SELECT COUNT(*) FROM formation WHERE espace = 'psup_app'").fetchone()[0]
        self.noter("insee_apprentissage", sans == 0, n_app, sans_code_insee=sans)
        # Information, non jugée : lieux dont le GPS officiel est à plus de 40 km du centre de leur commune.
        loin = []
        for r in self.con.execute("SELECT l.id, l.lat, l.lon, c.lat AS clat, c.lon AS clon, l.commune FROM lieu l "
                                  "JOIN commune c ON c.code_insee = l.code_insee WHERE l.precision_geo = 'formation'"):
            d = haversine_km(r["lat"], r["lon"], r["clat"], r["clon"])
            if d > 40:
                loin.append({"id": r["id"], "commune_siege": r["commune"], "km": round(d, 1)})
        self.controles["info_sites_loin_de_leur_commune"] = {"vert": None, "liste": loin,
            "note": "supposé, non établi : la coordonnée officielle désignerait le site d'enseignement et la commune le "
                    "siège administratif (ex. psup:35500, PASS de Rennes, GPS près de Vannes). Fiches officielles non relues."}
        lieux_sans = self.con.execute("SELECT COUNT(DISTINCT id) FROM lieu WHERE precision_geo = 'non_disponible'").fetchone()[0]
        masters_sans = self.con.execute("SELECT COUNT(*) FROM formation f WHERE espace = 'mm' AND NOT EXISTS "
                                        "(SELECT 1 FROM lieu l WHERE l.id = f.id AND l.lat IS NOT NULL)").fetchone()[0]
        self.controles["info_lieux_sans_coordonnees"] = {"vert": None, "formations_avec_un_lieu_non_resolu": lieux_sans,
                                                        "masters_sans_aucune_coordonnee": masters_sans}

    # 6. Témoin positif
    def temoin(self) -> None:
        ok, vu = True, {}
        for cle, attendu in TEMOIN.items():
            if cle == "id":
                continue
            champ, session = cle.split("@")
            v = self.valeurs.get((TEMOIN["id"], champ, session))
            src = None if v is None else self.con.execute("SELECT url FROM source WHERE source_id = ?", (v["source_id"],)).fetchone()
            vu[cle] = None if v is None else {"valeur": v["valeur_num"], "source": v["source_id"], "url": src[0] if src else None}
            ok = ok and v is not None and egal(v["valeur_num"], attendu) and bool(src and src[0])
        self.noter("temoin_psup_7596", ok, len(TEMOIN) - 1, attendu=TEMOIN, lu=vu)

    # 7. Couverture du gate (périmètre)
    def couverture_gate(self) -> None:
        if self.gate is None:
            self.noter("couverture_gate", False, 0, note="fichier du gate introuvable")
            return
        ids = {i for r in self.gate["requetes"] for i in r["attendus"] + (r.get("frontiere") or [])}
        absents = sorted(i for i in ids if i not in self.formations)
        self.noter("couverture_gate", not absents, len(ids), absents=absents)

    # 8. Aller-retour base -> export -> règle de décompression (contrat v1.3.1)
    def export_aller_retour(self) -> None:
        if not self.export or not self.export.exists():
            self.noter("export_aller_retour", False, 0, note="export absent")
            return
        d = json.loads(self.export.read_bytes())
        dico = d["dico"]
        cle_id = {"psup": "cod_aff_form", "psup_app": "cod_aff_form", "mm": "ifc"}
        compares, ecarts = 0, []
        for f in d["formations"]:
            for cle, x in f["v"].items():
                champ, _, s = cle.partition("@")
                b = self.valeurs.get((f["id"], champ, s or SANS_SESSION))
                if x[3] is None:
                    ident = f"{cle_id[f['espace']]}={f['id'].split(':', 1)[1]};champ={pour_espace(d['champs'][champ]['nom_officiel'], f['espace']) or ''}"
                else:
                    ident = x[3] or None
                decode = {"valeur": x[0], "source_id": None if x[1] is None else dico["sources"][x[1]],
                          "millesime": None if x[2] is None else dico["millesimes"][x[2]], "identifiant_source": ident,
                          "raison": None if x[4] is None else dico["raisons"][x[4]], "portee": None if x[5] is None else dico["portees"][x[5]]}
                compares += 1
                base = None if b is None else {"valeur": b["valeur_num"] if b["valeur_num"] is not None else b["valeur_texte"],
                                               **{k: b[k] for k in ("source_id", "millesime", "identifiant_source", "raison", "portee")}}
                if base != decode:
                    ecarts.append({"cle": [f["id"], cle], "base": base, "export": decode})
        ok_meta = d["meta"].get("n_formations") == len(self.formations) and d["meta"].get("n_valeurs") == len(self.valeurs)
        self.noter("export_aller_retour", not ecarts and compares == len(self.valeurs) and ok_meta, compares,
                   valeurs_base=len(self.valeurs), ecarts=len(ecarts), exemples=[str(e) for e in ecarts[:3]],
                   meta_complete=ok_meta, octets=self.export.stat().st_size)

    def tout(self) -> dict:
        if self.corpus is not None:
            self.base_contre_corpus()
        self.base_contre_bruts()
        self.forme()
        self.completude()
        self.geographie()
        self.temoin()
        self.couverture_gate()
        self.export_aller_retour()
        juges = {k: v for k, v in self.controles.items() if v["vert"] is not None}
        return {"verts": sum(v["vert"] for v in juges.values()), "juges": len(juges), "controles": self.controles}


def _csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def determinisme(base: Path) -> dict:
    """Reconstruit la base dans un dossier temporaire et compare l'empreinte canonique."""
    from src.collect.base_etape_c import empreinte_canonique
    avant, _ = empreinte_canonique(base)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-m", "src.collect.base_etape_c", "--sortie", tmp, "--sans-copie-resultats"],
                       cwd=RACINE, check=True, capture_output=True, env={k: v for k, v in os.environ.items() if k != "ORIENTIA_SABOTAGE_C"})
        apres, _ = empreinte_canonique(Path(tmp) / "base_etape_c.sqlite")
        octets_identiques = (Path(tmp) / "base_etape_c.sqlite").read_bytes() == base.read_bytes()
    return {"vert": avant == apres, "compares": 1, "empreinte_1": avant, "empreinte_2": apres,
            "fichier_identique_octet_pour_octet": octets_identiques}


def sabotages(corpus: Path, gate: Path) -> dict:
    from src.collect.base_etape_c import SABOTAGES
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for nom in SABOTAGES:
            env = {**os.environ, "ORIENTIA_SABOTAGE_C": nom}
            p = subprocess.run([sys.executable, "-m", "src.collect.base_etape_c", "--sortie", tmp], cwd=RACINE,
                               env=env, capture_output=True, text=True)
            cible = CIBLES[nom]
            description = SABOTAGES[nom]
            if p.returncode != 0:
                derniere = (p.stderr.strip().splitlines() or ["?"])[-1]
                out[nom] = {"description": description, "cible": cible, "rouge_sur_sa_cible": cible == "construction",
                            "resultat": "construction refusée", "erreur": derniere}
                continue
            base = Path(tmp) / f"base_etape_c.sabote-{nom}.sqlite"
            export = Path(tmp) / f"base_etape_c.sabote-{nom}.explorateur.json"
            r = Audit(base, corpus, gate, export).tout()
            rouges = sorted(k for k, v in r["controles"].items() if v["vert"] is False)
            out[nom] = {"description": description, "cible": cible, "rouge_sur_sa_cible": cible in rouges, "resultat": "base construite",
                        "controles_rouges": rouges}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=BASE)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--gate", type=Path, default=GATE)
    ap.add_argument("--export", type=Path, default=EXPORT)
    ap.add_argument("--sabotages", action="store_true")
    ap.add_argument("--sans-determinisme", action="store_true")
    ap.add_argument("--sortie", type=Path, default=SORTIE)
    args = ap.parse_args(argv)
    args.sortie.mkdir(parents=True, exist_ok=True)
    if args.sabotages:
        s = sabotages(args.corpus, args.gate)
        (args.sortie / "sabotages.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for nom, r in s.items():
            print(f"{'ROUGE sur sa cible' if r['rouge_sur_sa_cible'] else 'VERT (défaut non vu)'} : {nom} -> {r['cible']}  "
                  f"{r.get('controles_rouges') or r.get('erreur')}")
        return 0 if all(r["rouge_sur_sa_cible"] for r in s.values()) else 1
    r = Audit(args.base, args.corpus, args.gate, args.export).tout()
    if not args.sans_determinisme:
        r["controles"]["determinisme"] = determinisme(args.base)
        r["verts"] += r["controles"]["determinisme"]["vert"]
        r["juges"] += 1
    (args.sortie / "audit.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    for nom, c in r["controles"].items():
        etat = "info" if c["vert"] is None else ("VERT " if c["vert"] else "ROUGE")
        print(f"{etat}  {nom}  compares={c.get('compares')}")
    print(f"{r['verts']}/{r['juges']} contrôles verts")
    return 0 if r["verts"] == r["juges"] else 1


if __name__ == "__main__":
    sys.exit(main())
