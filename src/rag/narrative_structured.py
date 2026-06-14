"""Parser DÉTERMINISTE prose -> sortie typée `NarrativeResponse` (ordre 1926).

La génération récit reste PROSE-native (contrat factuel v4 strict inchangé,
citations `[source SX]` inline). Ce module DÉRIVE de façon déterministe une
structure typée exploitable par le frontend (cards formations, chips sources,
comparison_table, trajectory_steps, stat callouts), SANS jamais forcer le LLM à
émettre du JSON (ce qui menacerait le groundedness).

## Contrat (front-exploitable, ordre 1926 Option A)

    NarrativeResponse = {
      "format": str,                      # cf narrative_format.VALID_FORMATS
      "overlays": {"anchor_constraint": bool, "reassure": bool},
      "blocks": [Block, ...],             # couche d'ENRICHISSEMENT
      "markdown_full": str,               # CANONIQUE / source de vérité
      "parse_confidence": float,          # 0-1, santé STRUCTURELLE du parse
    }
    Block = {
      "role": str,                        # lead|options|comparison_table|
                                          # passerelles|vigilance|justification|
                                          # closing|prose
      "heading": str | None,
      "markdown": str,                    # le front retombe là-dessus par bloc
      "items": [Piste, ...],              # pistes/formations (cards)
      "table": ComparisonTable | None,
      "sources": [str, ...],              # ex ["S1","S2"] (chips)
    }
    Piste = {"titre": str, "url": str|None, "pourquoi": str,
             "sources": [str], "markdown": str}
    ComparisonTable = {"options": [str], "criteria":
             [{"label": str, "values": {opt: str}, "sources": [str]}]}

## Règle d'or : `markdown_full` est CANONIQUE, les blocs sont un BONUS

`markdown_full` contient toujours la réponse intégrale (zéro perte). Sur parse
low-confidence, le front DOIT retomber sur `markdown_full` (jamais un demi-
tableau). Le parser est TOTAL : il ne lève JAMAIS — toute exception renvoie un
bloc `prose` unique + `parse_confidence=0.0`, le texte intégral préservé.
"""
from __future__ import annotations

import re

from src.rag.narrative_format import (
    FormatDecision,
    CONSEIL, EXPLORATOIRE, COMPARAISON, TRAJECTOIRE, VALIDATION, SHORTLIST,
)


# Ligne = titre de section en gras (« **1. Ta situation** », « **Le palmarès** »),
# avec éventuel parenthétique de fin. Une puce « - **[x](y)** ... » ne matche pas
# (elle ne commence pas par « ** »).
_HEADING_RE = re.compile(r"^\*\*\s*(?P<num>\d+\.\s*)?(?P<title>.+?)\*\*\s*(?P<paren>\(.*\))?\s*$")

# Citation source : « [source S2] » ou « [S2] ».
_SOURCE_RE = re.compile(r"\[\s*(?:source\s*)?S?(\d+)\s*\]", re.IGNORECASE)

# Lien Markdown : [titre](url).
_MDLINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Puce de piste : « - ... » ou « 1. ... » / « 2) ... ».
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(?P<body>.+)$")

# Ligne de séparation d'un tableau markdown : « |---|---| ».
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}.*$")

# Détection de TRONCATURE (fix B, ordre 1926) — la réponse a été coupée au cap
# max_tokens en pleine phrase. Déterministe, uniforme sync+stream (l'heuristique
# fin-de-texte est plus fiable que `finish_reason`, absent/instable en streaming).
# Cas observés : R01 finissait sur « [source S », T3 (démo) sur un lien markdown
# inachevé « [Data scientist](https://...%20automatis ». Un parse_confidence=1.0
# ne suffit PAS : les titres étaient tous présents AVANT la coupe.
_TRUNCATION_RE = re.compile(r"(\[[^\]]*$)|(\]\([^)]*$)")  # crochet / lien ouvert en fin
_COMPLETE_LAST_CHARS = set(".!?)»”\"'…")


def _looks_truncated(markdown: str) -> bool:
    """True si la réponse semble coupée en pleine phrase (cap max_tokens atteint).

    Heuristique déterministe : lien markdown / citation source inachevé en fin,
    OU dernier caractère significatif = alphanumérique / ponctuation de milieu de
    phrase (pas une fin de phrase propre). On NE sert JAMAIS une coupe silencieuse
    (surtout en démo) -> ce flag remonte dans NarrativeResponse + pénalise la
    confiance, le serving/front peut décider de masquer ou re-générer.
    """
    s = (markdown or "").rstrip().rstrip("*_`").rstrip()
    if not s:
        return False
    if _TRUNCATION_RE.search(s):
        return True
    last = s[-1]
    if last in _COMPLETE_LAST_CHARS:
        return False
    # finit sur un mot / une ponctuation de milieu de phrase -> coupé
    return last.isalnum() or last in ",;:-—–/«("


def _extract_sources(text: str) -> list[str]:
    """Sources citées, normalisées « S<n> », dédupliquées en ordre d'apparition."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _SOURCE_RE.finditer(text or ""):
        s = "S" + m.group(1)
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# --- Rôles de section par mots-clés du titre (normalisés sans accents) ---

def _norm_head(title: str) -> str:
    import unicodedata
    t = "".join(
        c for c in unicodedata.normalize("NFKD", (title or "").lower())
        if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", t).strip()


_ROLE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # ordre = priorité de match
    ("comparison_table", ("face a face", "comparatif", "face-a-face")),
    ("passerelles", ("passerelle",)),
    ("vigilance", ("vigilance", "point de vigilance", "points de vigilance", "a surveiller")),
    ("justification", ("pourquoi",)),
    ("options", ("pistes", "familles", "le chemin", "chemin concret", "alternatives",
                 "palmares", "options")),
    ("closing", ("prochaine etape", "premier pas", "pour t'aider", "pour t aider",
                 "ma reco", "ce que je ferais", "et apres", "prochaine")),
    ("lead", ("ta situation", "ce que je retiens", "ta question en clair",
              "d'ou tu pars", "d ou tu pars", "reponse directe", "situation")),
)


def _role_for_heading(title: str) -> str:
    h = _norm_head(title)
    for role, kws in _ROLE_KEYWORDS:
        if any(kw in h for kw in kws):
            return role
    return "prose"


# Sections-cœur attendues par format (hors vigilance conditionnelle) -> confiance.
_EXPECTED_CORE: dict[str, frozenset[str]] = {
    CONSEIL: frozenset({"lead", "options", "closing"}),
    EXPLORATOIRE: frozenset({"lead", "options", "closing"}),
    COMPARAISON: frozenset({"lead", "comparison_table", "closing"}),
    TRAJECTOIRE: frozenset({"lead", "passerelles", "options", "closing"}),
    VALIDATION: frozenset({"lead", "justification", "options"}),
    SHORTLIST: frozenset({"options"}),
}


def _split_sections(markdown: str) -> list[tuple[str | None, str]]:
    """Découpe en (titre|None, corps) sur les lignes-titres en gras.

    Le préambule éventuel avant le 1er titre est rendu avec titre=None.
    """
    lines = markdown.splitlines()
    sections: list[tuple[str | None, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []
    started = False
    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if m:
            if started or current_body:
                sections.append((current_title, current_body))
            num = m.group("num") or ""
            current_title = (num + m.group("title")).strip()
            current_body = []
            started = True
        else:
            current_body.append(line)
    if started or current_body:
        sections.append((current_title, current_body))
    return [(t, "\n".join(b).strip()) for t, b in sections]


def _parse_pistes(body: str) -> list[dict]:
    """Extrait les pistes (puces / liste numérotée) d'un corps de section."""
    pistes: list[dict] = []
    for raw in body.splitlines():
        bm = _BULLET_RE.match(raw)
        if not bm:
            continue
        line = bm.group("body").strip()
        link = _MDLINK_RE.search(line)
        if link:
            titre, url = link.group(1).strip(), link.group(2).strip()
        else:
            # « **Titre** ... » sans lien
            bold = re.search(r"\*\*(.+?)\*\*", line)
            titre = bold.group(1).strip() if bold else line[:80].strip()
            url = None
        # « pourquoi » = ce qui suit le titre/lien (tiret, deux-points...)
        pourquoi = line
        if link:
            pourquoi = line[link.end():]
        elif "**" in line:
            pourquoi = line.split("**", 2)[-1]
        pourquoi = pourquoi.lstrip(" :-—–").strip()
        # nettoie les marqueurs de source du « pourquoi » lisible (gardés à part)
        pourquoi = _SOURCE_RE.sub("", pourquoi).strip().rstrip(".").strip()
        pistes.append({
            "titre": _strip_md(titre),
            "url": url,
            "pourquoi": pourquoi,
            "sources": _extract_sources(line),
            "markdown": raw.strip(),
        })
    return pistes


def _strip_md(s: str) -> str:
    return re.sub(r"\*\*?", "", s or "").strip()


def _parse_comparison_table(body: str) -> dict | None:
    """Parse le 1er tableau markdown trouvé en {options, criteria}."""
    rows: list[list[str]] = []
    sep_seen = False
    for raw in body.splitlines():
        if "|" not in raw:
            if rows:  # tableau terminé
                break
            continue
        if _TABLE_SEP_RE.match(raw.replace("|", "|")) and set(raw.strip()) <= set("|-: "):
            sep_seen = True
            continue
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        rows.append(cells)
    if not rows or len(rows) < 2:
        return None
    header = rows[0]
    if len(header) < 3:
        return None
    options = [_strip_md(h) for h in header[1:]]
    criteria: list[dict] = []
    for r in rows[1:]:
        if len(r) < 2 or all(not c for c in r):
            continue
        label = _strip_md(r[0])
        if not label or label.lower() in ("critere", "critère"):
            continue
        values: dict[str, str] = {}
        srcs: list[str] = []
        for i, opt in enumerate(options):
            cell = r[i + 1] if (i + 1) < len(r) else ""
            values[opt] = cell.strip()
            srcs += _extract_sources(cell)
        criteria.append({"label": label, "values": values, "sources": _dedup(srcs)})
    if not criteria:
        return None
    return {"options": options, "criteria": criteria}


def _dedup(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    return [x for x in xs if not (x in seen or seen.add(x))]


def _empty_response(decision: FormatDecision, markdown: str, reason: str = "") -> dict:
    fmt = decision.format if decision and decision.is_valid() else CONSEIL
    return {
        "format": fmt,
        "overlays": {
            "anchor_constraint": bool(decision.anchor_constraint) if decision else False,
            "reassure": bool(decision.reassure) if decision else False,
        },
        "blocks": [{
            "role": "prose", "heading": None, "markdown": markdown or "",
            "items": [], "table": None, "sources": _extract_sources(markdown or ""),
        }],
        "markdown_full": markdown or "",
        "parse_confidence": 0.0,
        "truncated": _looks_truncated(markdown or ""),
        **({"parse_error": reason} if reason else {}),
    }


def parse_narrative_response(markdown: str, decision: FormatDecision) -> dict:
    """Dérive un `NarrativeResponse` typé depuis la réponse markdown récit.

    TOTAL : ne lève jamais. `markdown_full` toujours intègre. Sur échec, renvoie
    un unique bloc `prose` + `parse_confidence=0.0`.
    """
    try:
        markdown = markdown or ""
        fmt = decision.format if decision and decision.is_valid() else CONSEIL
        sections = _split_sections(markdown)

        # Aucun titre détecté -> blob : un seul bloc prose (le front utilise markdown_full).
        if not any(t for t, _ in sections):
            return _empty_response(decision, markdown, reason="no_headings")

        blocks: list[dict] = []
        found_roles: set[str] = set()
        for title, body in sections:
            if title is None:
                if body.strip():
                    blocks.append(_mk_block("prose", None, body))
                continue
            role = _role_for_heading(title)
            block = _mk_block(role, title, body)

            if role == "options":
                block["items"] = _parse_pistes(body)
            elif role == "comparison_table":
                table = _parse_comparison_table(body)
                if table is not None:
                    block["table"] = table
                else:
                    # tableau attendu mais introuvable -> on déclasse en prose
                    role = "prose"
                    block["role"] = "prose"
            found_roles.add(role)
            blocks.append(block)

        # Confiance = couverture des sections-cœur attendues du format.
        expected = _EXPECTED_CORE.get(fmt, frozenset({"lead"}))
        confidence = len(found_roles & expected) / len(expected) if expected else 0.5
        # Bonus/malus durs sur les formats à structure forte.
        if fmt == COMPARAISON and not any(b.get("table") for b in blocks):
            confidence = min(confidence, 0.5)
        if fmt == SHORTLIST:
            n_items = sum(len(b.get("items", [])) for b in blocks)
            if n_items < 2:
                confidence = min(confidence, 0.5)
        # Troncature (fix B) : une réponse coupée est incomplète même si tous les
        # titres sont présents avant la coupe -> pénalise la confiance + flag.
        truncated = _looks_truncated(markdown)
        if truncated:
            confidence = min(confidence, 0.5)

        return {
            "format": fmt,
            "overlays": {
                "anchor_constraint": bool(decision.anchor_constraint) if decision else False,
                "reassure": bool(decision.reassure) if decision else False,
            },
            "blocks": blocks,
            "markdown_full": markdown,
            "parse_confidence": round(min(1.0, max(0.0, confidence)), 3),
            "truncated": truncated,
        }
    except Exception as e:  # noqa: BLE001 — parser TOTAL (cf docstring)
        return _empty_response(decision, markdown or "", reason=f"exception:{type(e).__name__}")


def _mk_block(role: str, heading: str | None, body: str) -> dict:
    return {
        "role": role,
        "heading": heading,
        "markdown": body.strip(),
        "items": [],
        "table": None,
        "sources": _extract_sources(body),
    }
