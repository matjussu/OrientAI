"""Tests src/rag/scope_classifier.py — gating amont pipeline.

Tests :
- Pré-filter regex urgent (signaux forts non-ambigus)
- Mode dégradé sans LLM (default in_scope safe)
- Réponses pré-écrites cohérentes
- Format JSON parsing robuste
- Mock LLM Mistral pour les 3 verdicts
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.rag.scope_classifier import (
    GREETING_RESPONSE,
    IDENTITY_RESPONSE,
    OUT_OF_SCOPE_RESPONSE,
    URGENT_RESPONSE,
    ScopeClassifier,
    ScopeResult,
    detect_greeting_signals_regex,
    detect_identity_signals_regex,
    detect_urgent_signals_regex,
)


# ─────────────── Regex urgent pré-filter ───────────────


class TestRegexUrgent:
    def test_suicide_explicit_matched(self):
        assert detect_urgent_signals_regex("je veux me suicider")
        assert detect_urgent_signals_regex("j'ai des pensées suicidaires")
        assert detect_urgent_signals_regex("je vais en finir avec la vie")

    def test_violence_explicit_matched(self):
        assert detect_urgent_signals_regex("je suis battu par mon père")
        assert detect_urgent_signals_regex("violences conjugales depuis 2 ans")

    def test_disparaitre_pour_de_bon_matched(self):
        assert detect_urgent_signals_regex("je veux disparaître pour de bon")

    def test_normal_question_not_matched(self):
        assert not detect_urgent_signals_regex("je veux faire un BTS info")
        assert not detect_urgent_signals_regex("comment intégrer Sciences Po ?")
        assert not detect_urgent_signals_regex("j'ai 11 de moyenne pour HEC ?")

    def test_indirect_distress_NOT_caught_by_regex(self):
        """Les formulations indirectes type 'à quoi bon' doivent passer
        par le LLM, pas le regex (qui est conservateur sur les signaux clairs)."""
        assert not detect_urgent_signals_regex("à quoi bon faire des études")
        assert not detect_urgent_signals_regex("j'en peux plus de l'école")


class TestRegexUrgentDetresseIndirecte:
    """Filet déterministe détresse vitale indirecte (ordre #137, R07/R06).

    Additif : escalade GARANTIE sur épuisement/rupture/effondrement de sens,
    calibré pour NE PAS attraper le stress d'orientation NORMAL (R12). Vérifié
    0 sur-refus sur les 474 questions non-détresse du banc 497q."""

    def test_r07_markers_caught(self):
        assert detect_urgent_signals_regex("je suis epuise, je tiens plus, je sens que je craque")
        assert detect_urgent_signals_regex("je ne tiens plus")
        assert detect_urgent_signals_regex("je craque, tout va mal")

    def test_r06_markers_caught(self):
        assert detect_urgent_signals_regex("je me sens nul, je sers a rien")
        assert detect_urgent_signals_regex("je sers à rien")
        assert detect_urgent_signals_regex("rien n'a de sens en ce moment")
        assert detect_urgent_signals_regex("rien n'a plus de sens")
        assert detect_urgent_signals_regex("je me sens inutile")
        assert detect_urgent_signals_regex("je vais rater ma vie")

    def test_normal_orientation_stress_NOT_caught(self):
        # R12 et stress Parcoursup normal : du coeur de métier, JAMAIS urgent
        # par regex (le LLM les classe in_scope).
        assert not detect_urgent_signals_regex(
            "ca me stresse enormement, j'ai peur de faire le mauvais choix et "
            "de me tromper de voie, ca me prend la tete et je dors mal"
        )
        assert not detect_urgent_signals_regex("j'angoisse à l'idée de mal choisir mon orientation")
        assert not detect_urgent_signals_regex("je stresse pour Parcoursup")

    def test_craque_pour_is_positive_not_distress(self):
        # « je craque pour cette formation » = enthousiasme, PAS détresse.
        assert not detect_urgent_signals_regex("je craque pour le BUT informatique")
        assert not detect_urgent_signals_regex("je craque complètement pour Sciences Po")

    def test_je_suis_nul_en_matiere_not_caught(self):
        # « je suis nul en maths » = auto-éval scolaire normale, pas « je me sens nul ».
        assert not detect_urgent_signals_regex("je suis nul en maths, est-ce grave pour une prépa ?")

    def test_latent_false_positives_guardrailed(self):
        # Faux-positifs LATENTS (audit Jarvis pré-merge, absents du banc 497q donc
        # invisibles au gate 0/474) : tournures bénignes hyper-courantes en
        # orientation qui NE DOIVENT PAS escalader la crise.
        # « tenir à/au/aux X » = préférence, pas « je tiens plus » (rupture).
        assert not detect_urgent_signals_regex(
            "je tiens plus à la pratique qu'à la théorie, quelle formation ?"
        )
        assert not detect_urgent_signals_regex("je tiens plus aux maths qu'à la physique")
        assert not detect_urgent_signals_regex("je tiens plus au concret")
        # « nul EN [matière] » = auto-dépréciation scolaire, pas « je me sens nul ».
        assert not detect_urgent_signals_regex("je me sens nul en maths, c'est éliminatoire pour une prépa ?")
        # ... mais la détresse standalone reste bien attrapée (non-régression du fix).
        assert detect_urgent_signals_regex("je tiens plus, chaque jour est trop dur")
        assert detect_urgent_signals_regex("je me sens nul, je sers a rien")


# ─────────────── ScopeClassifier sans LLM (mode dégradé) ───────────────


class TestScopeClassifierWithoutClient:
    def test_urgent_regex_caught_without_llm(self):
        clf = ScopeClassifier(client=None)
        res = clf.classify("je veux me suicider")
        assert res.label == "urgent"
        assert res.via == "regex_urgent"
        assert res.pre_written_response == URGENT_RESPONSE

    def test_no_llm_default_in_scope(self):
        """Sans LLM, défaut conservateur = in_scope (laisse le pipeline gérer)."""
        clf = ScopeClassifier(client=None)
        res = clf.classify("quelle est la météo demain ?")
        assert res.label == "in_scope"
        assert res.via == "fallback_in_scope"
        assert res.pre_written_response is None

    def test_empty_question_out_of_scope(self):
        clf = ScopeClassifier(client=None)
        res = clf.classify("")
        assert res.label == "out_of_scope"
        assert res.pre_written_response == OUT_OF_SCOPE_RESPONSE


# ─────────────── ScopeClassifier avec LLM mocké ───────────────


def _mock_llm_returning(label: str, reason: str = "test"):
    """Construit un client Mistral mocké qui retourne le label voulu."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(
        content=json.dumps({"label": label, "reason": reason})
    ))]
    client.chat.complete.return_value = response
    return client


class TestScopeClassifierWithLLM:
    def test_in_scope_passes_through(self):
        client = _mock_llm_returning("in_scope", "orientation question")
        clf = ScopeClassifier(client=client)
        res = clf.classify("Quelles écoles d'ingénieur en Bretagne ?")
        assert res.label == "in_scope"
        assert res.via == "llm"
        assert res.pre_written_response is None

    def test_out_of_scope_returns_pre_written(self):
        client = _mock_llm_returning("out_of_scope", "cooking")
        clf = ScopeClassifier(client=client)
        res = clf.classify("recette de gâteau au chocolat ?")
        assert res.label == "out_of_scope"
        assert res.via == "llm"
        assert res.pre_written_response == OUT_OF_SCOPE_RESPONSE

    def test_urgent_via_llm_indirect(self):
        """LLM rattrape les formulations indirectes type 'j'en peux plus'."""
        client = _mock_llm_returning("urgent", "detresse psychologique")
        clf = ScopeClassifier(client=client)
        res = clf.classify("j'en peux plus, à quoi bon continuer")
        assert res.label == "urgent"
        assert res.via == "llm"
        assert res.pre_written_response == URGENT_RESPONSE

    def test_llm_error_falls_back_to_in_scope(self):
        """LLM API échoue → default in_scope (pipeline gère honnêtement)."""
        client = MagicMock()
        client.chat.complete.side_effect = RuntimeError("API down")
        clf = ScopeClassifier(client=client)
        res = clf.classify("quelle formation choisir ?")
        assert res.label == "in_scope"
        assert res.via == "fallback_in_scope"

    def test_llm_returns_invalid_label_falls_back(self):
        client = _mock_llm_returning("garbage_label", "test")
        clf = ScopeClassifier(client=client)
        res = clf.classify("test ?")
        assert res.label == "in_scope"  # safe default

    def test_llm_returns_invalid_json_falls_back(self):
        client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="not json at all"))]
        client.chat.complete.return_value = response
        clf = ScopeClassifier(client=client)
        res = clf.classify("test ?")
        assert res.label == "in_scope"

    def test_regex_urgent_short_circuits_before_llm(self):
        """Si regex match urgent, on ne fait PAS appel LLM (gain latency)."""
        client = MagicMock()
        clf = ScopeClassifier(client=client)
        res = clf.classify("je veux me suicider")
        assert res.label == "urgent"
        assert res.via == "regex_urgent"
        client.chat.complete.assert_not_called()


# ─────────────── Réponses pré-écrites ───────────────


class TestPreWrittenResponses:
    def test_urgent_response_lists_3114(self):
        assert "3114" in URGENT_RESPONSE

    def test_urgent_response_lists_3919(self):
        assert "3919" in URGENT_RESPONSE

    def test_urgent_response_lists_119(self):
        assert "119" in URGENT_RESPONSE

    def test_urgent_response_labels_3018_as_harcelement(self):
        # Régression ordre 2026-07-15 : le 3018 est le numéro harcèlement
        # scolaire / cyberharcèlement, il était étiqueté "SOS Amitié" à tort.
        line_3018 = next(l for l in URGENT_RESPONSE.splitlines() if "3018" in l)
        assert "arcèlement" in line_3018
        assert "SOS Amitié" not in line_3018

    def test_urgent_response_lists_sos_amitie_real_number(self):
        line_sos = next(l for l in URGENT_RESPONSE.splitlines() if "SOS Amitié" in l)
        assert "09 72 39 40 50" in line_sos

    def test_urgent_response_recognizes_distress(self):
        assert "détresse" in URGENT_RESPONSE.lower()

    def test_out_of_scope_response_redirects_to_orientation(self):
        assert "orientation" in OUT_OF_SCOPE_RESPONSE.lower()
        assert "post-bac" in OUT_OF_SCOPE_RESPONSE.lower()

    def test_out_of_scope_gives_examples(self):
        """Pour aider l'utilisateur à reformuler, on donne 3 exemples concrets."""
        assert OUT_OF_SCOPE_RESPONSE.count("«") >= 3


# ─────────────── Identité ("qui es-tu", "es-tu une IA") ───────────────


class TestRegexIdentity:
    def test_tu_es_qui_matched(self):
        assert detect_identity_signals_regex("Tu es qui ?")

    def test_qui_es_tu_matched(self):
        assert detect_identity_signals_regex("Qui es-tu ?")
        assert detect_identity_signals_regex("qui es tu")

    def test_qui_est_tu_typo_matched(self):
        """Typo fréquente "qui est tu" (au lieu de "qui es tu") doit matcher."""
        assert detect_identity_signals_regex("Qui est tu ?")
        assert detect_identity_signals_regex("qui est-tu")

    def test_identity_with_greeting_prefix_matched(self):
        """"Salut ! Qui est tu ?" doit matcher identity (pas greeting seul)."""
        assert detect_identity_signals_regex("Salut ! Qui est tu ?")
        assert detect_identity_signals_regex("Bonjour, qui es-tu ?")

    def test_es_tu_une_ia_matched(self):
        assert detect_identity_signals_regex("Es-tu une IA ?")
        assert detect_identity_signals_regex("es tu une IA")
        assert detect_identity_signals_regex("Tu es une intelligence artificielle ?")

    def test_es_tu_humain_matched(self):
        assert detect_identity_signals_regex("Es-tu un humain ?")
        assert detect_identity_signals_regex("Es-tu un robot ?")
        assert detect_identity_signals_regex("Tu es un chatbot ?")

    def test_presente_toi_matched(self):
        assert detect_identity_signals_regex("Présente-toi")
        assert detect_identity_signals_regex("présente toi")

    def test_ton_nom_matched(self):
        assert detect_identity_signals_regex("Comment tu t'appelles ?")
        assert detect_identity_signals_regex("C'est quoi ton nom ?")

    def test_normal_orientation_question_not_matched(self):
        """Pas de faux positif sur des questions d'orientation."""
        assert not detect_identity_signals_regex("Quelles écoles d'ingénieur en cyber ?")
        assert not detect_identity_signals_regex("Je suis en terminale, j'hésite")
        assert not detect_identity_signals_regex("C'est quoi un BUT informatique ?")


class TestIdentityShortCircuit:
    def test_identity_short_circuits_before_urgent(self):
        """'qui es-tu' ne doit pas tomber dans urgent malgré tout."""
        clf = ScopeClassifier(client=None)
        result = clf.classify("Qui es-tu ?")
        assert result.label == "identity"
        assert result.via == "regex_identity"
        assert result.pre_written_response == IDENTITY_RESPONSE

    def test_identity_works_without_llm(self):
        """Le pré-filter regex marche sans LLM (gratuit, déterministe)."""
        clf = ScopeClassifier(client=None)
        for q in ["Tu es qui ?", "Es-tu une IA ?", "Présente-toi"]:
            result = clf.classify(q)
            assert result.label == "identity", f"Failed for: {q}"

    def test_identity_response_mentions_orientia(self):
        assert "OrientAI" in IDENTITY_RESPONSE

    def test_identity_response_mentions_data_sources(self):
        """L'identité doit citer les sources publiques."""
        assert "Parcoursup" in IDENTITY_RESPONSE
        assert "ONISEP" in IDENTITY_RESPONSE

    def test_identity_response_does_not_start_with_oui(self):
        """Une question ouverte ("Qui es-tu ?") ne doit pas se voir répondre
        par "Oui, …" — la réponse doit fonctionner pour les deux types
        (oui/non type "Es-tu une IA ?" ET ouvert type "Qui es-tu ?")."""
        assert not IDENTITY_RESPONSE.lstrip().lower().startswith("oui,")
        assert not IDENTITY_RESPONSE.lstrip().lower().startswith("**oui,")


# ─────────────── Greeting (bonjour, salut, hey…) ───────────────


class TestRegexGreeting:
    def test_bonjour_matched(self):
        assert detect_greeting_signals_regex("Bonjour !")
        assert detect_greeting_signals_regex("bonjour")
        assert detect_greeting_signals_regex("Bonjour")

    def test_salut_matched(self):
        assert detect_greeting_signals_regex("Salut !")
        assert detect_greeting_signals_regex("salut")
        assert detect_greeting_signals_regex("Slt")

    def test_hello_hey_matched(self):
        assert detect_greeting_signals_regex("Hello")
        assert detect_greeting_signals_regex("Hey !")
        assert detect_greeting_signals_regex("Hi")
        assert detect_greeting_signals_regex("Coucou")

    def test_greeting_with_smalltalk_matched(self):
        """Greeting + small talk ("ça va", "comment vas-tu") doit matcher."""
        assert detect_greeting_signals_regex("Bonjour, ça va ?")
        assert detect_greeting_signals_regex("Salut comment vas-tu ?")
        assert detect_greeting_signals_regex("Hey, tout va bien ?")

    def test_greeting_followed_by_real_question_not_matched(self):
        """"Salut, je suis en terminale…" ne doit PAS matcher (vraie question
        derrière, on traite la question normalement)."""
        assert not detect_greeting_signals_regex("Salut, je suis en terminale, j'hésite")
        assert not detect_greeting_signals_regex("Bonjour, quelles écoles cyber ?")

    def test_orientation_question_not_matched(self):
        """Pas de faux positif sur les questions d'orientation."""
        assert not detect_greeting_signals_regex("Quelles écoles cyber en Bretagne ?")
        assert not detect_greeting_signals_regex("C'est quoi un BUT informatique ?")


class TestGreetingShortCircuit:
    def test_bonjour_short_circuits(self):
        clf = ScopeClassifier(client=None)
        result = clf.classify("Bonjour !")
        assert result.label == "greeting"
        assert result.via == "regex_greeting"
        assert result.pre_written_response == GREETING_RESPONSE

    def test_greeting_response_invites_question(self):
        """La réponse greeting doit inviter à poser une question d'orientation."""
        assert "OrientAI" in GREETING_RESPONSE
        assert "orientation" in GREETING_RESPONSE.lower()
        # Au moins un exemple concret pour aider l'utilisateur
        assert "«" in GREETING_RESPONSE
