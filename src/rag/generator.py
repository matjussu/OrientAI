import re
from typing import AsyncGenerator

from mistralai.client import Mistral
from src.prompt.system import SYSTEM_PROMPT, build_user_prompt
from src.rag.fact_card import format_sources_for_llm, SOURCE_LABEL_MAP
from src.rag.intent import classify_intent, intent_to_format_guidance
from src.rag.user_level import classify_user_level, level_to_guidance


# Mode récit (1d, ordre #137) — paramètres de génération sectionnée.
# Cap output relevé (vs 800 en v4 strict) pour laisser respirer les 4 sections ;
# le cap 250 mots R6 est remplacé par la structure (cf SYSTEM_PROMPT_NARRATIVE).
NARRATIVE_MAX_TOKENS = 1500
# Plus de sources qu'en v4 strict (5) : un récit multi-facettes a besoin de
# matière pour hiérarchiser 2-4 pistes ; le routing récit sert top_k=12.
NARRATIVE_MAX_SOURCES = 8


def selectivite_qualitative(taux: float | None) -> str:
    """Translate a Parcoursup access rate to a qualitative label.

    Thresholds picked to match Parcoursup's own "sélective" terminology.
    """
    if taux is None:
        return "non renseignée"
    if taux < 20.0:
        return "Très sélective"
    if taux < 50.0:
        return "Sélective"
    return "Accessible"


def _fiche_header(i: int, f: dict) -> str:
    nom = (f.get("nom") or "").strip()
    etab = (f.get("etablissement") or "").strip()
    ville = (f.get("ville") or "").strip()
    dept = (f.get("departement") or "").strip()
    niveau = (f.get("niveau") or "").strip()
    statut = (f.get("statut") or "Inconnu").strip()

    loc = ville
    if dept:
        loc = f"{ville} ({dept})" if ville else dept
    head_bits = [f"{nom}"]
    if etab:
        head_bits.append(f"— {etab}")
    if loc:
        head_bits.append(f", {loc}")
    head = " ".join(head_bits)
    meta_bits = [b for b in (niveau, statut) if b]
    if meta_bits:
        head = f"{head} | {' | '.join(meta_bits)}"
    return f"FICHE {i}: {head}"


def _labels_line(f: dict) -> str | None:
    labels = [l for l in (f.get("labels") or []) if l]
    if not labels:
        return None
    return f"  Labels officiels: {', '.join(labels)}"


def _selectivite_line(f: dict) -> str | None:
    # Prefer structured admission block (Vague A), fallback to legacy flat fields
    adm = f.get("admission") or {}
    taux = adm.get("taux_acces") if adm else f.get("taux_acces_parcoursup_2025")
    places = adm.get("places") if adm else f.get("nombre_places")
    volumes = adm.get("volumes") or {}
    voeux_totaux = volumes.get("voeux_totaux")
    internat = adm.get("internat_disponible")

    if taux is None and places is None and voeux_totaux is None:
        return None
    qual = selectivite_qualitative(taux)
    if taux is not None:
        body = f"Parcoursup 2025: {taux:g}% ({qual})"
    else:
        body = f"Parcoursup 2025: non renseignée"
    if places is not None:
        body = f"{body} | Places: {places}"
    if voeux_totaux is not None:
        body = f"{body} | Vœux formulés: {voeux_totaux}"
    if internat is True:
        body = f"{body} | Internat: oui"
    elif internat is False:
        body = f"{body} | Internat: non"
    # Vague C — trend summary: significant direction changes 2023→2025 folded
    # into the selectivity line to preserve the ≤8-lines-per-fiche budget.
    trend_suffix = _trend_suffix(f.get("trends") or {})
    if trend_suffix:
        body = f"{body} | {trend_suffix}"
    return f"  Sélectivité {body}"


_TREND_TAUX_MIN_PP = 5      # Task B : ±5pp minimum pour trend actionable
_TREND_VOEUX_MIN_PCT = 15   # Task B : ±15% minimum de vœux
_TREND_PLACES_MIN = 10      # Task B : ±10 places minimum


def _trend_suffix(trends: dict) -> str | None:
    """Compact trend string for the selectivity line. Emits only
    SIGNIFICANT directions (task B, 2026-04-19) — seuils minimaux
    pour éviter les trends décoratives que les 5 testeurs v2 ont
    jugées bruit ou anxiogènes.

    Seuils : taux ≥5pp, vœux ≥15%, places ≥10. En-deçà → omis.

    Exemple output :
      'Tendance 2023→2025 : taux ↓23pp (plus sélective), vœux ↑38% (attrait +)'
    """
    if not trends:
        return None
    bits: list[str] = []
    # Taux d'accès direction — significance threshold 5pp
    taux = trends.get("taux_acces") or {}
    if taux.get("direction") in ("up", "down"):
        delta = abs(taux.get("delta_pp") or 0)
        if delta >= _TREND_TAUX_MIN_PP:
            arrow = "↓" if taux["direction"] == "down" else "↑"
            label = "plus sélective" if taux["direction"] == "down" else "plus accessible"
            bits.append(f"taux {arrow}{delta:g}pp ({label})")
    # Places direction — significance threshold 10 places
    places = trends.get("places") or {}
    if places.get("direction") in ("up", "down"):
        delta = abs(places.get("delta") or 0)
        if delta >= _TREND_PLACES_MIN:
            arrow = "↑" if places["direction"] == "up" else "↓"
            bits.append(f"places {arrow}{delta}")
    # Vœux direction (popularité) — significance threshold 15%
    voeux = trends.get("voeux") or {}
    if voeux.get("direction") in ("up", "down"):
        start = voeux.get("start_value") or 1
        delta = voeux.get("delta") or 0
        pct = round(delta / start * 100)
        if abs(pct) >= _TREND_VOEUX_MIN_PCT:
            arrow = "↑" if voeux["direction"] == "up" else "↓"
            label = "attrait +" if voeux["direction"] == "up" else "attrait -"
            bits.append(f"vœux {arrow}{pct:+d}% ({label})")
    if not bits:
        return None
    # Infer year range from whichever trend is present
    years_seen = set()
    for t in (taux, places, voeux):
        if t.get("start_year"):
            years_seen.add(t["start_year"])
            years_seen.add(t["end_year"])
    if years_seen:
        yr = f"{min(years_seen)}→{max(years_seen)}"
    else:
        yr = "historique"
    return f"Tendance {yr} : " + ", ".join(bits)


def _debouches_line(f: dict) -> str | None:
    """Tier 0 extended (2026-04-19 task B) : masque les codes ROME
    du texte exposé au LLM. Le libellé suffit pour la génération ;
    le code ROME reste disponible dans le dict fiche pour le retrieval
    interne mais n'apparaît plus en clair dans le contexte LLM
    (même rationale que cod_aff_form / RNCP / FOR.xxx du Tier 0)."""
    debouches = f.get("debouches") or []
    if not debouches:
        return None
    top = debouches[:3]
    parts = [
        d.get("libelle", "").strip()
        for d in top
        if d.get("libelle")
    ]
    parts = [p for p in parts if p]
    if not parts:
        return None
    return f"  Débouchés métiers: {', '.join(parts)}"


def _profil_line(f: dict) -> str | None:
    profil = f.get("profil_admis") or {}
    mentions = profil.get("mentions_pct") or {}
    bac_types = profil.get("bac_type_pct") or {}
    boursiers = profil.get("boursiers_pct")
    femmes = profil.get("femmes_pct")
    neobac = profil.get("neobacheliers_pct")

    bits = []
    # V2 data cleanup (ADR-036) : préfixer "mention" explicitement pour
    # éviter que Mistral Medium confonde "B 42%" avec "série bac B 42%"
    # (cf bug détecté dans Q8 Gate J+6, ground truth humain 2026-04-22).
    m_bits = []
    if mentions.get("tb") is not None:
        m_bits.append(f"mention TB {mentions['tb']:.0f}%")
    if mentions.get("b") is not None:
        m_bits.append(f"mention B {mentions['b']:.0f}%")
    if mentions.get("ab") is not None:
        m_bits.append(f"mention AB {mentions['ab']:.0f}%")
    if m_bits:
        bits.append(", ".join(m_bits))

    # Full bac-type split (Vague A: previously only "general" was exposed)
    bac_bits = []
    for key, label in (("general", "général"), ("techno", "techno"), ("pro", "pro")):
        val = bac_types.get(key)
        if val is not None:
            bac_bits.append(f"{label} {val:.0f}%")
    if bac_bits:
        bits.append(f"Bac {', '.join(bac_bits)}")

    if boursiers is not None:
        bits.append(f"Boursiers {boursiers:.0f}%")
    if femmes is not None:
        bits.append(f"Femmes {femmes:.0f}%")
    if neobac is not None:
        bits.append(f"Néobacheliers {neobac:.0f}%")

    if not bits:
        return None
    return f"  Profil admis: {' | '.join(bits)}"


def _detail_line(f: dict) -> str | None:
    detail = (f.get("detail") or "").strip()
    if not detail:
        return None
    return f"  Détail: {detail[:500]}"


def _insertion_line(f: dict) -> str | None:
    """Vague D + fix 2026-06-13 — insertion pro (taux emploi, salaire médian).

    Lit `insertion_pro` (le champ réel du corpus migré) en priorité, fallback
    `insertion` (clé legacy, rétrocompat). Supporte les 2 namings de salaire
    (`salaire_median_embauche` neuf, `salaire_median_12m_mensuel_net` ancien).
    Attribution de source DATA-DRIVEN (`source`/`salaire_source` via
    SOURCE_LABEL_MAP) au lieu d'un "InserSup DEPP" hardcodé : insertion_pro peut
    venir d'InserSup MESR, Céreq ou CFA selon la fiche. Aucune conversion
    brut<->net ; flag `salaire_net` jamais sorti comme valeur.

    NB : chemin LEGACY v3.2 (format_context). La prod tourne en v4 strict via
    fact_card.format_sources_for_llm — ce fix garde la cohérence du 2e chemin.
    """
    ins = f.get("insertion_pro") or f.get("insertion")
    if not isinstance(ins, dict):
        return None
    bits: list[str] = []
    # InserSup stocke le taux en fraction (0.88) ou en pourcent (88) — si >1.5,
    # déjà en pourcent (évite le double ×100).
    taux = ins.get("taux_emploi_12m")
    if taux is not None:
        bits.append(f"emploi 12m: {(taux if taux > 1.5 else taux * 100):.0f}%")
    else:
        taux18 = ins.get("taux_emploi_18m")
        if taux18 is not None:
            bits.append(f"emploi 18m: {(taux18 if taux18 > 1.5 else taux18 * 100):.0f}%")

    # Salaire mensuel : clé neuve insertion_pro, fallback clé legacy (= net par déf).
    sal = ins.get("salaire_median_embauche")
    if sal is not None:
        nf = ins.get("salaire_net")
        sal_net = nf if isinstance(nf, bool) else None
    else:
        sal = ins.get("salaire_median_12m_mensuel_net")
        sal_net = True if sal is not None else None
    if sal is not None:
        unit = " net" if sal_net is True else (" brut" if sal_net is False else "")
        bits.append(f"salaire médian: {sal}€/mois{unit}")
    elif ins.get("salaire_brut_median_annuel") is not None:
        bits.append(f"salaire brut médian annuel: {ins['salaire_brut_median_annuel']}€/an")

    if not bits:
        return None

    # Attribution source data-driven (mappée si code connu, sinon libellé brut).
    raw_src = ins.get("source") or ins.get("salaire_source")
    src_label = None
    if isinstance(raw_src, str) and raw_src.strip():
        src_label = SOURCE_LABEL_MAP.get(raw_src.lower().strip()) or raw_src.strip()
    cohorte = ins.get("salaire_cohorte") or ins.get("cohorte")
    gran = ins.get("granularite")
    gran_short = "discipline" if gran == "discipline" else ("agrégat établissement" if gran else None)
    meta = [m for m in (src_label,
                        f"cohorte {cohorte}" if cohorte else None,
                        gran_short) if m]
    prefix = f"Insertion ({', '.join(meta)})" if meta else "Insertion"
    return f"  {prefix}: " + " | ".join(bits)


def _source_line(f: dict) -> str | None:
    """Tier 0 fix (2026-04-18 user feedback) : produce an LLM-facing line
    that nudges toward clickable markdown links and away from raw admin
    codes in the output.

    The system prompt tells the LLM explicitly NOT to cite cod_aff_form /
    RNCP / FOR.xxx in cleartext — instead use the URLs from this line as
    markdown links `[fiche officielle Parcoursup](URL)`. The codes remain
    available in the context for the LLM's internal reasoning (knowing
    which fiche is which), but the user-visible output stays clean.
    """
    psup = (f.get("lien_form_psup") or "").strip()
    onisep = (f.get("url_onisep") or "").strip()

    parts: list[str] = []
    if psup:
        parts.append(f"Parcoursup officiel = {psup}")
    if onisep and onisep != psup:
        parts.append(f"ONISEP officiel = {onisep}")

    if not parts:
        return None
    return (f"  Sources à citer en liens markdown cliquables "
            f"(pas d'ID brut dans la réponse) : {' | '.join(parts)}")


def format_context(results: list[dict]) -> str:
    """Format retrieved fiches as a dense signal-first context block.

    Layout (≤ 8 lines per fiche, lines missing data are omitted):
        FICHE i: Nom — Etab, Ville (Dept) | Niveau | Statut
          Labels officiels: ...
          Sélectivité Parcoursup 2025: X% (qualif) | Places: N
          Débouchés métiers: m1 (ROME), m2, m3
          Profil admis: TB %, Bac général %, Boursiers %
          Détail: [500 chars]
          Source: url
    """
    blocks = []
    for i, r in enumerate(results, 1):
        f = r["fiche"]
        lines: list[str] = [_fiche_header(i, f)]
        for line in (
            _labels_line(f),
            _selectivite_line(f),
            _debouches_line(f),
            _profil_line(f),
            _insertion_line(f),
            _detail_line(f),
            _source_line(f),
        ):
            if line is not None:
                lines.append(line)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _build_user_prompt_strict_v4(
    sources_json: str,
    question: str,
    golden_qa_prefix: str | None = None,
) -> str:
    """User prompt v4 strict — JSON tabulaire <sources> + question.

    Pas de prose retrouvée. Le LLM voit explicitement les chiffres et les
    `null`. Le contrat dans SYSTEM_PROMPT_V4_STRICT impose la fidélité.

    Args:
        sources_json: output de `format_sources_for_llm(top_sources)`
        question: la question utilisateur·ice originale
        golden_qa_prefix: si fourni, exemple Q&A Golden injecté EN AMONT
            (référence ton/structure UNIQUEMENT, contrat le rappelle)
    """
    parts = []
    if golden_qa_prefix:
        # Le préfixe Golden contient déjà l'avertissement "IGNORE écoles/chiffres".
        # On le met ici en user side pour que le LLM le voie en contexte de la question.
        parts.append(golden_qa_prefix)
        parts.append("---")
    parts.append("<sources>")
    parts.append(sources_json)
    parts.append("</sources>")
    parts.append("")
    parts.append(f"Question utilisateur·ice : {question}")
    parts.append("")
    parts.append(
        "Réponds en respectant le contrat strict : chiffres uniquement depuis "
        "`<sources>`, citations `[source SX]`, formations identifiées uniquement "
        "celles présentes, refus honnête si information non disponible."
    )
    return "\n".join(parts)


def _build_chat_kwargs(
    retrieved: list[dict],
    question: str,
    *,
    model: str,
    temperature: float,
    inject_user_level: bool,
    system_prompt_override: str | None,
    golden_qa_prefix: str | None,
    history: list[dict] | None,
    hint_block: str,
    use_strict_v4: bool,
    hardlock_block: str,
    narrative_mode: bool = False,
    narrative_decision: "FormatDecision | None" = None,
) -> dict:
    """Build the ``client.chat.complete`` / ``stream_async`` kwargs.

    Extrait depuis ``generate()`` pour permettre une seconde fonction
    ``generate_stream()`` async (SSE Phase 1) sans dupliquer la
    construction des messages. Comportement identique à pré-extraction —
    couvert par ``tests/test_generator.py`` + ``tests/test_system_v4_strict_r7.py``.

    ``narrative_mode`` (1d, ordre #137) : branche « rendu conseiller ». Réutilise
    EXACTEMENT la mécanique factuelle v4 strict (sources JSON tabulaire via
    FactCard, R1-R3 inchangées) mais substitue ``SYSTEM_PROMPT_NARRATIVE``
    (structure en 4 sections) au cap 250 mots R6, et relève ``max_tokens`` à
    ``NARRATIVE_MAX_TOKENS``. Le few-shot récit dédié transite par
    ``golden_qa_prefix`` (même canal que le Golden QA, côté user). Prioritaire
    sur ``use_strict_v4`` (le mode récit tourne avec strict_v4=True).
    """
    if narrative_mode:
        # Branche MODE RÉCIT (1d) : contrat factuel v4 strict + system prompt
        # sectionné. Pas de hardlock_block (le routing récit pose criteria=None,
        # jamais de hardlock). Le few-shot récit est injecté côté user comme le
        # Golden QA, attaché au contexte fact.
        from src.prompt.system_narrative import build_narrative_system_prompt
        sources_json = format_sources_for_llm(retrieved, max_sources=NARRATIVE_MAX_SOURCES)
        user_prompt = _build_user_prompt_strict_v4(
            sources_json, question, golden_qa_prefix=golden_qa_prefix,
        )
        # Forme adaptative (ordre 1926) : le system prompt sectionné dépend du
        # FORMAT routé + des overlays. Sans décision (back-compat / appel direct),
        # défaut = CONSEIL sans overlay (== ancien SYSTEM_PROMPT_NARRATIVE).
        if narrative_decision is not None:
            sys_prompt = build_narrative_system_prompt(
                narrative_decision.format,
                anchor_constraint=narrative_decision.anchor_constraint,
                reassure=narrative_decision.reassure,
                constraint_terms=narrative_decision.constraint_terms,
            )
        else:
            sys_prompt = build_narrative_system_prompt()
    elif use_strict_v4:
        # Branche v4 strict : pas de prose retrieved, JSON tabulaire seul.
        # v4.1 (2026-05-06) : top-5 sources au lieu de top-10 (réduit input
        # tokens + force le LLM à se concentrer sur les sources pertinentes).
        # Étape 7 refonte (2026-05-09) : si `hardlock_block` est fourni
        # (= RouterLLM a détecté une contrainte région/domaine forte),
        # on utilise `build_system_prompt_v4_strict(hardlock_block)` pour
        # injecter le bloc en tête. Sans hardlock_block, comportement v4.1
        # historique préservé strict.
        from src.prompt.system_v4_strict import build_system_prompt_v4_strict
        sources_json = format_sources_for_llm(retrieved, max_sources=5)
        user_prompt = _build_user_prompt_strict_v4(
            sources_json, question, golden_qa_prefix=golden_qa_prefix,
        )
        sys_prompt = build_system_prompt_v4_strict(hardlock_block=hardlock_block)
        # Pas de golden_qa_prefix sur le system (on l'a injecté côté user pour
        # que le LLM le voie ATTACHÉ au contexte fact). Pas de hint_block en v4
        # (le contrat strict n'utilise pas le retry-with-hint pattern v3.2).
    else:
        context = format_context(retrieved)
        guidance_parts: list[str] = []
        if inject_user_level:
            level = classify_user_level(question)
            guidance_parts.append(level_to_guidance(level).tone_instruction)
            intent = classify_intent(question)
            guidance_parts.append(intent_to_format_guidance(intent))
        user_guidance = "\n\n".join(guidance_parts)
        user_prompt = build_user_prompt(
            context, question, user_guidance=user_guidance, hint_block=hint_block,
        )
        sys_prompt = system_prompt_override if system_prompt_override is not None else SYSTEM_PROMPT
        if golden_qa_prefix:
            # Append au system prompt avec séparateur clair. Mistral honore
            # plus strictement les system instructions que les user-side
            # injections — le few-shot avec instruction "IGNORE écoles/chiffres
            # exemple" doit être system pour maximiser le respect.
            sys_prompt = sys_prompt + "\n\n" + golden_qa_prefix

    # Sprint 11 P0 Item 2 — buffer mémoire short-term
    # Construction messages array : system → history (user/assistant alternés) → user current
    messages: list[dict] = [{"role": "system", "content": sys_prompt}]
    if history:
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})

    # v4.1 (2026-05-06) : cap dur output tokens en mode strict v4 pour faire
    # respecter R6 max 250 mots. 250 mots ≈ 350-400 tokens en français.
    # Cap initial 400 = égal au "soft target" R6, ce qui tronquait la long-tail
    # des réponses qui citent 3-5 sources avec URLs Markdown + chiffres
    # (avg observée 184 mots / 280 tokens — mais p90 ~250 mots / ~450 tokens).
    # 2026-05-12 (ordre Jarvis 2026-05-12-1445) : bump 400→800 pour permettre
    # à ces réponses long-tail de FINIR proprement leur dernière phrase /
    # URL Markdown. Le cap reste un filet de sécurité ; R6 ≤250 mots demeure
    # le soft target via SYSTEM_PROMPT_V4_STRICT, donc drift avg attendu
    # léger (+30-40 mots). Coût marginal +$0.0005/query, latence p50 +5-10%.
    # En v3.2 legacy, pas de cap pour préserver le comportement historique.
    api_kwargs: dict = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    if narrative_mode:
        # Cap relevé : les 4 sections + 2-4 pistes sourcées dépassent largement
        # les 800 tokens du contrat court v4. Le cap reste un filet de sécurité.
        api_kwargs["max_tokens"] = NARRATIVE_MAX_TOKENS
    elif use_strict_v4:
        api_kwargs["max_tokens"] = 800
    return api_kwargs


def _strip_brouillon_xml(content: str) -> str:
    """Strip ``<brouillon>...</brouillon><reponse_finale>...</reponse_finale>``
    si présents et retourne juste le contenu de ``<reponse_finale>``.

    Tolérant : si Mistral n'utilise pas les balises (Q simple, fallback,
    consigne ignorée), retourne le content brut tel quel. Extrait depuis
    ``generate()`` pour être réutilisé par ``generate_stream()``.
    """
    m = _RE_REPONSE_FINALE.search(content)
    if m:
        return m.group(1).strip()
    return content


def generate(
    client: Mistral,
    retrieved: list[dict],
    question: str,
    model: str = "mistral-medium-latest",
    temperature: float = 0.3,
    inject_user_level: bool = True,
    system_prompt_override: str | None = None,
    golden_qa_prefix: str | None = None,
    history: list[dict] | None = None,
    hint_block: str = "",
    use_strict_v4: bool = False,
    hardlock_block: str = "",
    narrative_mode: bool = False,
    narrative_decision: "FormatDecision | None" = None,
) -> str:
    """Generate an answer via Mistral.

    `inject_user_level` (Tier 2.2, 2026-04-18) adds a "Profil détecté"
    guidance prefix derived from rule-based classification of the
    question. Disable only for A/B comparisons of the feature itself
    in benchmark harnesses — production should keep it on.

    `system_prompt_override` (Sprint 7, 2026-04-27) optional override
    of the system prompt. Default `None` = utilise `SYSTEM_PROMPT` v3.2
    (non-régression Sprint 5/6 stricte). Pour activer v3.3 strict
    (Sprint 7 Action 3), passer `SYSTEM_PROMPT_V33_STRICT` depuis
    `src.experimental.system_strict`.

    `golden_qa_prefix` (Sprint 10 chantier D, 2026-04-29) optional
    Q&A Golden Dynamic Few-Shot prefix avec **séparation stricte
    Comment/Quoi** (cf `OrientIAPipeline._build_few_shot_prefix`).
    Quand fourni, append au system prompt — la Q&A devient référence
    comportementale, les fiches du retrieved restent seules sources
    factuelles autorisées. Default `None` = backward compat strict.

    `history` (Sprint 11 P0 Item 2, 2026-04-29) optional buffer de la
    conversation précédente pour permettre le suivi de tiroir
    ("Oui Plan A" → développe ce qui a été dit). Format Mistral compliant :
    `[{"role": "user"|"assistant", "content": str}, ...]`. Injecté
    entre system prompt et user current. Default `None`/empty = no-op
    (backward compat strict pour Run F+G + serving stateless).

    `use_strict_v4` (Étape 2 refonte 2026-05-06) bascule sur le contrat
    v4 strict : SYSTEM_PROMPT_V4_STRICT + user prompt JSON `<sources>`
    typé via FactCard. Coupe la prose libre, force le LLM à n'utiliser
    que les chiffres explicitement listés. Default `False` = comportement
    v3.2 historique préservé. Quand `True`, `system_prompt_override`,
    `inject_user_level` et `hint_block` sont IGNORÉS (le contrat v4 a
    sa propre orchestration).
    """
    api_kwargs = _build_chat_kwargs(
        retrieved, question,
        model=model,
        temperature=temperature,
        inject_user_level=inject_user_level,
        system_prompt_override=system_prompt_override,
        golden_qa_prefix=golden_qa_prefix,
        history=history,
        hint_block=hint_block,
        use_strict_v4=use_strict_v4,
        hardlock_block=hardlock_block,
        narrative_mode=narrative_mode,
        narrative_decision=narrative_decision,
    )
    response = client.chat.complete(**api_kwargs)
    content = response.choices[0].message.content
    # Sprint 11 P1.1 v5 — strip brouillon XML balises si détectées.
    # Format attendu : <brouillon>...</brouillon>\n<reponse_finale>...</reponse_finale>
    # Tolérant : si Mistral n'utilise pas les balises (Q simple, fallback,
    # consigne ignorée), retourne le content brut.
    return _strip_brouillon_xml(content)


# Seuil de flush du buffer pre-streaming : si on a accumulé plus de N caractères
# sans voir `<brouillon>` ou `<reponse_finale>`, on considère que Mistral n'a
# pas utilisé les balises XML (cas tolérant de `_strip_brouillon_xml`) et on
# flush directement en mode stream pour ne pas faire attendre l'utilisateur.
_STREAM_FLUSH_THRESHOLD_CHARS = 80

_OPEN_TAG = "<reponse_finale>"
_CLOSE_TAG = "</reponse_finale>"


async def generate_stream(
    client: Mistral,
    retrieved: list[dict],
    question: str,
    *,
    model: str = "mistral-medium-latest",
    temperature: float = 0.3,
    inject_user_level: bool = True,
    system_prompt_override: str | None = None,
    golden_qa_prefix: str | None = None,
    history: list[dict] | None = None,
    hint_block: str = "",
    use_strict_v4: bool = False,
    hardlock_block: str = "",
    narrative_mode: bool = False,
    narrative_decision: "FormatDecision | None" = None,
) -> AsyncGenerator[str, None]:
    """Variante streaming async de :func:`generate`.

    Reuse la même construction de messages que ``generate()`` via
    ``_build_chat_kwargs()``. Utilise ``client.chat.stream_async()`` pour
    yieldé les chunks de tokens au fil de l'eau.

    **Strip brouillon en streaming** :
    Si le modèle wrappe sa sortie en ``<brouillon>...</brouillon><reponse_finale>...</reponse_finale>``,
    on buffer les premiers chunks jusqu'à détection du tag d'ouverture
    ``<reponse_finale>`` puis on stream le contenu jusqu'au tag de fermeture.
    Si après ``_STREAM_FLUSH_THRESHOLD_CHARS`` caractères on n'a vu aucune
    balise (cas tolérant : Q simple où Mistral skip les balises), on flush
    le buffer accumulé et on continue à streamer tel quel.

    **Cancellation** : ``async for`` propage ``asyncio.CancelledError``
    naturellement quand le consumer (FastAPI handler) est cancelled.
    Le ``async with`` ferme proprement l'EventStreamAsync, qui ferme la
    connection httpx upstream et signale à l'API Mistral d'arrêter la
    génération — tokens non consommés.

    Args:
        Identiques à ``generate()``.

    Yields:
        Chunks de texte (str) au fur et à mesure de la génération.
    """
    api_kwargs = _build_chat_kwargs(
        retrieved, question,
        model=model,
        temperature=temperature,
        inject_user_level=inject_user_level,
        system_prompt_override=system_prompt_override,
        golden_qa_prefix=golden_qa_prefix,
        history=history,
        hint_block=hint_block,
        use_strict_v4=use_strict_v4,
        hardlock_block=hardlock_block,
        narrative_mode=narrative_mode,
        narrative_decision=narrative_decision,
    )

    pending: str = ""
    in_response_phase: bool = False

    async with await client.chat.stream_async(**api_kwargs) as stream:
        async for event in stream:
            # event.data.choices[0].delta.content — chunk de texte (peut être None / vide)
            try:
                chunk = event.data.choices[0].delta.content
            except (AttributeError, IndexError):
                continue
            if not isinstance(chunk, str) or not chunk:
                continue

            if in_response_phase:
                # On stream directement, en surveillant le tag de fermeture.
                close_idx = chunk.find(_CLOSE_TAG)
                if close_idx >= 0:
                    if close_idx > 0:
                        yield chunk[:close_idx]
                    return
                yield chunk
                continue

            # Phase d'accumulation : on cherche `<reponse_finale>` ou on décide
            # que Mistral n'utilise pas les balises XML.
            pending += chunk
            open_idx = pending.find(_OPEN_TAG)
            if open_idx >= 0:
                # Trouvé le tag d'ouverture — on commence à streamer après lui.
                after = pending[open_idx + len(_OPEN_TAG):]
                close_idx = after.find(_CLOSE_TAG)
                if close_idx >= 0:
                    # Cas dégénéré : tag fermant déjà dans le buffer.
                    if close_idx > 0:
                        yield after[:close_idx]
                    return
                if after:
                    yield after
                pending = ""
                in_response_phase = True
                continue

            # Pas (encore) de tag d'ouverture. Si on a passé le seuil ET qu'on
            # n'a vu aucune balise (ni `<brouillon>`, ni `<reponse_finale>`),
            # on considère que Mistral ne wrappe pas → flush et stream.
            if len(pending) >= _STREAM_FLUSH_THRESHOLD_CHARS:
                lowered = pending.lower()
                if "<brouillon" not in lowered and "<reponse_finale" not in lowered:
                    yield pending
                    pending = ""
                    in_response_phase = True

    # Fin de stream sans avoir trouvé `<reponse_finale>`. Si on a encore du
    # contenu dans pending (cas court qui n'a pas dépassé le seuil), on flush
    # via le strip tolérant (même comportement que `generate()` sync).
    if not in_response_phase and pending:
        yield _strip_brouillon_xml(pending)


_RE_REPONSE_FINALE = re.compile(
    r"<reponse_finale>\s*(.*?)\s*</reponse_finale>",
    re.DOTALL | re.IGNORECASE,
)
