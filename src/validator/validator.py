"""Orchestrateur Validator v1 (couches 1 + 2 combinées).

Expose `Validator.validate(answer) -> ValidatorResult`.
Couche 3 fallback LLM (Mistral Small souverain) reportée v2.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.validator.rules import Severity, Violation, apply_rules
from src.validator.citation_check import CitationMismatch, check_citations
from src.validator.corpus_check import CorpusWarning, check_claims_in_corpus
from src.validator.layer3 import Layer3Validator, Layer3Warning
from src.validator.presence import PresenceWarning, check_presence

from src.rag.fact_card import FactCard


@dataclass
class ValidatorResult:
    honesty_score: float  # 0.0 (pire) .. 1.0 (parfait)
    rule_violations: list[Violation] = field(default_factory=list)
    corpus_warnings: list[CorpusWarning] = field(default_factory=list)
    layer3_warnings: list[Layer3Warning] = field(default_factory=list)
    presence_warnings: list[PresenceWarning] = field(default_factory=list)
    # H1 lot 1.2 — chiffres attribués à un tag [source SX] absents de la
    # FactCard SX vue par le LLM (check déterministe, cf citation_check).
    citation_mismatches: list[CitationMismatch] = field(default_factory=list)
    flagged: bool = False  # True si >= 1 BLOCKING, corpus_warning ou citation_mismatch

    def summary(self) -> str:
        """Résumé lisible pour log / debug."""
        lines = [
            f"honesty_score={self.honesty_score:.2f} "
            f"flagged={self.flagged} "
            f"rules={len(self.rule_violations)} "
            f"corpus={len(self.corpus_warnings)} "
            f"layer3={len(self.layer3_warnings)}"
        ]
        for v in self.rule_violations:
            lines.append(f"  [{v.severity.value}] {v.rule_id}: {v.matched_text!r}")
        for w in self.corpus_warnings:
            lines.append(
                f"  [corpus] {w.claim!r} (sim={w.similarity}, "
                f"closest={w.closest_match!r})"
            )
        for lw in self.layer3_warnings:
            lines.append(f"  [layer3] {lw.claim!r} — {lw.reason}")
        return "\n".join(lines)


# Pondération du score honnêteté
_SCORE_PENALTIES: dict[Severity, float] = {
    Severity.BLOCKING: 0.15,
    Severity.WARNING: 0.05,
    Severity.INFO: 0.02,
}
_CORPUS_PENALTY = 0.10
_LAYER3_PENALTY = 0.05  # warning layer3 = mêmme pondération que WARN rule


# Allowlist des intents qui justifient un appel layer3 LLM Mistral Small
# (~$0.001/call, +2-4s latence). Skip layer3 sur les intents purement
# textuels (passerelles/decouverte/conceptual/general) où :
#   - les hallus layer3-detectables (chiffres fabriqués, distances, coûts
#     privés sous-estimés) sont rares,
#   - le coût LLM n'est pas justifié.
# Activé en Sprint refonte (2026-05-05) post-forensic du bench
# audit_post_chantiers révélant que layer3 désactivé masque les hallus
# textuelles type "label CTI bac+3" / "à 2h en train de Toulouse".
# Comportement quand `intent=None` : run layer3 si dispo (legacy safe default).
LAYER3_INTENTS: frozenset[str] = frozenset({
    "factual_pointed",  # questions chiffrées sur école nommée
    "geographic",       # multi-filtres géographiques (ville/région)
    "comparaison",      # comparaison entre formations
    "realisme",         # projection accessibilité (% mentions/prestige)
})


class Validator:
    """Orchestrateur règles + corpus-check + (optionnel) couche 3 LLM souverain.

    Usage simple (couches 1+2 uniquement) :
        v = Validator(fiches=corpus)
        result = v.validate(answer_text)

    Usage complet V2 avec couche 3 Mistral Small :
        from src.validator.layer3 import Layer3Validator
        layer3 = Layer3Validator(client=mistral_client)
        v = Validator(fiches=corpus, layer3=layer3)
        result = v.validate(answer_text)
    """

    def __init__(
        self,
        fiches: list[dict],
        corpus_sim_threshold: float = 0.30,
        layer3: Layer3Validator | None = None,
    ):
        self.fiches = fiches
        self.corpus_sim_threshold = corpus_sim_threshold
        self.layer3 = layer3

    def validate(
        self,
        answer: str,
        intent: str | None = None,
        fact_cards: list[FactCard] | None = None,
    ) -> ValidatorResult:
        """Valide une réponse pipeline.

        Args:
            answer: réponse texte du générateur
            intent: intent classé (`factual_pointed`, `passerelles`, etc.) —
                si fourni, gate l'appel layer3 LLM via `LAYER3_INTENTS`
                allowlist. Si None : comportement legacy (run layer3 si dispo).
            fact_cards: FactCards S1..SN telles que vues par le LLM (même
                numérotation que la génération). Si fournies, active le check
                déterministe chiffre-vs-source-citée (H1 lot 1.2) : tout
                chiffre attribué à [source SX] absent de la carte SX flagge
                la réponse (verdict INFIDELE côté API).
        """
        rule_violations = apply_rules(answer)
        corpus_warnings = check_claims_in_corpus(
            answer, self.fiches, threshold=self.corpus_sim_threshold
        )
        # Couche 3 optionnelle (V2). Skip si :
        #  - layer3 non instancié (mode déterministe pur), OU
        #  - intent fourni ET hors LAYER3_INTENTS (économie coût/latence).
        # Si client instancié sans intent : run layer3 (legacy safe default).
        layer3_warnings: list[Layer3Warning] = []
        if self.layer3 is not None:
            if intent is None or intent in LAYER3_INTENTS:
                layer3_warnings = self.layer3.check(answer)
        # V4 : règles de PRÉSENCE — flag si topic sans info obligatoire
        presence_warnings = check_presence(answer)

        # H1 lot 1.2 — check déterministe chiffre-vs-source-citée. Actif
        # seulement si l'appelant fournit les FactCards vues par le LLM.
        citation_mismatches: list[CitationMismatch] = []
        if fact_cards:
            citation_mismatches = check_citations(answer, fact_cards)

        honesty_score = self._compute_honesty(
            rule_violations, corpus_warnings, layer3_warnings, presence_warnings,
            citation_mismatches,
        )
        flagged = (
            any(v.severity == Severity.BLOCKING for v in rule_violations)
            or len(corpus_warnings) > 0
            or len(citation_mismatches) > 0
        )
        # Couche 3 : n'escalade pas à `flagged` en v2 (= WARN severity
        # contribuant juste au score + β Warn footer via policy). Changer
        # le mapping si v3 veut bloquer sur layer3.

        return ValidatorResult(
            honesty_score=honesty_score,
            rule_violations=rule_violations,
            corpus_warnings=corpus_warnings,
            layer3_warnings=layer3_warnings,
            presence_warnings=presence_warnings,
            citation_mismatches=citation_mismatches,
            flagged=flagged,
        )

    @staticmethod
    def _compute_honesty(
        violations: list[Violation],
        corpus_warnings: list[CorpusWarning],
        layer3_warnings: list[Layer3Warning] | None = None,
        presence_warnings: list[PresenceWarning] | None = None,
        citation_mismatches: list[CitationMismatch] | None = None,
    ) -> float:
        score = 1.0
        for v in violations:
            score -= _SCORE_PENALTIES.get(v.severity, 0.05)
        score -= _CORPUS_PENALTY * len(corpus_warnings)
        if layer3_warnings:
            score -= _LAYER3_PENALTY * len(layer3_warnings)
        if presence_warnings:
            score -= 0.05 * len(presence_warnings)
        if citation_mismatches:
            # Même gravité qu'un corpus_warning : un chiffre mal attribué à
            # sa source casse la traçabilité autant qu'un claim non source.
            score -= _CORPUS_PENALTY * len(citation_mismatches)
        return max(0.0, min(1.0, score))


def extract_failed_claims(result: ValidatorResult) -> list[str]:
    """Extrait les claims échoués pour le retry-with-hint loop (chantier 1.B).

    Récupère les `matched_text` / `claim` des violations et warnings qui
    indiquent qu'une affirmation factuelle de la réponse n'est pas sourcée
    ou contredit les sources. Retourne une liste de strings courts utilisable
    pour construire un hint block réinjecté dans le contexte au tour 2.

    Priorité :
      1. corpus_warnings (claim explicite vs corpus → fort signal d'invention)
      2. layer3_warnings (LLM-judge dit infidèle)
      3. rule_violations BLOCKING (terminologie obsolète, hallu connue)
      4. presence_warnings (info obligatoire manquante)

    Returns:
        list[str] des claims problématiques (max ~10 pour ne pas saturer le hint).
        Retourne [] si la réponse est propre (aucune action retry nécessaire).
    """
    claims: list[str] = []

    # 1. Corpus warnings — priorité haute (claim absent du corpus = invention)
    for w in result.corpus_warnings:
        claim_text = (w.claim or "").strip()
        if claim_text and claim_text not in claims:
            claims.append(claim_text)

    # 2. Layer3 warnings — LLM-judge a flagué
    for lw in result.layer3_warnings:
        claim_text = (lw.claim or "").strip()
        if claim_text and claim_text not in claims:
            claims.append(claim_text)

    # 3. Rule violations BLOCKING (terminologie obsolète notamment)
    for v in result.rule_violations:
        if v.severity == Severity.BLOCKING:
            matched = (v.matched_text or "").strip()
            if matched and matched not in claims:
                claims.append(f"{matched} ({v.rule_id})")

    # 4. Presence warnings — infos manquantes
    for pw in result.presence_warnings:
        # PresenceWarning a `missing_pattern_label` et `message`
        label = getattr(pw, "missing_pattern_label", None) or ""
        if label and label not in claims:
            claims.append(f"info manquante : {label}")

    # Cap à 10 pour ne pas saturer le hint (le LLM décroche au-delà).
    return claims[:10]


def format_hint_block(failed_claims: list[str]) -> str:
    """Construit le hint block à réinjecter dans le user prompt au tour 2.

    Pattern : liste les claims problématiques + instruction explicite de les
    retirer ou de basculer sur le fallback unifié si l'info manque.

    Args:
        failed_claims: output de `extract_failed_claims()`.

    Returns:
        String formatée pour append au user prompt. Empty string si pas de claims.
    """
    if not failed_claims:
        return ""

    lines = [
        "",
        "─── HINT RETRY (chantier 1.B) — claims à corriger ───",
        "",
        "Ta réponse précédente contenait des affirmations factuelles non "
        "sourcées dans les fiches retrievées. Reformule en :",
        "  - retirant les claims listés ci-dessous (ou en les remplaçant par "
        "une formulation qualitative non précise),",
        "  - OU en utilisant le format de fallback unifié « Je n'ai pas "
        "l'information [précise sur X] dans mes sources vérifiées » si l'info "
        "manque vraiment.",
        "",
        "Claims problématiques :",
    ]
    for i, claim in enumerate(failed_claims, 1):
        # Tronquer les claims très longs pour clarté
        snippet = claim if len(claim) <= 200 else claim[:197] + "..."
        lines.append(f"  {i}. {snippet}")
    lines.append("")
    lines.append("Ne reproduis PAS ces claims dans ta nouvelle réponse.")
    lines.append("─────────────────────────────────────────────────────")
    return "\n".join(lines)
