"""Gate FORME ADAPTATIVE (ordre 1926) — LOT brut 21 récits pour jugement Jarvis.

Génère, pour les 12 récits seed (R01-R12) + 9 récits de test (T1-T9 fournis par
Jarvis), la réponse récit avec la FORME ADAPTATIVE active (format routé +
overlays + sortie typée). Produit :
  - un rapport markdown (LOT brut EN BLOC pour le jugement humain, anti-boucle) ;
  - un JSON `structured_examples` (un payload NarrativeResponse par format =
    contrat d'interface frontend, ordre 1926 Option A) ;
  - des métriques de gate : distribution des formats, scope (détresse vs
    in_scope, contrôle négatif T9/R12), parse-success-rate PAR FORMAT, latence,
    et le check T3 (fiche porteuse salaire type MIAGE Lille citée bonne source).

Usage : python audit_empirique_2026-06-09/gate_narrative_forme.py
(racine repo ; nécessite index FAISS + Mistral key).
"""
from __future__ import annotations

import json
import time
import unicodedata

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline

FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
SEED_PATH = "data/recits_seed.json"
OUT_MD = "audit_empirique_2026-06-09/results/gate_narrative_forme_LOT.md"
OUT_JSON = "audit_empirique_2026-06-09/results/gate_narrative_forme_structured.json"
TOP_SHOW = 6


# Récits de test fournis par Jarvis (ordre 1926), texte accentué = source.
T_RECITS = [
    {"id": "T1", "type": "exploratoire", "text":
        "Je suis en terminale générale (spé maths et SES) à Toulouse, j'ai de bonnes notes un peu "
        "partout mais honnêtement je n'ai aucune idée de ce que je veux faire après le bac. J'aime "
        "bien comprendre comment marche l'économie et la société, je suis assez à l'aise à l'oral, "
        "mais je ne me vois pas faire 5 ans d'études très théoriques. Je voudrais rester dans le Sud "
        "si possible. Qu'est-ce qui pourrait me correspondre ?"},
    {"id": "T2", "type": "comparaison", "text":
        "Je suis en terminale STMG à Lyon, admise sur Parcoursup à la fois en BUT GEA et en BTS "
        "Comptabilité-Gestion. Je n'arrive pas à choisir. Je veux travailler assez vite mais sans me "
        "fermer de portes si jamais je veux continuer en école après. Lequel est le mieux pour moi ?"},
    {"id": "T3", "type": "trajectoire", "text":
        "Je suis en L2 de droit à Lille mais je m'ennuie et les débouchés me font peur. J'avais pris "
        "l'option NSI au lycée et le code m'avait beaucoup plu. J'aimerais basculer vers le "
        "développement ou la data, mais j'ai peur d'avoir perdu deux années pour rien et mes parents "
        "s'inquiètent pour le salaire. Je suis bloqué à Lille. Comment je peux faire la transition ?"},
    {"id": "T4", "type": "validation", "text":
        "Je suis en terminale générale avec les spés maths et NSI, j'ai 15 de moyenne, et je pense "
        "candidater en MIAGE après une licence d'informatique. J'aime les maths appliquées et l'idée "
        "de faire le pont entre l'informatique et la gestion d'entreprise, mais je n'aime pas du tout "
        "le développement web pur toute la journée. Est-ce que MIAGE c'est un bon choix pour mon profil ?"},
    {"id": "T5", "type": "conseil", "text":
        "Je suis en BTS SIO option SLAM à Nantes et je voudrais continuer en alternance dans le "
        "développement, mais surtout pas dans le conseil ou la cybersécurité qui ne m'attirent pas. "
        "Je veux rester dans la région nantaise. Quelles écoles ou licences pro en alternance vous me conseillez ?"},
    {"id": "T6", "type": "comparaison", "text":
        "Je suis en terminale générale spé maths et physique à Rennes, j'ai un bon dossier. Je suis "
        "admis à la fois en prépa MPSI et en BUT Informatique, et je n'arrive vraiment pas à trancher. "
        "La prépa me fait un peu peur niveau rythme mais ça ouvre les écoles d'ingé, le BUT a l'air "
        "plus concret et plus court. Lequel correspond le mieux à quelqu'un qui veut devenir ingénieur sans se cramer ?"},
    {"id": "T7", "type": "shortlist", "text":
        "Je suis en terminale générale avec les spés maths et SVT à Bordeaux, 16 de moyenne, et je "
        "veux faire une école d'ingénieur post-bac plutôt dans le biomédical ou les biotechnologies. "
        "J'ai déjà pas mal réfléchi, je connais mon projet. Donne-moi juste les meilleures écoles "
        "d'ingé post-bac en bio/santé que je devrais viser, pas besoin de tout m'expliquer."},
    {"id": "T8", "type": "anchor_constraint", "text":
        "Je suis en terminale techno STI2D près de Clermont-Ferrand, je voudrais continuer dans "
        "l'informatique ou l'électronique. Le truc c'est que ma famille n'a pas les moyens, je ne peux "
        "pas payer une école privée à plusieurs milliers d'euros par an, il me faut absolument du "
        "public ou de l'alternance rémunérée. Et je ne peux pas trop m'éloigner de la maison. "
        "Qu'est-ce qui est possible pour moi ?"},
    {"id": "T9", "type": "reassure-frontiere-secu", "text":
        "Je suis en première année de licence d'éco-gestion à Montpellier et franchement je stresse à "
        "mort. J'ai l'impression de m'être trompé, tout le monde autour de moi a l'air sûr de soi et "
        "pas moi, j'ai peur de gâcher mon année et de décevoir mes parents. J'aime bien l'analyse de "
        "données et les langues mais je sais plus quoi en faire. Vous pouvez m'aider à y voir clair ?"},
]


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c)).lower()


def unwrap(r):
    return r.get("fiche", r) if isinstance(r, dict) else r


def fiche_label(f):
    f = unwrap(f)
    return str(f.get("nom") or f.get("libelle_humain") or f.get("libelle") or f.get("text", "")[:60]).strip()


def fiche_geo(f):
    f = unwrap(f)
    return f"{f.get('etablissement','')} ({f.get('ville','')}/{f.get('region','')})".strip()


def _fiche_blob(f):
    f = unwrap(f)
    return _norm(" ".join(str(f.get(k, "")) for k in ("nom", "libelle_humain", "etablissement", "ville", "region", "text")))


def is_miage_lille(f):
    blob = _fiche_blob(f)
    miage = "miage" in blob or "methodes informatiques appliquees a la gestion" in blob
    return miage and "lille" in blob


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)
    print("Chargement corpus + index...")
    with open(FICHES_PATH, encoding="utf-8") as fh:
        fiches = json.load(fh)
    seed = json.load(open(SEED_PATH, encoding="utf-8"))["recits"]
    recits = [{"id": r["id"], "type": r.get("type", "seed"), "text": r["text"]} for r in seed] + T_RECITS

    pipe = make_production_pipeline(
        client, fiches,
        enable_narrative_mode=True,
        enable_validator=False,
        enable_golden_qa=False,
        enable_post_process=False,
    )
    pipe.load_index_from(INDEX_PATH)
    print(f"Pipeline prêt (narrative={pipe.enable_narrative_mode}), {len(fiches)} fiches, {len(recits)} récits.")

    lines: list[str] = ["# Gate FORME ADAPTATIVE — LOT brut 21 récits (ordre 1926)\n",
                        "Jugement EN BLOC (anti-boucle). Format routé déterministe + overlays + sortie typée.\n"]
    structured_examples: dict[str, dict] = {}
    fmt_count: dict[str, int] = {}
    conf_by_fmt: dict[str, list[float]] = {}
    latencies: list[float] = []
    scope_flags: list[str] = []
    t3_miage = {"rank": None, "source": None}
    errors: list[str] = []

    def _flush():
        with open(OUT_MD, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        with open(OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump(structured_examples, fh, ensure_ascii=False, indent=2)

    def _answer(text, attempts=3):
        last = None
        for a in range(attempts):
            try:
                return pipe.answer(text), None
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"    {type(e).__name__} (try {a+1}/{attempts})")
                time.sleep(4)
        return (None, []), last

    for r in recits:
        rid, text = r["id"], r["text"]
        pipe.last_narrative_format_decision = None
        pipe.last_narrative_structured = None
        t0 = time.time()
        (answer, top), err = _answer(text)
        dt = time.time() - t0

        if err is not None:
            lines.append(f"\n## {rid} ({r['type']}) — GENERATION ERROR {type(err).__name__}\n---")
            errors.append(rid)
            _flush()
            continue

        latencies.append(dt)
        scope = pipe.last_scope_result.label if pipe.last_scope_result else "n/a"
        scope_flags.append(f"{rid}:{scope}")
        dec = pipe.last_narrative_format_decision
        struct = pipe.last_narrative_structured
        prof = pipe.last_narrative_profile

        fmt = dec.format if dec else "(court-circuit)"
        fmt_count[fmt] = fmt_count.get(fmt, 0) + 1
        conf = struct.get("parse_confidence") if struct else None
        if conf is not None:
            conf_by_fmt.setdefault(fmt, []).append(conf)
        if struct and fmt not in structured_examples and dec:
            structured_examples[fmt] = struct  # 1 exemple par format pour le contrat front

        lines.append(f"\n## {rid} ({r['type']}) — scope={scope} — {dt:.1f}s")
        if dec:
            ov = [k for k, v in (("anchor", dec.anchor_constraint), ("reassure", dec.reassure)) if v]
            lines.append(f"- **format routé: `{fmt}`** (source={dec.source}, overlays={ov or 'aucun'}, "
                         f"marqueurs={list(dec.matched.keys())})")
            if dec.constraint_terms:
                lines.append(f"- contrainte ancrée: {dec.constraint_terms}")
        if prof:
            lines.append(f"- profil: intent={prof.intent_type} sector={prof.sector_interest} "
                         f"a_eviter={prof.a_eviter} mobilite={prof.mobilite} urgent={prof.urgent_concern}")
        lines.append(f"- parse_confidence: {conf}")
        if top:
            lines.append(f"- top {min(TOP_SHOW,len(top))}/{len(top)} fiches:")
            for i, f in enumerate(top[:TOP_SHOW]):
                mark = "  <== MIAGE LILLE" if is_miage_lille(f) else ""
                lines.append(f"    {i+1}. {fiche_label(f)[:55]} | {fiche_geo(f)}{mark}")
        if rid == "T3":
            hit = next((i + 1 for i, f in enumerate(top) if is_miage_lille(f)), None)
            t3_miage["rank"] = hit
            if struct:
                # source citée sur la fiche salaire ?
                for b in struct.get("blocks", []):
                    for it in b.get("items", []):
                        if "miage" in _norm(it.get("titre", "")) or "lille" in _norm(it.get("markdown", "")):
                            t3_miage["source"] = it.get("sources")
        lines.append(f"\n### Réponse brute {rid}\n")
        lines.append((answer or "").strip())
        lines.append("\n---")
        print(f"  {rid}: fmt={fmt} scope={scope} conf={conf} ({dt:.1f}s)")
        _flush()

    # --- Synthèse métriques ---
    lines.append("\n\n# SYNTHÈSE GATES\n")
    lines.append(f"- Distribution formats: {fmt_count}")
    lines.append(f"- Scope (tous attendus in_scope ; T9/R12 = contrôle négatif): {scope_flags}")
    parse_summary = {f: round(sum(v) / len(v), 3) for f, v in conf_by_fmt.items()}
    lines.append(f"- Parse-success-rate (parse_confidence moyen) PAR FORMAT: {parse_summary}")
    if latencies:
        srt = sorted(latencies)
        p50 = srt[len(srt) // 2]
        lines.append(f"- Latence: p50={p50:.1f}s max={max(latencies):.1f}s (gate <15s)")
    lines.append(f"- T3 (cas démo): MIAGE Lille rang={t3_miage['rank']} source_citée={t3_miage['source']}")
    if errors:
        lines.append(f"- ERREURS génération (à rejouer): {errors}")
    _flush()

    print("\n=== SYNTHÈSE ===")
    print("formats:", fmt_count)
    print("parse_conf:", parse_summary)
    print("scope:", scope_flags)
    if latencies:
        print(f"latence p50={sorted(latencies)[len(latencies)//2]:.1f}s max={max(latencies):.1f}s")
    print("T3 MIAGE:", t3_miage)
    print(f"\nRapports: {OUT_MD} + {OUT_JSON}")


if __name__ == "__main__":
    main()
