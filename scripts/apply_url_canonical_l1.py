"""L1 - enrich RNCP fiches with REAL France Competences fiche URLs in formations.json.

Context (ordre 2026-06-15-0911, corpus OrientAI Levier 1):
  RNCP (5181) + rncp_blocs (4891) fiches had no real clickable fiche link
  (url_type=fallback_search / none). France Competences fiche pages live at
  https://www.francecompetences.fr/recherche/rncp/<NUM>/ . That route soft-404s
  (returns HTTP 200 for non-existent numbers) so we gate on CONTENT: the page must
  echo its own 'RNCP<num>' code. Verified per fiche -> zero dead links by construction.

Field strategy:
  p2 (default)   : set url + url_canonical + url_type='direct_francecompetences'.
                   `url` is needed because the runtime strict picker
                   _pick_real_fiche_url (structured payload / clickable source chips)
                   reads lien_form_psup > url_onisep > url and IGNORES url_canonical
                   by design (A1 excluded the ONISEP search fallback). Writing `url`
                   makes the link clickable in the recit demo. Pure metadata, no code.
  canonical-only : set url_canonical + url_type only (P1 variant; expects a separate
                   runtime relax of _pick_real_fiche_url to surface it).

Safety:
  - Corpus is gitignored (ADR-046) -> rollback = backup file (taken separately:
    data/processed/formations.json.bak-pre-l1-url-YYYYMMDD).
  - Preserves fiche order + count (FAISS index alignment) - asserts count unchanged.
  - NO re-embed: url_* fields are not consumed by fiche_to_text (embeddings).
  - Atomic write (tmp + os.replace).

Usage:
  python3 scripts/apply_url_canonical_l1.py                      # dry-run (verify + report)
  python3 scripts/apply_url_canonical_l1.py --apply              # write in place (P2)
  python3 scripts/apply_url_canonical_l1.py --apply --strategy canonical-only
"""
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

PATH = "data/processed/formations.json"
SOURCES = ("rncp", "rncp_blocs")
FC_URL = "https://www.francecompetences.fr/recherche/rncp/{num}/"
WORKERS = 8


def rncp_num(fiche):
    """Extract the numeric RNCP id from `rncp` ('RNCP37299') or `id` ('rncp_blocs:RNCP35185')."""
    for v in (fiche.get("rncp"), fiche.get("id")):
        if v:
            m = re.search(r"RNCP(\d+)", str(v))
            if m:
                return m.group(1)
    return None


def verify(num):
    """Fetch the FC fiche page; True only if the body echoes 'RNCP<num>' (real fiche, not soft-404)."""
    url = FC_URL.format(num=num)
    try:
        r = subprocess.run(
            ["curl", "-sS", "-L", "-A", "Mozilla/5.0 (X11; Linux x86_64)",
             "--retry", "3", "--retry-delay", "1", "--retry-all-errors",
             "--max-time", "25", url],
            capture_output=True, text=True, timeout=60,
        )
        return num, (f"RNCP{num}" in r.stdout)
    except Exception:
        return num, False


def verify_all(nums):
    verdict = {}
    done = 0
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(verify, n): n for n in nums}
        for fut in as_completed(futs):
            n, ok = fut.result()
            verdict[n] = ok
            done += 1
            if done % 500 == 0:
                print(f"[info] verified {done}/{len(nums)}", file=sys.stderr)
    # Second pass: re-verify MISSes sequentially (gentle) to rescue transient throttling.
    misses = [n for n, ok in verdict.items() if not ok]
    if misses:
        print(f"[info] re-verifying {len(misses)} misses sequentially…", file=sys.stderr)
        for n in misses:
            _, ok = verify(n)
            if ok:
                verdict[n] = True
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write formations.json in place")
    ap.add_argument("--strategy", choices=["p2", "canonical-only"], default="p2")
    args = ap.parse_args()

    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    n0 = len(data)

    targets = [(i, rncp_num(e)) for i, e in enumerate(data)
               if e.get("source") in SOURCES and rncp_num(e)]
    nums = sorted({n for _, n in targets})
    print(f"[info] targets={len(targets)} unique_nums={len(nums)} strategy={args.strategy} "
          f"apply={args.apply}", file=sys.stderr)

    verdict = verify_all(nums)

    stats = {}
    for i, num in targets:
        src = data[i]["source"]
        st = stats.setdefault(src, {"set": 0, "miss": 0})
        if verdict.get(num):
            url = FC_URL.format(num=num)
            data[i]["url_canonical"] = url
            data[i]["url_type"] = "direct_francecompetences"
            if args.strategy == "p2":
                data[i]["url"] = url
            st["set"] += 1
        else:
            st["miss"] += 1

    assert len(data) == n0, f"COUNT CHANGED {n0} -> {len(data)}"

    if args.apply:
        tmp = PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, PATH)

    report = {
        "applied": args.apply,
        "strategy": args.strategy,
        "count": len(data),
        "unique_nums_verified": len(nums),
        "resolved_unique": sum(1 for v in verdict.values() if v),
        "by_source": stats,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
