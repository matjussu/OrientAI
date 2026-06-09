"""C1 diff-validation : baseline-merge vs C1-merge (isole l'effet C1 pur).

Le merge est DÉTERMINISTE (fingerprints tous distincts) -> on diffe par
empreinte de contenu, puis on apparie les fiches changées par IDENTITÉ pour
vérifier que C1 est ADDITIF (nouvelles fiches + champs remplis là où null),
pas une altération des fiches existantes.
"""
import json
import sys
import unicodedata
import re

BASE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/c1merge/out_baseline.json"
C1 = sys.argv[2] if len(sys.argv) > 2 else "/tmp/c1merge/out_c1.json"


def _norm(s):
    if s is None:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def identity(f):
    cod = (f.get("cod_aff_form") or "").strip()
    if cod:
        return ("cod", cod)
    if f.get("id"):
        return ("id", str(f["id"]))
    return ("nev", f.get("source"), _norm(f.get("nom")), _norm(f.get("etablissement")), _norm(f.get("ville")))


def fp(f):
    return json.dumps(f, sort_keys=True, ensure_ascii=False)


def load(p):
    d = json.load(open(p))
    return list(d.values()) if isinstance(d, dict) else d


bf, cf = load(BASE), load(C1)
print(f"baseline: {len(bf)} fiches | C1: {len(cf)} fiches | delta net: {len(cf)-len(bf):+d}")

b_fp = {fp(f): f for f in bf}
c_fp = {fp(f): f for f in cf}
unchanged = b_fp.keys() & c_fp.keys()
removed_fps = b_fp.keys() - c_fp.keys()   # formes baseline disparues
added_fps = c_fp.keys() - b_fp.keys()     # formes C1 nouvelles
print(f"\nINCHANGÉES (byte-identiques) : {len(unchanged)}")
print(f"formes baseline disparues     : {len(removed_fps)}")
print(f"formes C1 nouvelles           : {len(added_fps)}")

# Apparier par identité : enrichies (id des 2 côtés) vs vraiment nouvelles / supprimées
removed_by_id = {identity(b_fp[k]): b_fp[k] for k in removed_fps}
added_by_id = {identity(c_fp[k]): c_fp[k] for k in added_fps}
enriched_ids = removed_by_id.keys() & added_by_id.keys()
new_ids = added_by_id.keys() - removed_by_id.keys()
gone_ids = removed_by_id.keys() - added_by_id.keys()

print(f"\nNOUVELLES fiches (identité absente du baseline) : {len(new_ids)}")
print(f"ENRICHIES (même identité, contenu changé)       : {len(enriched_ids)}")
print(f"SUPPRIMÉES (identité disparue)                   : {len(gone_ids)}  {'<<< FLAG' if gone_ids else 'OK'}")

# Vérifier que les ENRICHIES sont additives (champs ajoutés, pas de valeur altérée)
IDENTITY = {"nom", "etablissement", "ville", "region", "niveau", "source", "statut", "type_diplome"}
field_adds, value_changes, identity_changes = {}, [], []
for idk in enriched_ids:
    b, c = removed_by_id[idk], added_by_id[idk]
    for kk in c:
        if kk not in b or b.get(kk) in (None, "", [], {}):
            field_adds[kk] = field_adds.get(kk, 0) + 1
    for kk in b:
        if kk in c and b.get(kk) not in (None, "", [], {}) and c.get(kk) != b.get(kk):
            (identity_changes if kk in IDENTITY else value_changes).append((idk, kk, b.get(kk), c.get(kk)))

print("\n  top champs REMPLIS sur les enrichies :")
for kk, n in sorted(field_adds.items(), key=lambda x: -x[1])[:12]:
    print(f"    {n:5}  {kk}")
print(f"\n  valeurs modifiées (champs non-identité) : {len(value_changes)}")
for idk, kk, bv, cv in value_changes[:8]:
    print(f"    {kk}: {str(bv)[:18]} -> {str(cv)[:18]}  @ {idk}")
print(f"  changements d'IDENTITÉ : {len(identity_changes)}  {'<<< FLAG GRAVE' if identity_changes else 'OK'}")
for idk, kk, bv, cv in identity_changes[:8]:
    print(f"    {kk}: {str(bv)[:18]} -> {str(cv)[:18]}  @ {idk}")

clean = (len(gone_ids) == 0 and len(identity_changes) == 0)
print(f"\n=== VERDICT : {'ADDITIF PROPRE' if clean else 'NON-ADDITIF — STOP+FLAG'} ===")
print(f"    +{len(new_ids)} nouvelles, {len(enriched_ids)} enrichies, {len(gone_ids)} supprimées, "
      f"{len(value_changes)} valeurs modifiées, {len(identity_changes)} identités modifiées")
