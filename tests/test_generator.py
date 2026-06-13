from unittest.mock import MagicMock
from src.rag.generator import format_context, generate, selectivite_qualitative


def _full_fiche():
    return {
        "nom": "Master Cybersécurité",
        "etablissement": "Université de Rennes",
        "ville": "Rennes",
        "departement": "Ille-et-Vilaine",
        "statut": "Public",
        "niveau": "bac+5",
        "labels": ["SecNumEdu", "CTI"],
        "taux_acces_parcoursup_2025": 18.0,
        "nombre_places": 24,
        "detail": "A" * 600,  # 600 chars to test 500-char truncation
        "profil_admis": {
            "mentions_pct": {"tb": 45.0, "b": 30.0, "ab": 20.0, "sans": 5.0},
            "bac_type_pct": {"general": 80.0, "techno": 15.0, "pro": 5.0},
            "boursiers_pct": 20.0,
        },
        "debouches": [
            {"libelle": "Analyste cyber", "code_rome": "M1812"},
            {"libelle": "Architecte réseaux", "code_rome": "M1803"},
            {"libelle": "RSSI", "code_rome": "M1802"},
            {"libelle": "Admin sécurité", "code_rome": "M1810"},
            {"libelle": "Pentester", "code_rome": "M1809"},
        ],
        "url_onisep": "https://onisep.fr/FOR.1234",
    }


def test_format_context_includes_all_fiches():
    results = [
        {"fiche": {"nom": "Master A", "etablissement": "X", "ville": "Paris",
                   "labels": ["SecNumEdu"], "statut": "Public",
                   "taux_acces_parcoursup_2025": 25.0}, "score": 0.9},
        {"fiche": {"nom": "Master B", "etablissement": "Y", "ville": "Lyon",
                   "labels": [], "statut": "Privé"}, "score": 0.7},
    ]
    context = format_context(results)
    assert "Master A" in context
    assert "Master B" in context
    assert "SecNumEdu" in context


def test_format_context_selectivite_appears_before_detail():
    """Critical info (selectivity) must come before verbose detail text."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    sel_idx = ctx.find("Sélectivité")
    detail_idx = ctx.find("Détail")
    assert sel_idx != -1 and detail_idx != -1
    assert sel_idx < detail_idx, (
        "Sélectivité must come before Détail for signal-first ordering"
    )


def test_format_context_detail_truncated_to_500_chars():
    """Phase 1.2: detail window expanded from 250 → 500 chars."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    detail_line = next(
        line for line in ctx.split("\n") if line.strip().startswith("Détail")
    )
    detail_body = detail_line.split("Détail:", 1)[1].strip()
    assert 490 <= len(detail_body) <= 520, (
        f"Detail should be ~500 chars, got {len(detail_body)}"
    )


def test_format_context_debouches_limited_to_three():
    """Phase 1.2: top 3 metiers only (vs 5 before) to reduce noise."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    debouches_line = next(
        line for line in ctx.split("\n") if "Débouchés" in line
    )
    assert "Analyste cyber" in debouches_line
    assert "Architecte réseaux" in debouches_line
    assert "RSSI" in debouches_line
    assert "Admin sécurité" not in debouches_line, "should stop at 3 metiers"
    assert "Pentester" not in debouches_line


def test_format_context_emits_at_most_eight_lines_per_fiche():
    """Post Vague D: the original 8-line budget (1 header + 7 content) was
    expanded by one slot for the InserSup insertion line. Fiches without
    insertion must remain ≤ 8 lines. Fiches WITH insertion may go to 9."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    non_empty = [l for l in ctx.split("\n") if l.strip()]
    # Base fiche has no insertion → still ≤ 8 lines
    assert len(non_empty) <= 8, (
        f"Expected ≤ 8 lines per fiche (no insertion), got {len(non_empty)}"
    )


def test_selectivite_qualitative_thresholds():
    """Qualitative label reflects Parcoursup access rate."""
    assert selectivite_qualitative(10.0) == "Très sélective"
    assert selectivite_qualitative(19.9) == "Très sélective"
    assert selectivite_qualitative(20.0) == "Sélective"
    assert selectivite_qualitative(49.9) == "Sélective"
    assert selectivite_qualitative(50.0) == "Accessible"
    assert selectivite_qualitative(85.0) == "Accessible"
    assert selectivite_qualitative(None) == "non renseignée"


def test_format_context_shows_qualitative_selectivity():
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    # 18% → Très sélective
    assert "18" in ctx and "Très sélective" in ctx


def test_format_context_omits_missing_optional_lines():
    """Lines with no data are omitted rather than printing 'None'."""
    minimal = {
        "nom": "BTS X",
        "etablissement": "Lycée Y",
        "ville": "Paris",
        "statut": "Public",
        "labels": [],
    }
    results = [{"fiche": minimal, "score": 0.5}]
    ctx = format_context(results)
    assert "None" not in ctx
    # Labels line is omitted when there's nothing to say
    assert "Profil admis" not in ctx
    assert "Débouchés" not in ctx
    assert "Détail" not in ctx


def test_format_context_no_labels_shows_explicit_none():
    """When labels list is empty, the labels line is simply omitted."""
    fiche = _full_fiche()
    fiche["labels"] = []
    results = [{"fiche": fiche, "score": 0.9}]
    ctx = format_context(results)
    # No 'Labels officiels:' line when there are none
    assert "Labels officiels" not in ctx


def test_generate_calls_mistral_with_system_and_user_prompts():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
    mock_client.chat.complete.return_value = mock_response

    results = [{"fiche": {"nom": "F", "etablissement": "E", "ville": "V", "labels": [],
                          "statut": "Public"}, "score": 0.5}]
    answer = generate(mock_client, results, "question?", model="mistral-medium-latest")
    assert answer == "Response text"
    call = mock_client.chat.complete.call_args
    messages = call.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "question?" in messages[1]["content"]


# === Vague A — enriched generator context ===

def _vague_a_fiche() -> dict:
    """Fiche with Vague A structured admission block + extended demographics."""
    return {
        "nom": "Master Cybersécurité",
        "etablissement": "Université de Rennes",
        "ville": "Rennes",
        "departement": "Ille-et-Vilaine",
        "statut": "Public",
        "niveau": "bac+5",
        "labels": ["SecNumEdu"],
        "rncp": "37989",
        "cod_aff_form": "42156",
        "lien_form_psup": "https://www.parcoursup.fr/formation/42156",
        "url_onisep": "https://onisep.fr/FOR.9891",
        "admission": {
            "session": 2025,
            "taux_acces": 18.0,
            "places": 24,
            "volumes": {
                "voeux_totaux": 1250,
                "voeux_phase_principale": 800,
                "classes_phase_principale": 600,
            },
            "internat_disponible": True,
        },
        "profil_admis": {
            "mentions_pct": {"tb": 45.0, "b": 30.0, "ab": 20.0, "sans": 5.0},
            "bac_type_pct": {"general": 80.0, "techno": 15.0, "pro": 5.0},
            "boursiers_pct": 20.0,
            "femmes_pct": 24.0,
            "neobacheliers_pct": 85.0,
        },
        "debouches": [{"libelle": "RSSI", "code_rome": "M1812"}],
    }


def test_vague_a_selectivite_includes_volumes_and_internat():
    """New admission.volumes + internat are surfaced to the LLM."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "1250" in sel_line, "voeux_totaux must appear"
    assert "Internat: oui" in sel_line


def test_vague_a_selectivite_falls_back_to_legacy_when_no_admission_block():
    """Backward compat: fiches without admission.* still work via legacy flat fields."""
    legacy = {
        "nom": "M", "etablissement": "E", "ville": "V", "statut": "Public",
        "labels": [],
        "taux_acces_parcoursup_2025": 42.0,
        "nombre_places": 30,
    }
    ctx = format_context([{"fiche": legacy, "score": 0.5}])
    assert "42" in ctx
    assert "Places: 30" in ctx


def test_vague_a_profil_shows_full_bac_type_split():
    """All 3 bac types (général/techno/pro) are surfaced, not just général."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    profil_line = next(l for l in ctx.split("\n") if "Profil admis" in l)
    assert "général 80%" in profil_line
    assert "techno 15%" in profil_line
    assert "pro 5%" in profil_line


def test_vague_a_profil_includes_diversity_demographics():
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    profil_line = next(l for l in ctx.split("\n") if "Profil admis" in l)
    assert "Femmes 24%" in profil_line
    assert "Néobacheliers 85%" in profil_line


def test_vague_a_source_line_exposes_urls_only_no_raw_codes():
    """Tier 0 fix (post-user-feedback 2026-04-18) : la source line expose
    les URLs comme instructions au LLM pour produire des liens markdown
    cliquables — MAIS ne contient plus les codes bruts RNCP / cod_aff_form
    (polluent la lecture utilisateur selon les 4 testeurs). Les URLs sont
    toujours présentes pour que le LLM puisse les transformer en liens."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    src_line = next(l for l in ctx.split("\n") if "Sources" in l and "Parcoursup" in l)
    # URL Parcoursup toujours exposée (pour le LLM, à transformer en lien)
    assert "parcoursup.fr/formation/42156" in src_line
    # URL ONISEP idem
    assert "onisep.fr" in src_line and "FOR.9891" in src_line
    # Instruction au LLM : liens markdown cliquables, pas d'ID brut
    assert "liens markdown" in src_line.lower() or "cliquable" in src_line.lower()
    # Les codes bruts ne sont PAS dans la ligne source
    assert "RNCP 37989" not in src_line
    assert "cod_aff_form 42156" not in src_line


def test_vague_a_budget_still_eight_lines_per_fiche():
    """Despite richer content, still ≤8 lines per fiche (contract from Phase 1.2)."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    non_empty = [l for l in ctx.split("\n") if l.strip()]
    assert len(non_empty) <= 8, (
        f"Vague A must preserve ≤8-lines budget, got {len(non_empty)}: {non_empty}"
    )


# === Vague C — trends folded into selectivity line ===


def _vague_c_fiche_with_trends() -> dict:
    """Fiche with historical trends (taux down, voeux up) — signals a
    formation becoming more selective and more popular 2023→2025."""
    base = _vague_a_fiche()
    base["trends"] = {
        "taux_acces": {
            "direction": "down", "delta_pp": -23.0,
            "start_year": 2023, "end_year": 2025,
            "start_value": 68.0, "end_value": 45.0,
            "interpretation": "taux d'accès en baisse 2023→2025 (68% → 45%) : formation devenue plus sélective",
        },
        "places": {
            "direction": "stable", "delta": 2,
            "start_year": 2023, "end_year": 2025,
            "start_value": 24, "end_value": 26,
            "interpretation": None,
        },
        "voeux": {
            "direction": "up", "delta": 300,
            "start_year": 2023, "end_year": 2025,
            "start_value": 500, "end_value": 800,
            "interpretation": "popularité en hausse 2023→2025 (500 → 800 vœux) : attrait renforcé",
        },
    }
    return base


def test_vague_c_selectivity_line_includes_trend_when_significant():
    results = [{"fiche": _vague_c_fiche_with_trends(), "score": 0.9}]
    ctx = format_context(results)
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "Tendance" in sel_line
    # Taux drop surfaced
    assert "↓23pp" in sel_line
    assert "plus sélective" in sel_line
    # Voeux growth surfaced
    assert "vœux" in sel_line and "+60%" in sel_line
    # Stable places NOT mentioned (direction=stable)
    assert "places ↑" not in sel_line
    assert "places ↓" not in sel_line


def test_vague_c_no_trend_suffix_when_all_stable():
    f = _vague_a_fiche()
    f["trends"] = {
        "taux_acces": {"direction": "stable", "delta_pp": 2.0,
                       "start_year": 2023, "end_year": 2025,
                       "start_value": 50.0, "end_value": 52.0,
                       "interpretation": "taux stable"},
    }
    ctx = format_context([{"fiche": f, "score": 0.9}])
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "Tendance" not in sel_line


def test_vague_c_no_trend_suffix_when_trends_missing():
    """Fiche without trends field — no regression, no trend suffix."""
    f = _vague_a_fiche()
    # explicitly no "trends" key
    ctx = format_context([{"fiche": f, "score": 0.9}])
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "Tendance" not in sel_line


def test_vague_c_budget_preserved_at_eight_lines():
    """Trends folded INTO selectivity line — ≤8-line budget preserved."""
    results = [{"fiche": _vague_c_fiche_with_trends(), "score": 0.9}]
    ctx = format_context(results)
    non_empty = [l for l in ctx.split("\n") if l.strip()]
    assert len(non_empty) <= 8


# === Vague D — insertion pro line (optional, emits when matched) ===


def _vague_d_fiche_with_insertion() -> dict:
    base = _vague_a_fiche()
    base["insertion"] = {
        "taux_emploi_12m": 0.88,
        "taux_emploi_18m": 0.91,
        "taux_emploi_stable_12m": 0.72,
        "salaire_median_12m_mensuel_net": 2500,
        "salaire_median_30m_mensuel_net": 3200,
        "nombre_sortants": 80,
        "cohorte": "2022",
        "granularite": "discipline",
        "disclaimer": "Chiffres d'insertion calculés sur tous les diplômés INFORMATIQUE...",
        "source": "InserSup DEPP",
        "source_url": "https://www.data.gouv.fr/datasets/...",
    }
    return base


def test_vague_d_insertion_line_emitted_when_present():
    results = [{"fiche": _vague_d_fiche_with_insertion(), "score": 0.9}]
    ctx = format_context(results)
    ins_line = next(l for l in ctx.split("\n") if "Insertion" in l)
    assert "88%" in ins_line or "88 %" in ins_line  # taux_emploi_12m
    assert "2500" in ins_line  # salaire médian
    assert "2022" in ins_line  # cohorte


def test_vague_d_insertion_line_absent_when_no_insertion():
    fiche = _vague_a_fiche()  # no insertion key
    ctx = format_context([{"fiche": fiche, "score": 0.9}])
    assert "Insertion" not in ctx


def test_vague_d_insertion_line_includes_granularite_disclaimer():
    """Granularity (discipline vs aggregate) must be visible — honest scope."""
    fiche = _vague_d_fiche_with_insertion()
    fiche["insertion"]["granularite"] = "type_diplome_agrege"
    ctx = format_context([{"fiche": fiche, "score": 0.9}])
    ins_line = next(l for l in ctx.split("\n") if "Insertion" in l)
    assert "agrégat" in ins_line.lower() or "agregat" in ins_line.lower()


def test_vague_d_handles_percent_already_stored():
    """Some InserSup values may come pre-multiplied as percents (88.0 not 0.88).
    The generator must detect and avoid double-multiplying."""
    fiche = _vague_d_fiche_with_insertion()
    fiche["insertion"]["taux_emploi_12m"] = 88.0  # stored as percent already
    ctx = format_context([{"fiche": fiche, "score": 0.9}])
    ins_line = next(l for l in ctx.split("\n") if "Insertion" in l)
    # Should show "88%", NOT "8800%"
    assert "88%" in ins_line or "88 %" in ins_line
    assert "8800" not in ins_line


def test_vague_d_skips_nd_values_gracefully():
    """When taux_emploi_12m is None (nd) but salaire is available, show salaire only."""
    fiche = _vague_d_fiche_with_insertion()
    fiche["insertion"]["taux_emploi_12m"] = None
    fiche["insertion"]["taux_emploi_18m"] = None
    fiche["insertion"]["taux_emploi_stable_12m"] = None
    # Salaire remains
    ctx = format_context([{"fiche": fiche, "score": 0.9}])
    ins_line = next(l for l in ctx.split("\n") if "Insertion" in l)
    assert "2500" in ins_line
    # Should NOT show "emploi: None%" or similar
    assert "None" not in ins_line


def test_vague_d_budget_allows_nine_lines_with_insertion():
    """When insertion is present, the budget becomes ≤9 lines per fiche
    (1 header + 8 content with insertion as the new slot). Without insertion,
    stays at ≤8. This is the documented expansion of the format."""
    results = [{"fiche": _vague_d_fiche_with_insertion(), "score": 0.9}]
    ctx = format_context(results)
    non_empty = [l for l in ctx.split("\n") if l.strip()]
    assert len(non_empty) <= 9


def test_insertion_line_reads_insertion_pro_new_schema():
    """Fix 2026-06-13 — chemin legacy lit insertion_pro (corpus migré), salaire
    via la clé neuve + net depuis le flag, source mappée data-driven (pas de
    'InserSup DEPP' hardcodé). Cas MIAGE Lille."""
    fiche = _vague_a_fiche()
    fiche["insertion_pro"] = {
        "taux_emploi_12m": 0.747,
        "salaire_median_embauche": 2370,
        "salaire_net": True,
        "salaire_horizon": "12m",
        "salaire_cohorte": "2022",
        "granularite": "etablissement_x_discipline",
        "nombre_sortants": 83,
        "source": "insersup_mesr",
    }
    line = next(l for l in format_context([{"fiche": fiche, "score": 0.9}]).split("\n")
                if "Insertion" in l)
    assert "2370" in line              # salaire (clé neuve)
    assert "net" in line.lower()       # unité depuis le flag salaire_net
    assert "75%" in line               # 0.747 -> 75%
    assert "InserSup MESR" in line     # source mappée, PAS hardcodée
    assert "2022" in line              # cohorte salaire
    assert "salaire_net" not in line   # le flag n'est jamais sorti tel quel


def test_v2_profil_line_prefixes_mentions_with_word_mention():
    """V2 data cleanup (ADR-036) : les mentions TB/B/AB sont préfixées
    'mention' dans le contexte pour éviter que le LLM Mistral Medium ne
    confonde 'B 42%' (mention Bien) avec 'série bac B' (supprimée 1995).

    Bug root cause identifié dans Q8 Gate J+6 ground truth humain 2026-04-22."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    profil_line = next(l for l in ctx.split("\n") if "Profil admis" in l)
    # Préfixe "mention" présent sur les 3 niveaux
    assert "mention TB" in profil_line
    assert "mention B" in profil_line
    assert "mention AB" in profil_line
    # Les anciens formats sans préfixe (risque confusion) sont absents —
    # on vérifie via une heuristique : "TB X%" seul ne doit plus apparaître
    # séparé d'un préfixe "mention" (sinon le bug est réintroduit)
    # Safety : on cherche " TB 45%" (avec espace devant) sans "mention" juste avant
    assert ", TB " not in profil_line, "mention TB doit toujours avoir préfixe 'mention'"
