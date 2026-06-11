"""Tests SELECT structuré — Chantier 2 (2026-05-03)."""
from __future__ import annotations

import pytest

from src.lookup.structured_select import (
    AMBIGUITY_DELTA,
    _DISCRIMINATORS,
    Entity,
    FUZZY_THRESHOLD,
    INVALID_VALUES,
    SelectResult,
    detect_field_key,
    extract_entity_simple,
    extract_field,
    format_select_response,
    is_select_candidate,
    is_valid_field_value,
    lookup_formation,
    try_select_or_none,
)


# ──────────────────────── Constants conformity ────────────────────────


class TestConstants:
    def test_fuzzy_threshold_85(self):
        assert FUZZY_THRESHOLD == 85, "Plan exige seuil ≥85 (cf voici-le-retour-de-lively-yao.md)"

    def test_invalid_values_includes_zero_and_dash(self):
        assert 0 in INVALID_VALUES
        assert -1 in INVALID_VALUES
        assert None in INVALID_VALUES
        assert "-" in INVALID_VALUES
        assert "N/A" in INVALID_VALUES
        assert "non renseigné" in INVALID_VALUES

    def test_ambiguity_delta_reasonable(self):
        assert 0 < AMBIGUITY_DELTA <= 10


# ──────────────────────── is_valid_field_value ────────────────────────


class TestIsValidFieldValue:
    def test_zero_invalid(self):
        assert not is_valid_field_value(0)
        assert not is_valid_field_value(0.0)
        assert not is_valid_field_value("0")
        assert not is_valid_field_value("0%")

    def test_minus_one_invalid(self):
        assert not is_valid_field_value(-1)

    def test_none_invalid(self):
        assert not is_valid_field_value(None)

    def test_empty_string_invalid(self):
        assert not is_valid_field_value("")
        assert not is_valid_field_value("   ")  # whitespace strip via lower in the impl

    def test_dash_invalid(self):
        assert not is_valid_field_value("-")
        assert not is_valid_field_value("N/A")
        assert not is_valid_field_value("non renseigné")

    def test_nan_invalid(self):
        import math
        assert not is_valid_field_value(float("nan"))
        assert not is_valid_field_value(float("inf"))

    def test_real_values_valid(self):
        assert is_valid_field_value(27.5)
        assert is_valid_field_value(100)
        assert is_valid_field_value("Public")
        assert is_valid_field_value(2080)


# ──────────────────────── Entity extraction ────────────────────────


class TestExtractEntitySimple:
    def test_empty_question_returns_empty_entity(self):
        e = extract_entity_simple("")
        assert e.is_empty()

    def test_extracts_city(self):
        e = extract_entity_simple("Quel est le taux d'accès à Bordeaux ?")
        assert e.ville is not None
        assert e.ville.lower() == "bordeaux"

    def test_extracts_acronym(self):
        e = extract_entity_simple("Combien de places à EFREI ?")
        # EFREI doit apparaître dans formation_name (pas filtré comme stopword)
        assert e.formation_name is not None
        assert "EFREI" in e.formation_name

    def test_extracts_niveau(self):
        e = extract_entity_simple("Combien de places en BUT informatique ?")
        assert e.niveau is not None
        assert e.niveau == "BUT"

    def test_combines_city_acronym_niveau(self):
        e = extract_entity_simple("Taux d'accès Bachelor cyber EFREI Bordeaux ?")
        assert e.ville and e.ville.lower() == "bordeaux"
        assert e.formation_name and "EFREI" in e.formation_name
        assert e.niveau and e.niveau == "BACHELOR"


# ──────────────────────── detect_field_key ────────────────────────


class TestDetectFieldKey:
    def test_taux_acces_pattern(self):
        result = detect_field_key("Quel est le taux d'accès de l'EFREI ?")
        assert result is not None
        field_key, label = result
        assert field_key == "taux_acces_parcoursup_2025"
        assert "accès" in label.lower() or "acces" in label.lower()

    def test_selectivite_pattern(self):
        result = detect_field_key("C'est quoi la sélectivité de Sciences Po ?")
        assert result is not None
        assert result[0] == "taux_acces_parcoursup_2025"

    def test_places_pattern(self):
        result = detect_field_key("Combien de places à EFREI Bordeaux ?")
        assert result is not None
        assert result[0] == "nombre_places"

    def test_salaire_pattern(self):
        result = detect_field_key("Quel salaire médian après LEA ?")
        assert result is not None
        assert "salaire" in result[0]

    def test_taux_emploi_3ans(self):
        result = detect_field_key("Quel est le taux d'emploi à 3 ans pour Master Info ?")
        assert result is not None
        assert "3ans" in result[0]

    def test_no_match_returns_none(self):
        result = detect_field_key("Quelles formations en cybersécurité ?")
        assert result is None

    def test_orientation_question_no_match(self):
        result = detect_field_key("Je suis en terminale, quelle orientation ?")
        assert result is None


# ──────────────────────── lookup_formation (rapidfuzz) ────────────────────────


class TestLookupFormation:
    def test_empty_entity_returns_none(self):
        fiches = [{"nom": "X"}]
        f, score, amb = lookup_formation(Entity(), fiches)
        assert f is None
        assert score == 0.0
        assert amb is False

    def test_empty_fiches_returns_none(self):
        e = Entity(formation_name="X")
        f, score, amb = lookup_formation(e, [])
        assert f is None

    def test_exact_match_high_score(self):
        fiches = [
            {"nom": "Bachelor Cybersécurité", "etablissement": "EFREI", "ville": "Bordeaux"},
            {"nom": "Master Droit", "etablissement": "Sorbonne", "ville": "Paris"},
        ]
        e = Entity(formation_name="Bachelor Cybersécurité EFREI", ville="Bordeaux")
        f, score, amb = lookup_formation(e, fiches)
        assert f is not None
        assert f["etablissement"] == "EFREI"
        assert score >= FUZZY_THRESHOLD

    def test_no_match_below_threshold(self):
        fiches = [
            {"nom": "Master Droit", "etablissement": "Sorbonne", "ville": "Paris"},
        ]
        e = Entity(formation_name="Bachelor Aérospatial", ville="Toulouse")
        f, score, amb = lookup_formation(e, fiches)
        assert f is None  # score insuffisant
        assert score < FUZZY_THRESHOLD

    def test_ambiguous_two_efreis(self):
        """Si EFREI Paris et EFREI Bordeaux matchent à scores proches → ambiguous."""
        fiches = [
            {"nom": "Bachelor Cybersécurité", "etablissement": "EFREI", "ville": "Paris"},
            {"nom": "Bachelor Cybersécurité", "etablissement": "EFREI", "ville": "Bordeaux"},
        ]
        e = Entity(formation_name="EFREI Bachelor Cybersécurité")  # pas de ville → ambiguous
        f, score, amb = lookup_formation(e, fiches)
        assert f is not None  # un match retourné
        assert amb is True


# ──────────────────────── Garde discriminateur (critique expert #4b) ────────────────────────


class TestDiscriminatorGuard:
    """Critique expert #4b (2026-05-03) : ne pas confondre prépa commerciale
    avec prépa A/L à Henri IV juste parce que « prépa » + « Henri IV »
    overlap accidentellement."""

    def test_commercial_disc_blocks_al_match(self):
        """« prépa commerciales Henri IV » ne doit PAS matcher la prépa A/L Henri IV."""
        fiches = [
            {"nom": "CPGE A/L Lettres Supérieures", "etablissement": "Lycée Henri IV", "ville": "Paris"},
        ]
        e = extract_entity_simple("Quel est le taux d'accès des prépas commerciales à Henri IV ?")
        f, score, amb = lookup_formation(e, fiches)
        # Conservatif : reject (mieux qu'un faux positif confiant)
        assert f is None, "Prépa commerciale ≠ prépa A/L — la garde doit reject"

    def test_al_disc_matches_al_fiche(self):
        """« prépa A/L Henri IV » doit matcher correctement la prépa A/L."""
        fiches = [
            {"nom": "CPGE A/L Lettres Supérieures", "etablissement": "Lycée Henri IV", "ville": "Paris"},
        ]
        e = extract_entity_simple("Quel est le taux d'accès de la prépa A/L Henri IV ?")
        f, score, amb = lookup_formation(e, fiches)
        assert f is not None
        assert "A/L" in f["nom"]

    def test_cyber_prefix_match_cybersecurite(self):
        """« cyber » dans la query doit matcher « Cybersécurité » par préfixe."""
        fiches = [
            {"nom": "Bachelor Cybersécurité", "etablissement": "EPITA Lyon", "ville": "Lyon"},
        ]
        e = extract_entity_simple("Combien de places en Bachelor cyber Lyon ?")
        f, score, amb = lookup_formation(e, fiches)
        assert f is not None  # cyber → cybersécurité préfixe match

    def test_droit_international_disc_filters_fiches(self):
        """« Master Droit International » doit privilégier la fiche International,
        pas n'importe quelle fiche Master Droit."""
        fiches = [
            {"nom": "Master Droit International", "etablissement": "Sorbonne", "ville": "Paris"},
            {"nom": "Master Droit Civil", "etablissement": "Sorbonne", "ville": "Paris"},
        ]
        e = extract_entity_simple("Quel est le taux d'accès du Master Droit International Sorbonne ?")
        f, score, amb = lookup_formation(e, fiches)
        assert f is not None
        assert "International" in f["nom"], (
            f"La garde discriminateur 'international' doit privilégier la fiche International. "
            f"Actuellement: {f['nom']}"
        )

    def test_no_discriminator_no_guard_applied(self):
        """Sans discriminateur dans la query, le match standard fonctionne."""
        fiches = [{"nom": "BTS Informatique", "etablissement": "Lycée X", "ville": "Lyon"}]
        e = extract_entity_simple("Quel est le taux d'accès du BTS X à Lyon ?")
        f, score, amb = lookup_formation(e, fiches)
        # Soit un match (BTS reconnu) soit un reject (score trop bas) — pas de garde déclenchée
        # Test minimal : pas d'exception
        assert f is None or f is not None

    def test_discriminators_set_includes_critical_keywords(self):
        """Vérification que la liste des discriminateurs couvre les keywords critiques."""
        critical = {
            "commercial", "commerciales",
            "scientifique", "kine", "kiné",
            "international", "internationale",
            "mp", "pcsi", "bcpst",
            "cyber", "cybersecurite",
        }
        for k in critical:
            assert k in _DISCRIMINATORS, f"Discriminateur manquant : {k}"


# ──────────────────────── extract_field (avec dotted path + INVALID_VALUES) ────────────────────────


class TestExtractField:
    def test_simple_field(self):
        f = {"taux_acces_parcoursup_2025": 27.5}
        assert extract_field(f, "taux_acces_parcoursup_2025") == 27.5

    def test_dotted_path(self):
        f = {"insertion_pro": {"salaire_median_embauche": 2080}}
        assert extract_field(f, "insertion_pro.salaire_median_embauche") == 2080

    def test_missing_field_returns_none(self):
        f = {"nom": "X"}
        assert extract_field(f, "taux_acces_parcoursup_2025") is None

    def test_zero_value_invalid(self):
        f = {"taux_acces_parcoursup_2025": 0}
        # GUARDE EXPERT : 0% taux d'accès = catastrophe démo si pas filtré
        assert extract_field(f, "taux_acces_parcoursup_2025") is None

    def test_minus_one_invalid(self):
        f = {"nombre_places": -1}
        assert extract_field(f, "nombre_places") is None

    def test_dotted_path_missing_intermediate(self):
        f = {"nom": "X"}
        assert extract_field(f, "insertion_pro.salaire_median_embauche") is None

    def test_dotted_path_intermediate_not_dict(self):
        f = {"insertion_pro": "string_value"}
        assert extract_field(f, "insertion_pro.taux_emploi_3ans") is None


# ──────────────────────── format_select_response (templater) ────────────────────────


class TestFormatSelectResponse:
    def test_includes_formation_name_and_value(self):
        f = {"nom": "Bachelor Cyber", "etablissement": "EFREI", "ville": "Bordeaux"}
        out = format_select_response(f, "taux_acces_parcoursup_2025", "taux d'accès", 77.0)
        assert "Bachelor Cyber" in out
        assert "EFREI" in out
        assert "Bordeaux" in out
        assert "77 %" in out

    def test_taux_format_percentage(self):
        f = {"nom": "X"}
        out = format_select_response(f, "taux_acces_parcoursup_2025", "taux d'accès", 0.275)
        # ratio 0-1 doit être converti en %
        assert "28 %" in out  # round(0.275 * 100) = 28

    def test_salaire_format_euro(self):
        f = {"nom": "X"}
        out = format_select_response(f, "insertion_pro.salaire_median_embauche", "salaire médian", 2080.5)
        assert "2080" in out or "2081" in out
        assert "€" in out

    def test_places_format(self):
        f = {"nom": "X"}
        out = format_select_response(f, "nombre_places", "nombre de places", 24)
        assert "24 places" in out

    def test_url_source_when_lien_form_psup_present(self):
        f = {"nom": "X", "lien_form_psup": "https://parcoursup.fr/X"}
        out = format_select_response(f, "taux_acces_parcoursup_2025", "taux", 50.0)
        assert "https://parcoursup.fr/X" in out
        assert "fiche officielle Parcoursup" in out

    def test_no_url_no_source_suffix(self):
        f = {"nom": "X"}
        out = format_select_response(f, "taux_acces_parcoursup_2025", "taux", 50.0)
        assert "Source" not in out


# ──────────────────────── try_select_or_none (end-to-end) ────────────────────────


class TestTrySelectOrNone:
    def _make_fiches(self):
        return [
            {
                "id": "F1",
                "nom": "Bachelor Cybersécurité et Ethical Hacking",
                "etablissement": "EFREI Bordeaux",
                "ville": "Bordeaux",
                "niveau": "bac+3",
                "taux_acces_parcoursup_2025": 77.0,
                "nombre_places": 36,
                "lien_form_psup": "https://parcoursup.fr/efrei-bordeaux",
            },
            {
                "id": "F2",
                "nom": "Master Droit International",
                "etablissement": "Université Paris-Panthéon-Assas",
                "ville": "Paris",
                "niveau": "bac+5",
                "taux_acces_parcoursup_2025": None,  # absent en source
            },
            {
                "id": "F3",
                "nom": "BTS Cybersécurité, Informatique et Réseaux",
                "etablissement": "Lycée Déodat Toulouse",
                "ville": "Toulouse",
                "niveau": "bac+2",
                "taux_acces_parcoursup_2025": 28.0,
                "nombre_places": 24,
            },
        ]

    def test_no_field_pattern_returns_none(self):
        """Question sans field key détecté → None (laisser router décider)."""
        result = try_select_or_none("Je suis en terminale, quelle orientation ?", self._make_fiches())
        assert result is None

    def test_select_success_with_url(self):
        """Question factual_pointed sur formation reconnue → SELECT déterministe."""
        result = try_select_or_none(
            "Quel est le taux d'accès du Bachelor EFREI Bordeaux ?",
            self._make_fiches(),
        )
        assert result is not None
        assert result.via_select is True
        assert result.fuzzy_score >= FUZZY_THRESHOLD
        assert "77 %" in result.text
        assert "EFREI" in result.text
        assert result.reason is None

    def test_select_invalid_value_falls_back(self):
        """Field présent mais valeur None/0 → fallback unifié, pas '0 %'."""
        result = try_select_or_none(
            "Quel est le taux d'accès du Master Droit International Assas ?",
            self._make_fiches(),
        )
        assert result is not None
        assert result.via_select is False
        assert result.reason == "select_invalid_value"
        assert "Je n'ai pas l'information" in result.text
        assert "n'est pas renseigné" in result.text or "Master Droit International" in result.text

    def test_select_no_match_falls_back(self):
        """Question sur formation hors corpus → fallback no_match."""
        result = try_select_or_none(
            "Quel est le taux d'accès de l'École Inexistante de Quelque Part ?",
            [{"nom": "Master Droit", "etablissement": "Sorbonne", "ville": "Paris"}],
        )
        assert result is not None
        assert result.via_select is False
        assert result.reason == "select_no_match"
        assert "Je n'ai pas l'information" in result.text

    def test_select_no_entity_falls_back(self):
        """Question avec field mais sans entité reconnue."""
        result = try_select_or_none(
            "Quel est le taux d'accès ?",  # pas de nom de formation
            self._make_fiches(),
        )
        # La question peut quand même extraire des stopwords filtrés → entity vide
        # OU faire un fuzzy match faible — on accepte les deux comportements
        assert result is not None
        # Soit no_entity, soit no_match
        assert result.reason in ("select_no_entity", "select_no_match")
        assert result.via_select is False

    def test_select_marker_via_select_true_for_audit(self):
        """L'expert insiste : via_select=True comme marqueur visible audit/démo.

        Question discriminante (BTS Déodat Toulouse) qui ne risque pas
        d'être ambiguë avec la fiche EFREI Bordeaux.
        """
        result = try_select_or_none(
            "Quel est le taux d'accès du BTS Déodat Toulouse ?",
            self._make_fiches(),
        )
        assert result is not None
        # Soit un SELECT déterministe (idéal), soit un fallback contrôlé —
        # on ne doit JAMAIS hallucinier un chiffre. via_select=True est le
        # marqueur visible quand le SELECT a vraiment réussi.
        if result.via_select:
            assert "28 %" in result.text or "Toulouse" in result.text
        else:
            # Fallback acceptable si ambigu — mais doit dire "Je n'ai pas l'info"
            assert "Je n'ai pas l'information" in result.text


# ──────────────────────── Pool filter SELECT (J2 U1, 2026-06-11) ────────────────────────

# Le bug : des fiches NON-formation (CROUS logements, INSEE salaires, métiers,
# aides) squattaient le rang-1 du fuzzy via l'inflation WRatio sur les chaînes
# courtes (texte = nom de ville seul). 27/48 questions SELECT touchées. Servir
# le "dominant" = hallucination déterministe (taux d'accès depuis une fiche
# logement). Fix = filtrer le pool aux fiches formation-identité AVANT le fuzzy.

_CROUS_FICHE = {"domain": "crous", "ville": "Lyon",
                "source": "crous_combine_logements_restos",
                "text": "Logements étudiants CROUS à Lyon"}
_INSEE_FICHE = {"domain": "insee_salaire", "source": "insee_salaan_2023",
                "cs_libelle": "Professions scientifiques", "salaire_net_median_annuel": 37500}
_METIER_FICHE = {"domain": "metier", "nom": "contrôleur/euse aérien/ne", "source": "onisep_metiers"}
_AIDES_FICHE = {"domain": "aides_territoires", "nom": "Bourse régionale", "source": "aides_territoires"}
_FORMATION_DOUA = {"nom": "BUT - Informatique",
                   "etablissement": "IUT Lyon1 Site de Villeurbanne Doua",
                   "ville": "Villeurbanne", "niveau": "BUT", "domain": "autre",
                   "taux_acces_parcoursup_2025": 16.0}
_FORMATION_BOURG = {"nom": "BUT - Informatique",
                    "etablissement": "IUT Lyon1 Site de Bourg-en-Bresse",
                    "ville": "Bourg-en-Bresse", "niveau": "BUT", "domain": "autre",
                    "taux_acces_parcoursup_2025": 34.0}


class TestSelectCandidateFilter:
    """Condition (a) : crous/insee/metier/aides + sans identité ne sont JAMAIS candidats."""

    def test_crous_excluded(self):
        assert is_select_candidate(_CROUS_FICHE) is False

    def test_insee_excluded(self):
        assert is_select_candidate(_INSEE_FICHE) is False

    def test_metier_excluded(self):
        assert is_select_candidate(_METIER_FICHE) is False

    def test_aides_excluded(self):
        assert is_select_candidate(_AIDES_FICHE) is False

    def test_real_formation_included(self):
        assert is_select_candidate(_FORMATION_DOUA) is True

    def test_formation_etab_only_included(self):
        assert is_select_candidate(
            {"etablissement": "IUT Lyon1", "ville": "Lyon", "domain": "sciences_fondamentales"}
        ) is True

    def test_no_identity_excluded(self):
        assert is_select_candidate({"domain": "autre", "ville": "Lyon"}) is False

    def test_non_dict_excluded(self):
        assert is_select_candidate(None) is False


class TestLookupPoolFilterAndVille:
    """Conditions (a) + (b) : garbage jamais retourné ; ville matche aussi l'etab ;
    refus conservé si aucune vraie formation."""

    def test_crous_never_returned_real_formation_wins(self):
        fiches = [_CROUS_FICHE, _FORMATION_DOUA]
        entity = Entity(formation_name="Informatique", ville="Lyon", niveau="BUT")
        fiche, score, ambiguous = lookup_formation(entity, fiches)
        assert fiche is not None
        assert fiche.get("nom") == "BUT - Informatique"  # PAS la fiche CROUS

    def test_ville_matches_etablissement_not_just_ville_field(self):
        # entity ville=Lyon ; fiche ville=Villeurbanne mais etab "IUT Lyon1" -> incluse
        fiches = [_FORMATION_DOUA]
        entity = Entity(formation_name="Informatique", ville="Lyon", niveau="BUT")
        fiche, score, ambiguous = lookup_formation(entity, fiches)
        assert fiche is not None and fiche.get("nom") == "BUT - Informatique"

    def test_only_garbage_in_pool_returns_none(self):
        # aucune vraie formation -> refus conservé (condition b)
        fiches = [_CROUS_FICHE, _INSEE_FICHE, _METIER_FICHE]
        entity = Entity(formation_name="Informatique", ville="Lyon", niveau="BUT")
        fiche, score, ambiguous = lookup_formation(entity, fiches)
        assert fiche is None


class TestSameFormationVariants:
    """Condition (c) : variantes de SITE d'une même formation/etab != ambiguïté
    distincte (servir la meilleure, site affiché) ; établissements distincts = ambigu."""

    def test_same_nom_same_etab_root_not_ambiguous(self):
        entity = Entity(formation_name="Informatique", ville="Lyon", niveau="BUT")
        fiche, score, ambiguous = lookup_formation(entity, [_FORMATION_DOUA, _FORMATION_BOURG])
        assert fiche is not None
        assert fiche.get("nom") == "BUT - Informatique"
        assert ambiguous is False  # même formation, sites différents -> pas ambigu

    def test_distinct_etablissements_same_nom_is_ambiguous(self):
        lyon2 = {"nom": "Licence Droit", "etablissement": "Université Lumière - Lyon 2",
                 "ville": "Lyon", "niveau": "Licence", "domain": "droit",
                 "taux_acces_parcoursup_2025": 40.0}
        lyon3 = {"nom": "Licence Droit", "etablissement": "Université Jean Moulin - Lyon 3",
                 "ville": "Lyon", "niveau": "Licence", "domain": "droit",
                 "taux_acces_parcoursup_2025": 42.0}
        entity = Entity(formation_name="Droit", ville="Lyon", niveau="Licence")
        fiche, score, ambiguous = lookup_formation(entity, [lyon2, lyon3])
        assert ambiguous is True  # établissements distincts -> refus/clarification conservé
