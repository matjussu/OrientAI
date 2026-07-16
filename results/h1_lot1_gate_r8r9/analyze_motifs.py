"""Analyse déterministe des motifs R8/R9 sur une sortie de batterie golden.

Observables (gratuits, regex, par question) :
- r9_tag_avant : nb de chiffres dont le tag [SX] le plus proche est AVANT
  (motif R9 : source annoncée puis chiffre)
- r9_tag_apres : nb de chiffres suivis d'un tag [source SX] (motif legacy)
- r8_constat : la réponse contient le constat d'absence R8
- bloc_sources_final : présence d'un bloc "Sources :" en fin (interdit R9)
- n_mots : longueur (surveille la dérive R6)

Usage : python analyze_motifs.py battery_AVANT.json battery_APRES.json
"""
import json
import re
import sys

NUM = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|€|places|mots)?")
TAG = re.compile(r"\[(?:source\s+)?S\d+\]")
R8_CONSTAT = re.compile(r"je n'ai pas\s+.{0,80}?dans mes sources", re.IGNORECASE | re.DOTALL)
BLOC_SOURCES = re.compile(r"\n\s*\*{0,2}sources?\s*\*{0,2}\s*:\s*(?:\[?S\d|\S)", re.IGNORECASE)


def analyze_answer(text: str) -> dict:
    tags = [(m.start(), m.end()) for m in TAG.finditer(text)]
    tag_avant = tag_apres = 0
    for m in NUM.finditer(text):
        # ignore les nombres dans les tags eux-memes ou les URLs
        seg = text[max(0, m.start() - 8):m.start()]
        if "[S" in seg or "source S" in seg or "http" in text[max(0, m.start() - 60):m.start()]:
            continue
        # tag le plus proche avant (meme ligne) et apres (fenetre 40 chars)
        line_start = text.rfind("\n", 0, m.start()) + 1
        before = [t for t in tags if line_start <= t[1] <= m.start()]
        after = [t for t in tags if m.end() <= t[0] <= m.end() + 40]
        if before and (not after or (m.start() - before[-1][1]) < (after[0][0] - m.end())):
            tag_avant += 1
        elif after:
            tag_apres += 1
    return {
        "r9_tag_avant": tag_avant,
        "r9_tag_apres": tag_apres,
        "r8_constat": bool(R8_CONSTAT.search(text)),
        "bloc_sources_final": bool(BLOC_SOURCES.search(text)),
        "n_mots": len(text.split()),
    }


def load(path: str) -> dict:
    rows = json.load(open(path))
    return {r["id"]: analyze_answer(r.get("answer") or "") for r in rows if not r.get("error")}


def main() -> None:
    a_path, b_path = sys.argv[1], sys.argv[2]
    A, B = load(a_path), load(b_path)
    ids = sorted(set(A) & set(B))
    print(f"questions comparables : {len(ids)}")

    def agg(d, key):
        vals = [d[i][key] for i in ids]
        if isinstance(vals[0], bool):
            return sum(vals)
        return sum(vals)

    for key in ("r9_tag_avant", "r9_tag_apres", "r8_constat", "bloc_sources_final"):
        print(f"{key:22s} AVANT={agg(A, key):4d}  APRES={agg(B, key):4d}")
    ma = sum(A[i]["n_mots"] for i in ids) / len(ids)
    mb = sum(B[i]["n_mots"] for i in ids) / len(ids)
    print(f"{'n_mots moyen':22s} AVANT={ma:6.1f} APRES={mb:6.1f}")

    print("\nAttribution par question (deltas de motif) :")
    for i in ids:
        da, db = A[i], B[i]
        changes = []
        if da["r8_constat"] != db["r8_constat"]:
            changes.append(f"r8_constat {da['r8_constat']}->{db['r8_constat']}")
        ratio_a = da["r9_tag_avant"] - da["r9_tag_apres"]
        ratio_b = db["r9_tag_avant"] - db["r9_tag_apres"]
        if (ratio_b - ratio_a) != 0:
            changes.append(f"r9_avant-apres {ratio_a:+d}->{ratio_b:+d}")
        if da["bloc_sources_final"] != db["bloc_sources_final"]:
            changes.append(f"bloc_sources {da['bloc_sources_final']}->{db['bloc_sources_final']}")
        if changes:
            print(f"  {i}: " + " ; ".join(changes))


if __name__ == "__main__":
    main()
