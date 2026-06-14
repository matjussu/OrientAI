import re
import unicodedata
from datetime import date
from rapidfuzz import fuzz
from src.collect.normalize import normalize_name, normalize_city
from src.collect.niveau import infer_niveau
from src.collect.rome import get_debouches_for_domain


# Mapping codes NSF (Nomenclature Spécialités Formation) → domaine OrientIA.
# Utilisé pour inférer un `domaine` sur les fiches RNCP + MonMaster qui n'ont
# pas de classification domaine OrientIA native. Couvre les 17 secteurs
# NSF principaux (code première lettre = grand secteur).
_NSF_PREFIX_TO_DOMAIN = {
    "1": "sciences_fondamentales",   # 100-199
    "2": "ingenierie_industrielle",  # 200-249 informatique + 250-299 industrie
    "3": "services",                  # 300-499 services (commerce, santé, transport...)
    "4": "sciences_humaines",         # 410-429 lettres / 500-599 général
}

# Sous-mapping plus granulaire pour les NSF 3xx (services) : secteurs clés.
_NSF_CODE_TO_DOMAIN = {
    "326": "data_ia",                 # Informatique, TIT
    "344": "sante",                   # Technologies médicales
    "331": "sante",                   # Santé
    "332": "social",                  # Travail social — PAS santé : débouchés ROME
                                      # K* (action sociale), jamais J11xx médicaux.
                                      # Fix order 2026-06-11 (cf reclassify_social_health).
    "133": "sciences_fondamentales",  # Maths / physique fondamentales
    "134": "sciences_fondamentales",  # Sciences vie / terre
    "230": "ingenierie_industrielle", # Spécialités pluritechnologiques
    "310": "eco_gestion",             # Commerce, gestion
    "313": "eco_gestion",             # Finance, banque, assurance
    "315": "eco_gestion",             # Ressources humaines
    "125": "sciences_humaines",       # Histoire, géographie
    "126": "sciences_humaines",       # Philosophie
    "131": "langues",                 # Français, littérature, langues
    "136": "langues",                 # Langues vivantes étrangères
    "223": "ingenierie_industrielle", # Métallurgie
    "227": "ingenierie_industrielle", # Énergie
    "343": "communication",           # Communication, information
    "335": "sciences_humaines",       # Animation, tourisme
    "324": "eco_gestion",             # Secrétariat
    "345": "eco_gestion",             # Application informatique gestion
    "100": "sciences_fondamentales",  # Formations générales
    "200": "ingenierie_industrielle",
    "300": "services",
    "400": "sciences_humaines",
    "500": "sciences_humaines",
}


def _infer_domaine_from_nsf(nsf_codes: list) -> str | None:
    """Infère un domaine OrientIA depuis les codes NSF d'une fiche."""
    if not nsf_codes:
        return None
    for nsf in nsf_codes:
        code = nsf.get("code") if isinstance(nsf, dict) else str(nsf)
        if not code:
            continue
        # Match exact code 3 digits
        if code in _NSF_CODE_TO_DOMAIN:
            return _NSF_CODE_TO_DOMAIN[code]
    # Fallback sur préfixe 1-chiffre
    for nsf in nsf_codes:
        code = nsf.get("code") if isinstance(nsf, dict) else str(nsf)
        if code and code[0] in _NSF_PREFIX_TO_DOMAIN:
            return _NSF_PREFIX_TO_DOMAIN[code[0]]
    return None


def _infer_domaine_from_rome(rome_codes: list) -> str | None:
    """Infère un domaine OrientIA depuis les codes ROME d'une fiche."""
    if not rome_codes:
        return None
    # M18* = informatique/data, J* = santé, K* = social, M1405+ = data scientist
    first = rome_codes[0]
    code = first.get("code") if isinstance(first, dict) else str(first)
    if not code:
        return None
    if code.startswith("M18") or code in {"M1405", "M1419", "M1423", "M1811", "M1868", "M1894"}:
        return "data_ia" if code in {"M1405", "M1419", "M1423", "M1811", "M1868", "M1894"} else "cyber"
    if code.startswith("J"):
        return "sante"
    if code.startswith("K"):
        return "social"
    if code.startswith("M1"):
        return "ingenierie_industrielle"
    if code.startswith("C"):
        return "eco_gestion"
    if code.startswith("D"):
        return "ingenierie_industrielle"
    if code.startswith("E"):
        return "ingenierie_industrielle"
    if code.startswith("H"):
        return "ingenierie_industrielle"
    if code.startswith("F"):
        return "ingenierie_industrielle"  # Construction, BTP
    if code.startswith("G"):
        return "services"  # Hôtellerie restauration
    if code.startswith("L"):
        return "communication"  # Arts, spectacle, communication
    return None


def dedup_parcoursup_by_cod_aff_form(fiches: list[dict]) -> list[dict]:
    """Déduplique les fiches Parcoursup par `cod_aff_form` (ADR-050).

    Le merger v2 produit des doublons stricts pour ~1 324 codes Parcoursup
    (= 2 648 records répétés) parce que `legacy` (issu de `merge_all` sur
    CSV brut) ET `parcoursup_extended` (sources pré-normalisées) contiennent
    les mêmes `cod_aff_form`. Audit data 2026-04-25 a confirmé : 5.4 % du
    corpus formations est en double avec ce mécanisme silencieux.

    Stratégie de fusion (évite la perte d'information) :
    1. Groupe les fiches par `cod_aff_form` non vide.
    2. Pour chaque groupe (size > 1), choisit la fiche **la plus enrichie**
       comme base (max nb champs non-vides).
    3. **Merge soft** : tout champ absent de la base est complété depuis
       les autres fiches du groupe (premier non-vide). Préserve `labels`
       depuis legacy même si la base est extended.
    4. Retourne la liste filtrée + ordre stable (1ère occurrence du
       cod_aff_form en input).

    Fiches sans `cod_aff_form` (autres sources) sont préservées telles
    quelles.
    """
    from collections import OrderedDict

    keep_first_pos: dict[str, int] = {}
    groups: dict[str, list[dict]] = OrderedDict()

    for i, f in enumerate(fiches):
        caf = f.get("cod_aff_form")
        if not caf:
            continue
        if caf not in keep_first_pos:
            keep_first_pos[caf] = i
        groups.setdefault(caf, []).append(f)

    def _merge_group(group: list[dict]) -> dict:
        if len(group) == 1:
            return group[0]

        def _filled_count(rec: dict) -> int:
            return sum(1 for v in rec.values() if v not in (None, "", [], {}))

        base = max(group, key=_filled_count)
        merged = dict(base)
        for other in group:
            if other is base:
                continue
            for k, v in other.items():
                if v in (None, "", [], {}):
                    continue
                if merged.get(k) in (None, "", [], {}):
                    merged[k] = v
        return merged

    out: list[dict] = []
    seen_caf: set[str] = set()
    for f in fiches:
        caf = f.get("cod_aff_form")
        if not caf:
            out.append(f)
            continue
        if caf in seen_caf:
            continue
        seen_caf.add(caf)
        out.append(_merge_group(groups[caf]))
    return out


def merge_by_rncp(parcoursup: list[dict], onisep: list[dict]) -> list[dict]:
    onisep_by_rncp = {f["rncp"]: f for f in onisep if f.get("rncp")}
    merged = []
    for ps in parcoursup:
        rncp = ps.get("rncp")
        if rncp and rncp in onisep_by_rncp:
            merged_fiche = {**onisep_by_rncp[rncp], **ps}
            merged_fiche["match_method"] = "rncp"
            merged.append(merged_fiche)
    return merged


def _signature(fiche: dict) -> str:
    return f"{normalize_name(fiche.get('nom',''))} {normalize_name(fiche.get('etablissement',''))} {normalize_city(fiche.get('ville',''))}"


def fuzzy_match_fiches(
    parcoursup: list[dict],
    onisep: list[dict],
    threshold: int = 85,
    min_tokens: int = 4,
    require_onisep_etab: bool = True,
) -> list[dict]:
    """Fuzzy match parcoursup fiches to onisep fiches with precision guards.

    Two anti-spurious-match filters were added after run 4 revealed 280+
    fuzzy_100.0 matches where the signatures were too short or generic:

    1. `min_tokens` : require the PARCOURSUP signature to have at least N
       tokens. Short signatures like "master ia" match many things at 100%
       and pollute the merge with noise.
    2. `require_onisep_etab` : only consider onisep candidates that have a
       populated etablissement field. Matching a parcoursup fiche against
       an onisep fiche with empty etab gives a spurious 100% match on the
       formation name alone, losing the geographic discrimination.
    """
    # Pre-filter onisep candidates by etab populated (if required)
    if require_onisep_etab:
        candidates = [(f, _signature(f)) for f in onisep if (f.get("etablissement") or "").strip()]
    else:
        candidates = [(f, _signature(f)) for f in onisep]

    merged = []
    for ps in parcoursup:
        ps_sig = _signature(ps)
        # Skip too-short signatures (high false-positive risk)
        if len(ps_sig.split()) < min_tokens:
            continue
        best_score = 0
        best_onisep = None
        for onisep_fiche, on_sig in candidates:
            score = fuzz.token_set_ratio(ps_sig, on_sig)
            if score > best_score:
                best_score = score
                best_onisep = onisep_fiche
        if best_onisep and best_score >= threshold:
            merged_fiche = {**best_onisep, **ps}
            merged_fiche["match_method"] = f"fuzzy_{best_score}"
            merged.append(merged_fiche)
    return merged


def attach_labels(
    fiches: list[dict],
    secnumedu: list[dict],
    manual_table: list[dict] | None = None,
) -> list[dict]:
    """Attach SecNumEdu (and other) labels from the reference list to merged fiches.

    Uses a three-stage matcher:
    1. Full-signature fuzzy match (name + etab + ville) at threshold 85 —
       catches cases where formation names align between sources.
    2. Establishment-only fuzzy match at threshold 85 — fallback for cases
       where formation names differ but establishment names overlap
       (e.g., Parcoursup "EFREI Bordeaux" vs SecNumEdu "EFREI").
    3. Manual table lookup — looks up each fiche's normalized establishment
       against a cross-reference table using substring containment.
       An entry with empty labels is "explicitly unlabeled" — useful for
       benchmark contrast (private schools without SecNumEdu/CTI labels).

    The Stage 2 fallback only fires on fiches in domains where the label list
    is relevant (currently: "cyber" for SecNumEdu). This prevents spurious
    attachments on unrelated domains.
    """
    sec_sigs = [(s, _signature(s)) for s in secnumedu]
    sec_etabs = [(s, normalize_name(s.get("etablissement", ""))) for s in secnumedu]

    for f in fiches:
        f_sig = _signature(f)
        existing_labels = list(f.get("labels", []))
        matched = False

        # Stage 1: full signature match
        for sec, sec_sig in sec_sigs:
            if fuzz.token_set_ratio(f_sig, sec_sig) >= 85:
                for label in sec.get("labels", []):
                    if label not in existing_labels:
                        existing_labels.append(label)
                matched = True
                break

        # Stage 2: establishment-only fallback (cyber domain only for SecNumEdu)
        if not matched and f.get("domaine") == "cyber":
            f_etab = normalize_name(f.get("etablissement", ""))
            if f_etab:
                for sec, sec_etab in sec_etabs:
                    if sec_etab and fuzz.token_set_ratio(f_etab, sec_etab) >= 85:
                        for label in sec.get("labels", []):
                            if label not in existing_labels:
                                existing_labels.append(label)
                        break

        # Stage 3: manual table (AUTHORITATIVE — overrides earlier stages).
        # When a fiche's establishment matches a manual entry, the manual
        # labels REPLACE any labels attached by Stages 1/2. This makes the
        # manual table a correction layer: entries with empty labels act as
        # a blocklist (e.g., EPITA/Guardia/Epitech are explicitly unlabeled
        # for benchmark contrast even if fuzzy matching would have labeled them).
        #
        # DOMAIN FILTER (Vague santé fix) : the current manual table is all
        # cyber-focused (SecNumEdu, CTI, CGE, Grade Master). Applying its
        # labels to any fiche of a listed establishment wrongly labelled
        # PASS/Licence santé fiches at Université de Limoges etc. as
        # SecNumEdu. We now only apply the manual table to fiches in the
        # tech domains (cyber, data_ia) where those labels are relevant.
        if manual_table is not None and f.get("domaine") in ("cyber", "data_ia"):
            f_etab_norm = normalize_name(f.get("etablissement", ""))
            if f_etab_norm:
                for entry in manual_table:
                    ref = entry.get("etab_normalized", "")
                    if not ref:
                        continue
                    if ref in f_etab_norm or f_etab_norm in ref:
                        existing_labels = list(entry.get("labels", []))
                        break

        f["labels"] = existing_labels
    return fiches


def merge_all(
    parcoursup: list[dict],
    onisep: list[dict],
    secnumedu: list[dict],
    manual_labels: list[dict] | None = None,
    fuzzy_threshold: int = 85,
) -> list[dict]:
    # Step 1: RNCP matching
    rncp_matched = merge_by_rncp(parcoursup, onisep)
    matched_rncps = {f.get("rncp") for f in rncp_matched if f.get("rncp")}

    # Step 2: Fuzzy matching on parcoursup orphans against onisep orphans
    ps_orphans = [p for p in parcoursup
                  if not p.get("rncp") or p.get("rncp") not in matched_rncps]
    onisep_orphans = [o for o in onisep
                      if not o.get("rncp") or o.get("rncp") not in matched_rncps]
    fuzzy_matched = fuzzy_match_fiches(ps_orphans, onisep_orphans, fuzzy_threshold)

    # Step 3: Parcoursup-only (kept even without ONISEP enrichment —
    # taux d'accès is the most critical field and we don't want to lose it)
    fuzzy_matched_sigs = {_signature(f) for f in fuzzy_matched}
    ps_only = []
    for p in ps_orphans:
        if _signature(p) not in fuzzy_matched_sigs:
            p_copy = dict(p)
            p_copy["match_method"] = "parcoursup_only"
            ps_only.append(p_copy)

    # Step 3b: ONISEP-only — ONISEP fiches not matched by either RNCP or fuzzy
    # are kept as standalone entries (they provide higher-ed coverage that
    # Parcoursup lacks: ingénieurs post-prépa, mastères spécialisés, etc.)
    matched_onisep_ids = set()
    for f in rncp_matched + fuzzy_matched:
        if f.get("source") == "onisep" or f.get("url_onisep"):
            # The merged fiche already has ONISEP fields; mark as matched
            # by using a signature on its onisep provenance
            matched_onisep_ids.add((f.get("rncp"), f.get("url_onisep")))
    onisep_only = []
    for o in onisep:
        # If this onisep fiche wasn't merged with a parcoursup fiche, keep it standalone
        key = (o.get("rncp"), o.get("url_onisep"))
        if key not in matched_onisep_ids:
            o_copy = dict(o)
            o_copy["match_method"] = "onisep_only"
            onisep_only.append(o_copy)

    all_merged = rncp_matched + fuzzy_matched + ps_only + onisep_only

    # Step 4: Attach SecNumEdu labels (now with optional manual table)
    all_merged = attach_labels(all_merged, secnumedu, manual_table=manual_labels)

    # Step 5: Infer statut from establishment name when missing
    for f in all_merged:
        if not f.get("statut"):
            est = normalize_name(f.get("etablissement", ""))
            if any(pub in est for pub in ["universite", "ecole normale", "institut national",
                                           "ecole nationale", "insa", "ens", "cnam",
                                           "imt", "telecom paris", "polytechnique"]):
                f["statut"] = "Public"
            else:
                f["statut"] = "Inconnu"
        f.setdefault("labels", [])
        if not f.get("niveau"):
            f["niveau"] = infer_niveau(f.get("nom", ""))

    return all_merged


# === Fix order 2026-06-11 — travail social ≠ santé (mapping ROME J11) ===


def _strip_accents_lower(s) -> str:
    s = str(s or "").lower()
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


# Signatures professionnelles du TRAVAIL SOCIAL (NSF 332). Multi-mots /
# acronymes spécifiques : on évite volontairement le mot "social" seul, qui
# matcherait des disciplines ("sciences sociales", "psychologie sociale") et
# non des métiers du social.
_SOCIAL_WORK_PATTERNS = [
    r"accompagnant\w*\s+educati\w*\s+et\s+social",
    r"\baes\b",
    r"aide\s+medico-?psychologique", r"\bamp\b",
    r"auxiliaire\s+de\s+vie\s+sociale", r"\bavs\b",
    r"assistant\w*\s+(?:de\s+)?service\s+social", r"assistant\w*\s+social\w*",
    r"economie\s+sociale\s+et\s+familiale", r"\bcesf\b", r"\bdecesf\b",
    r"educateur\w*\s+specialise", r"educateur\w*\s+de\s+jeunes\s+enfants",
    r"educateur\w*\s+technique\s+specialise",
    r"moniteur\W*educateur",
    r"\beje\b", r"\bdees\b", r"\bdeme\b",
    r"intervention\s+sociale", r"\btisf\b",
    r"mediateur\w*\s+social\w*", r"mediation\s+sociale",
    r"travail\w*\s+social\w*", r"intervenant\w*\s+social\w*",
    r"conseiller\w*\s+en\s+economie\s+sociale",
    r"delegue\w*\s+aux?\s+prestations?\s+familiales?",
    r"mandataire\s+judiciaire\s+a\s+la\s+protection",
    # Faux négatifs récupérés (travail social réel, validés zéro faux positif
    # sur le corpus sante) : diplômes BUT Carrières Sociales, secteur
    # médico-social, accompagnement/habitat social, établissements sociaux.
    r"carrieres?\s+sociales?",
    r"accompagnement\s+social\w*",
    r"medico-?social",
    r"habitat\s+social",
    r"etablissements?\s+(?:et\s+services?\s+)?sociaux",
    # Petite enfance + insertion/orientation (résidu audit #131, même iceberg) :
    # AEPE, éducateur de jeunes enfants, Montessori petite enfance, relais petite
    # enfance, conseiller en transition professionnelle. Le garde-fou paramédical
    # exclut "auxiliaire de puériculture" (puéricult -> reste santé).
    r"petite\s+enfance",
    r"transition\s+professionnelle",
]
_SOCIAL_WORK_RE = re.compile("|".join(_SOCIAL_WORK_PATTERNS))

# Garde-fou : si le NOM désigne une profession médicale/paramédicale explicite,
# la fiche reste santé même si un terme social apparaît (ex « coordinateur
# infirmier en structure médico-sociale » = infirmier, débouchés santé légitimes).
_MEDICAL_PROFESSION_RE = re.compile(
    r"infirmi|aide-?soignant|kinesi|masseur|sage-?femme|maieut|m[ée]decin|"
    r"pharmaci|dentaire|odontolog|podolog|orthopt|orthophon|audiopro|opticien|"
    r"psychomot|dietet|ergothera|ambulanci|pueri[c]ult|manipulateur"
)

# Domaines "santé" depuis lesquels une formation sociale doit être requalifiée
# (toute fiche domaine=sante reçoit les 10 débouchés médicaux J11xx).
_HEALTH_DOMAINS_TO_RECHECK = {"sante"}


def is_social_work_formation(nom) -> bool:
    """True si le NOM désigne une formation au TRAVAIL SOCIAL (NSF 332).

    Prédicat déterministe (multi-mots / acronymes) calibré pour éviter les faux
    positifs sur les disciplines académiques ('sciences sociales') et le
    paramédical. Une formation sociale ne doit JAMAIS hériter de débouchés
    médicaux J11xx. Fix order 2026-06-11 — cf detresse-prec-007 (CESF).
    """
    norm = _strip_accents_lower(nom)
    if _MEDICAL_PROFESSION_RE.search(norm):
        return False  # profession médicale/paramédicale -> reste santé
    return bool(_SOCIAL_WORK_RE.search(norm))


def reclassify_social_health(fiches: list[dict]) -> list[dict]:
    """Requalifie les formations TRAVAIL SOCIAL mal classées domaine=sante vers
    domaine='social'. Chokepoint déterministe AVANT attach_debouches.

    Root cause order 2026-06-11 : NSF 332 ('Travail social'), parcoursup
    'd.e secteur social' et labonnealternance faisaient tomber CESF / AES /
    éducateurs spécialisés en domaine=sante -> injection des 10 débouchés
    médicaux J11xx (cf detresse-prec-007 : CESF affichant médecin/sage-femme).
    Cette passe capte toutes les sources d'un coup, par le nom. Idempotente.
    """
    for f in fiches:
        if not isinstance(f, dict):
            continue
        if f.get("domaine") in _HEALTH_DOMAINS_TO_RECHECK and is_social_work_formation(
            f.get("nom")
        ):
            f["domaine"] = "social"
    return fiches


# === Vague A — post-merge enrichment: debouches + provenance + fraîcheur ===


def attach_debouches(fiches: list[dict]) -> list[dict]:
    """Attach ROME 4.0 debouches to each fiche based on its `domaine`.

    Uses the canonical `get_debouches_for_domain()` mapping (src/collect/rome.py)
    which is verified against ROME 4.0 open data. Fiches without a known
    domaine keep their existing `debouches` (if any) or get an empty list.

    Before Vague A this step was done out-of-pipeline (one-off script).
    Now integrated so `run_merge.py` produces a fully-populated JSON from
    scratch, reproducibly.
    """
    for f in fiches:
        domaine = f.get("domaine")
        if not domaine:
            f.setdefault("debouches", [])
            continue
        # Don't clobber existing debouches if already populated (tests/fixtures)
        if f.get("debouches"):
            continue
        try:
            f["debouches"] = get_debouches_for_domain(domaine)
        except KeyError:
            # Unknown domain (e.g., future domain not yet in _DOMAIN_CODES) — keep empty
            f["debouches"] = []
    return fiches


def attach_metadata(
    fiches: list[dict],
    collection_date: str | None = None,
) -> list[dict]:
    """Attach Vague A provenance + collected_at metadata per fiche.

    - `provenance`: map of enriched-field → source name (for LLM citations
      and future conflict resolution when multiple sources disagree).
    - `collected_at`: map of source → ISO date (makes freshness first-class).
    - `merge_confidence`: confidence per source merge (1.0 for RNCP match,
      fuzzy score for fuzzy, null for unmatched).

    Called post-merge, post-attach_labels, post-attach_debouches.
    """
    today = collection_date or date.today().isoformat()

    for f in fiches:
        mm = f.get("match_method", "")
        # Infer which sources contributed this fiche
        sources_present = set()
        if f.get("cod_aff_form") or f.get("taux_acces_parcoursup_2025") is not None:
            sources_present.add("parcoursup")
        if f.get("url_onisep") or mm in ("rncp", "onisep_only") or mm.startswith("fuzzy"):
            sources_present.add("onisep")
        if f.get("debouches"):
            sources_present.add("rome")

        # Provenance per enriched field
        provenance = {}
        if f.get("admission") or f.get("taux_acces_parcoursup_2025") is not None:
            provenance["admission"] = "parcoursup_2025"
        if f.get("profil_admis"):
            provenance["profil_admis"] = "parcoursup_2025"
        if f.get("debouches"):
            provenance["debouches"] = "rome_4_0"
        if f.get("type_diplome") or f.get("duree"):
            provenance["type_diplome"] = "onisep"
        if f.get("labels"):
            # labels come from SecNumEdu scrape + manual_labels.json overlay
            provenance["labels"] = "secnumedu+manual"

        f["provenance"] = provenance

        # collected_at per source
        collected = {}
        if "parcoursup" in sources_present:
            collected["parcoursup"] = today
        if "onisep" in sources_present:
            collected["onisep"] = today
        if "rome" in sources_present:
            collected["rome"] = today
        f["collected_at"] = collected

        # merge_confidence per source
        confidence = {}
        if "parcoursup" in sources_present:
            confidence["parcoursup"] = 1.0
        if "onisep" in sources_present:
            if mm == "rncp":
                confidence["onisep"] = 1.0
            elif mm.startswith("fuzzy_"):
                try:
                    score = float(mm.split("_", 1)[1]) / 100.0
                    confidence["onisep"] = round(score, 2)
                except (ValueError, IndexError):
                    confidence["onisep"] = 0.85
            elif mm == "onisep_only":
                confidence["onisep"] = 1.0  # ONISEP-native, no merge loss
            elif mm == "parcoursup_only":
                confidence["onisep"] = None  # not matched
        if f.get("labels"):
            confidence["labels"] = 1.0
        f["merge_confidence"] = confidence

    return fiches


# === Extension scope élargi 17-25 ans (ADR-039) : MonMaster + RNCP + Céreq ===


def monmaster_to_fiche(mm_record: dict) -> dict:
    """Convertit un record MonMaster normalisé en fiche compatible pipeline.

    MonMaster normalisé (via src/collect/monmaster.py) a déjà les bons champs
    `nom`, `etablissement`, `ville`, `niveau`. On ajoute juste `domaine`
    (inféré depuis discipline) et `match_method`.
    """
    fiche = dict(mm_record)
    # Assure la présence des champs pipeline
    fiche.setdefault("match_method", "monmaster_only")
    fiche.setdefault("labels", [])
    fiche.setdefault("statut", "Public")  # masters universitaires = public par défaut
    # Domaine inféré depuis discipline MESR (plus fin que "master" générique)
    if not fiche.get("domaine"):
        disc = (fiche.get("discipline") or "").lower()
        if "informatique" in disc or "science" in disc and "donnée" in disc:
            fiche["domaine"] = "data_ia"
        elif "sant" in disc or "biologie" in disc or "médecine" in disc:
            fiche["domaine"] = "sante"
        elif "droit" in disc or "politique" in disc:
            fiche["domaine"] = "droit"
        elif "économ" in disc or "gestion" in disc:
            fiche["domaine"] = "eco_gestion"
        elif "humaine" in disc or "social" in disc:
            fiche["domaine"] = "sciences_humaines"
        elif "langue" in disc:
            fiche["domaine"] = "langues"
        elif "lettre" in disc or "art" in disc:
            fiche["domaine"] = "lettres_arts"
        elif "sport" in disc or "staps" in disc:
            fiche["domaine"] = "sport"
        elif "fondament" in disc or "ingénier" in disc or "technolog" in disc:
            fiche["domaine"] = "sciences_fondamentales"
        else:
            fiche["domaine"] = "autre"
    return fiche


def rncp_to_fiche(certif: dict) -> dict:
    """Convertit une certification RNCP normalisée en fiche pipeline.

    RNCP (via src/collect/rncp.py) a `intitule` / `numero_fiche` / `niveau`
    mais pas `nom` / `etablissement` / `ville`. On mappe :
    - `nom` = `intitule`
    - `etablissement` = premier certificateur (ou vide)
    - `ville` = "" (certification nationale, pas de ville)
    - `domaine` = inféré depuis codes_nsf + codes_rome
    """
    certificateurs = certif.get("certificateurs") or []
    etab = ""
    if certificateurs:
        etab = (certificateurs[0].get("nom") or "").strip()

    domaine = _infer_domaine_from_nsf(certif.get("codes_nsf") or []) or \
              _infer_domaine_from_rome(certif.get("codes_rome") or []) or \
              "autre"

    fiche = {
        "source": "rncp",
        "phase": certif.get("phase", "initial"),
        "nom": certif.get("intitule", ""),
        "etablissement": etab,
        "ville": "",
        "rncp": certif.get("numero_fiche"),
        "niveau": certif.get("niveau"),
        "niveau_eu": certif.get("niveau_eu"),
        "type_diplome": certif.get("abrege_intitule"),
        "abrege_type": certif.get("abrege_type"),
        # Signal autoritaire pour derive_rncp_professional_title (Stage 5.95, ordre
        # 1305) : "Enregistrement sur demande" = certif pro (titre/CQP) sans diplôme
        # formel. Préservé ici (était droppé) pour que la dérivation soit reproductible.
        "type_enregistrement": certif.get("type_enregistrement"),
        "domaine": domaine,
        "statut": "Certificat RNCP",  # catégorie distincte des formations classiques
        "voies_acces": certif.get("voies_acces") or [],
        "codes_rome": certif.get("codes_rome") or [],
        "codes_nsf": certif.get("codes_nsf") or [],
        "certificateurs": certificateurs,
        "actif": certif.get("actif", True),
        "date_effet": certif.get("date_effet"),
        "date_fin_enregistrement": certif.get("date_fin_enregistrement"),
        "match_method": "rncp_only",
        "labels": [],
    }
    return fiche


def inserjeunes_cfa_to_fiche(cfa_record: dict) -> dict:
    """Convertit un record Inserjeunes CFA en fiche pipeline.

    CFA Inserjeunes = apprentissage agrégé par centre (pas par formation
    fine). Plusieurs entrées par CFA si plusieurs années de cumul.

    Mappings clés :
    - `phase` = "reorientation" (apprentissage = voie de réorientation
      ou initial selon perspective, mais ADR-039 classe apprentissage
      dans réorientation pour équilibrage phases)
    - `niveau` : None côté source (CFA agrégé) → laissé à None, le
      fallback phase par défaut dans `merge_all_extended` n'écrase pas
      puisque phase est déjà posée.
    - `nom` : libellé CFA (pas une formation spécifique — c'est le centre)
    - `domaine` : "apprentissage" (catégorie distincte pour ne pas
      polluer les autres filtres)
    - `insertion_pro` mappé depuis `taux_emploi` horizons + autres
      métriques apprentissage-spécifiques (taux_contrats_interrompus,
      valeur_ajoutee_emploi_6_mois — métriques DEPP uniques)
    """
    taux_emploi = cfa_record.get("taux_emploi") or {}
    return {
        "source": "inserjeunes_cfa",
        "phase": "reorientation",
        "nom": cfa_record.get("etablissement") or "CFA (libellé manquant)",
        "etablissement": cfa_record.get("etablissement"),
        "ville": "",  # Pas de ville au niveau CFA agrégé
        "region": cfa_record.get("region"),
        "uai": cfa_record.get("uai"),
        "annee": cfa_record.get("annee"),
        "niveau": None,  # CFA agrégé, pas de niveau unique
        "domaine": "apprentissage",
        "statut": "CFA Apprentissage",
        "type_diplome": "Apprentissage (agrégé CFA)",
        "insertion_pro": {
            "source": "inserjeunes_cfa",
            "annee": cfa_record.get("annee"),
            "taux_emploi_6m": taux_emploi.get("6m"),
            "taux_emploi_12m": taux_emploi.get("12m"),
            "taux_emploi_18m": taux_emploi.get("18m"),
            "taux_emploi_24m": taux_emploi.get("24m"),
            "taux_emploi_6m_attendu": cfa_record.get("taux_emploi_6_mois_attendu"),
            "valeur_ajoutee_emploi_6m": cfa_record.get("valeur_ajoutee_emploi_6_mois"),
            "taux_contrats_interrompus": cfa_record.get("taux_contrats_interrompus"),
            "part_poursuite_etudes": cfa_record.get("part_poursuite_etudes"),
            "part_emploi_6m": cfa_record.get("part_emploi_6_mois_post"),
            "part_autres_situations": cfa_record.get("part_autres_situations"),
        },
        "match_method": "inserjeunes_cfa_only",
        "labels": [],
    }


def _cereq_stats_flat(entry: dict) -> dict:
    """Normalise une entrée Céreq vers les stats clés exposées sur fiches.

    Supporte 2 schémas :
    - CSV legacy : champs plats `taux_emploi_3ans`, `taux_emploi_6ans`,
      `taux_cdi`, `salaire_median_embauche` à la racine
    - XLSX OpenData (2026-04-24+) : champs sous `horizon_3ans` +
      `horizon_6ans` avec `taux_emploi`, `taux_edi` (CDI),
      `revenu_travail` (€ mensuel)

    Retourne toujours un dict au schéma unifié pour la fiche.
    """
    h3 = entry.get("horizon_3ans") or {}
    h6 = entry.get("horizon_6ans") or {}
    return {
        "taux_emploi_3ans": entry.get("taux_emploi_3ans")
            or (h3.get("taux_emploi") / 100.0 if isinstance(h3.get("taux_emploi"), (int, float)) else None),
        "taux_emploi_6ans": entry.get("taux_emploi_6ans")
            or (h6.get("taux_emploi") / 100.0 if isinstance(h6.get("taux_emploi"), (int, float)) else None),
        "taux_cdi": entry.get("taux_cdi")
            or (h3.get("taux_edi") / 100.0 if isinstance(h3.get("taux_edi"), (int, float)) else None),
        "salaire_median_embauche": entry.get("salaire_median_embauche")
            or h3.get("revenu_travail"),
        "source": "cereq",
        "cohorte": entry.get("cohorte"),
    }


def attach_cereq_insertion(
    fiches: list[dict], cereq_entries: list[dict] | None
) -> list[dict]:
    """Enrichit chaque fiche avec les stats d'insertion Céreq correspondant
    à son `niveau` + `domaine`.

    Céreq agrège par niveau × domaine, pas par formation individuelle — donc
    l'enrichissement est indicatif (plusieurs fiches partagent les mêmes
    stats). Utile pour réponses RAG "x% d'insertion à 3 ans pour les masters
    en informatique" sans inventer.

    Stratégie d'indexation :
    1. D'abord match exact `(niveau, domaine)` si domaine Céreq renseigné
    2. Fallback match `(niveau, None)` si la fiche a un niveau mais pas de
       domaine Céreq correspondant (stats "Ensemble" du niveau)

    Sans aucune entrée Céreq parsée → no-op.
    """
    if not cereq_entries:
        return fiches
    # Index Céreq : 2 niveaux de granularité
    index_niveau_domaine: dict[tuple, dict] = {}
    index_niveau_seul: dict[str, dict] = {}
    for entry in cereq_entries:
        niveau = entry.get("niveau")
        if not niveau:
            continue
        domaine = (entry.get("domaine") or "").lower() or None
        cohorte = entry.get("cohorte") or ""
        if domaine:
            key = (niveau, domaine)
            if key not in index_niveau_domaine or index_niveau_domaine[key].get("cohorte", "") < cohorte:
                index_niveau_domaine[key] = entry
        else:
            if niveau not in index_niveau_seul or index_niveau_seul[niveau].get("cohorte", "") < cohorte:
                index_niveau_seul[niveau] = entry

    for f in fiches:
        niveau = f.get("niveau")
        if not niveau:
            continue
        domaine = (f.get("domaine") or "").lower()
        stats = index_niveau_domaine.get((niveau, domaine)) or index_niveau_seul.get(niveau)
        if stats:
            f["insertion_pro"] = _cereq_stats_flat(stats)
    return fiches


def merge_all_extended(
    parcoursup: list[dict],
    onisep: list[dict],
    secnumedu: list[dict],
    monmaster: list[dict] | None = None,
    rncp: list[dict] | None = None,
    cereq: list[dict] | None = None,
    parcoursup_extended: list[dict] | None = None,
    onisep_extended: list[dict] | None = None,
    lba: list[dict] | None = None,
    inserjeunes_cfa: list[dict] | None = None,
    manual_labels: list[dict] | None = None,
    fuzzy_threshold: int = 85,
) -> list[dict]:
    """Pipeline étendu : intègre l'ensemble des corpus scope élargi en plus
    du pipeline legacy (Parcoursup CSV + ONISEP JSON + SecNumEdu).

    Sources ajoutées au fil du scope élargi ADR-039 :
    - `monmaster` (ex sessions 2024/2025 dédupliquées ADR-044)
    - `rncp` (certifications RNCP avec ROMEs + NSF)
    - `parcoursup_extended` (scrape étendu ~9k fiches, pré-normalisé)
    - `onisep_extended` (ONISEP formations étendues ~4.7k, pré-normalisé)
    - `lba` (La Bonne Alternance ~6.6k, phase réorientation)
    - `cereq` (stats insertion agrégées par niveau × domaine, enrichissement)

    Backward-compat : tous les nouveaux params sont optionnels, par défaut
    None → comportement identique à la version pré-scope-élargi quand non
    fournis. Les sources pré-normalisées (`*_extended`, `lba`, `monmaster`)
    sont appendées telles quelles (les audits les ont validées sans
    doublons internes, cf docs/AUDIT_DATA_QUALITY_2026-04-24.md).

    Respect ADR-039 : chaque fiche porte un `phase` explicite (master /
    initial / reorientation) pour la répartition 33/33/34.
    """
    # Étape 1 : pipeline legacy (fuzzy merger Parcoursup CSV × ONISEP JSON)
    legacy = merge_all(parcoursup, onisep, secnumedu, manual_labels, fuzzy_threshold)

    # Étape 2 : adapteurs pour sources nécessitant une normalisation
    mm_fiches = [monmaster_to_fiche(r) for r in (monmaster or [])]
    rncp_fiches = [rncp_to_fiche(c) for c in (rncp or [])]

    # Étape 3 : sources déjà normalisées (schéma fiche → append direct)
    pe_fiches = list(parcoursup_extended or [])
    oe_fiches = list(onisep_extended or [])
    lba_fiches = list(lba or [])

    # Étape 3b : adapteurs sources nécessitant un mapping fiche
    cfa_fiches = [inserjeunes_cfa_to_fiche(r) for r in (inserjeunes_cfa or [])]

    # Étape 4 : concat global — ordre = priorité retrieval implicite
    all_fiches = (
        legacy + pe_fiches + oe_fiches + mm_fiches + rncp_fiches
        + lba_fiches + cfa_fiches
    )

    # Étape 4b : dedup Parcoursup par cod_aff_form (ADR-050)
    # Les fiches `legacy` (Parcoursup CSV) et `pe_fiches` (parcoursup_extended)
    # se chevauchent silencieusement, produisant 5.4 % de doublons stricts.
    all_fiches = dedup_parcoursup_by_cod_aff_form(all_fiches)

    # Étape 5 : attach_debouches ROME (pour fiches sans debouches — MonMaster
    # et RNCP n'en ont pas nativement, LBA partiel)
    all_fiches = attach_debouches(all_fiches)

    # Étape 6 : attach_metadata pour les nouveaux ajouts sans provenance
    all_fiches = attach_metadata(all_fiches)

    # Étape 7 : enrichissement Céreq par (niveau, domaine) avec fallback
    # (niveau seul) — indicatif, cf `attach_cereq_insertion`
    all_fiches = attach_cereq_insertion(all_fiches, cereq)

    # Étape 8 : assurer phase par défaut si absente (rétrocompat fiches Parcoursup
    # pré-ADR-039 sans phase explicite)
    for f in all_fiches:
        if not f.get("phase"):
            niveau = f.get("niveau") or ""
            f["phase"] = "master" if niveau in ("bac+5", "bac+8") else "initial"

    return all_fiches
