"""Fact-checker aval pour OrientIA (v4). — STATUT : EXPERIMENTAL, NON SERVI.

Déplacé de src/rag/ le 2026-07-16 (H1 lot 1.4, ordre 0905). Décision :
jamais câblé en prod depuis sa création, et le besoin qu'il visait (vérifier
les chiffres cités contre les fiches) est couvert MÉCANIQUEMENT par
`src/validator/citation_check.py` (déterministe, 0 coût, 0 latence,
0 variance) branché sur les deux chemins de serving. Un vérificateur
LLM (mistral-small) reste pertinent uniquement pour les claims QUALITATIFS
non chiffrés — cas d'usage Phase 3 avec le critic_loop, d'où experimental/
plutôt que suppression.

Objectif : après génération par `pipeline.answer()`, vérifier chaque
statistique chiffrée citée dans la réponse en la confrontant aux fiches
retrievées. Détecte les hallucinations "citations fabrication" résiduelles
que le system prompt v3 n'élimine pas (Q4, Q12, Q15 bench v3 : ~20%
hallucinations persistantes).

**Contrainte architecturale** : 100% Mistral stack (souveraineté INRIA
— ADR produit stratégique). PAS d'Anthropic Haiku ni OpenAI pour le
fact-check. Modèle : `mistral-small-latest` (bon ratio coût/capacité
structured extraction).

**Workflow pipeline** :

    answer, sources = pipeline.answer(question)
    report = fact_checker.verify(answer, sources)
    if report.stats_unsourced and policy.strict:
        answer = fact_checker.annotate(answer, report)

**Policy configurable** :
- `annotate` : remplace les stats non sourcées par "(non vérifié dans
  les sources)" — conservative, préserve la réponse
- `flag_only` : logue les hallucinations sans modifier la réponse
  (utile pour monitoring)
- `strict` : supprime les stats non sourcées — agressif, risque
  de casser la réponse sur les estimations légitimes

Par défaut : `annotate` (moins destructif).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from mistralai.client import Mistral
from src.rag.models import MISTRAL_SMALL


FACT_CHECK_MODEL = MISTRAL_SMALL


# --- Prompt fact-checker ---

FACT_CHECK_PROMPT = """Tu es un vérificateur de statistiques spécialisé dans l'orientation française.

## Ta mission

On te donne :
1. Une RÉPONSE produite par un LLM pour un·e étudiant·e
2. Les FICHES officielles utilisées comme source (extrait embedding retrievé)

Tu dois :
- Lister TOUS les chiffres/statistiques/pourcentages/salaires cités dans la RÉPONSE
- Pour chacun, vérifier s'il est présent dans au moins une FICHE (texte littéral, ou paraphrase proche, ou fourchette approximative)
- Retourner un JSON structuré (pas de texte hors JSON)

## Schéma JSON strict

```json
{
  "stats_extracted": [
    {
      "stat_text": "le texte exact dans la réponse (ex: '85% taux emploi')",
      "stat_value": "85",
      "stat_unit": "%",
      "context_in_response": "phrase courte qui entoure la stat",
      "is_sourced_in_fiches": true|false,
      "source_fiche_excerpt": "extrait fiche si sourcé, sinon null",
      "verdict": "verified" | "verified_by_official_source" | "unsourced_with_disclaimer" | "unsourced_unsafe"
    }
  ]
}
```

## Règles d'évaluation

- `verified` : stat présente textuellement (ou paraphrase très proche, ex 0.85 ↔ 85%) dans au moins une fiche. Récupère l'extrait concerné dans `source_fiche_excerpt`.
- `verified_by_official_source` : la stat est mentionnée dans une fiche **anti-hallu défensif** qui :
  - donne une fourchette approximative explicite (ex `~X-Y€`, `~500€/an`, `~17000-22000€`)
  - **ET** pointe vers une URL officielle (etudiant.gouv.fr, education.gouv.fr, insee.fr, statistiques.francetravail.fr, moncompteformation.gouv.fr, service-public.fr, agefiph.fr, etc.)
  - **ET** la valeur dans la réponse tombe dans la fourchette ou est cohérente avec elle
  → Compte comme verified (pattern de cell curated avec disclaimer "voir source pour montant exact").
- `unsourced_with_disclaimer` : stat PAS dans les fiches MAIS la réponse marque `(connaissance générale)` ou `(estimation)` ou `(non vérifié)` à proximité immédiate → OK, pas de hallucination, mais pas verified.
- `unsourced_unsafe` : stat PAS dans les fiches ET AUCUN disclaimer proche → **hallucination à flaguer**. Cite une source fabriquée type "CEREQ 2023", "DEPP", "FNEK", "APEC", "Welcome to the Jungle", "Glassdoor", "Syntec" sans que cette stat soit dans les fiches = `unsourced_unsafe`.

## Exemples

RÉPONSE : "Le taux d'emploi à 3 ans est de 85% (source Céreq Generation 2017)."
FICHE 1 : "Master Info Paris | Insertion pro (source Céreq, Generation 2017) : taux emploi 3 ans : 85%"
→ `verified`, source_fiche_excerpt = "Insertion pro (source Céreq, Generation 2017) : taux emploi 3 ans : 85%"

RÉPONSE : "Le PIB par habitant en Guyane est environ 17000€."
FICHE 1 : "DROM — Guyane (973) | PIB par habitant (€) : ~17000 (2022) ; France métro ~38000 | Sources officielles : insee.fr/fr/statistiques?geo=DEP-973"
→ `verified_by_official_source` (fourchette ~17000 + URL insee.fr officielle, valeur réponse cohérente)

RÉPONSE : "Le CPF crédite 500€/an pour les salariés."
FICHE 1 : "Financement — CPF | Montants approximatifs : 500€/an ; plafond 5000€ | Source officielle : moncompteformation.gouv.fr"
→ `verified_by_official_source` (montant approximatif 500€ + URL officielle moncompteformation.gouv.fr)

RÉPONSE : "Salaire ~2500€ net (connaissance générale)."
FICHES : aucune ne contient 2500€
→ `unsourced_with_disclaimer` (le disclaimer est présent)

RÉPONSE : "Le taux d'insertion est de 90% (source CEREQ 2023)."
FICHES : aucune ne contient 90% ni "CEREQ 2023"
→ `unsourced_unsafe` (hallucination : source fabriquée)

## Contraintes

- Ta réponse est UNIQUEMENT le JSON ci-dessus, pas de préambule.
- Si la RÉPONSE ne contient aucune stat chiffrée, retourne `{"stats_extracted": []}`.
- Un chiffre de calendrier (ex: "en 2025") ou de volumétrie évidente ("3 options") ne compte PAS comme stat à vérifier.
- Focus sur : pourcentages, taux, salaires, effectifs, ratios, montants de frais d'inscription, durées formations.
"""

# URL patterns reconnus comme "source officielle" pour le upgrade verdict
# `verified_by_official_source` (Sprint 7 Action 1 — anti-hallu défensif unmute).
OFFICIAL_SOURCE_URL_PATTERNS = (
    r"etudiant\.gouv\.fr",
    r"education\.gouv\.fr",
    r"insee\.fr",
    r"statistiques\.francetravail\.fr",
    r"francetravail\.fr",
    r"moncompteformation\.gouv\.fr",
    r"service-public\.fr",
    r"agefiph\.fr",
    r"fiphfp\.fr",
    r"transitionspro\.fr",
    r"vae\.gouv\.fr",
    r"travail-emploi\.gouv\.fr",
    r"caf\.fr",
    r"visale\.fr",
    r"afdas\.com",
    r"constructys\.fr",
    r"akto\.fr",
    r"ladom\.fr",
    r"le-sma\.com",
)

OFFICIAL_SOURCE_REGEX = re.compile(
    "|".join(OFFICIAL_SOURCE_URL_PATTERNS),
    re.IGNORECASE,
)


def _extract_has_official_source(source_excerpt: Optional[str]) -> bool:
    """Vrai si l'extrait fiche contient une URL officielle reconnue."""
    if not source_excerpt:
        return False
    return bool(OFFICIAL_SOURCE_REGEX.search(source_excerpt))


VERIFIED_VERDICTS: tuple[str, ...] = ("verified", "verified_by_official_source")
"""Verdicts comptés comme verified dans summary (n_verified).

Sprint 7 Action 1 : ajout de `verified_by_official_source` pour le pattern
anti-hallu défensif (chiffre approximatif `~X` + URL officielle inline).
Préserve la non-régression : `verified` reste comptabilisé identique."""


@dataclass
class StatVerification:
    stat_text: str
    stat_value: Optional[str] = None
    stat_unit: Optional[str] = None
    context_in_response: str = ""
    is_sourced_in_fiches: bool = False
    source_fiche_excerpt: Optional[str] = None
    # verdict ∈ {verified, verified_by_official_source, unsourced_with_disclaimer, unsourced_unsafe}
    verdict: str = "unsourced_unsafe"


@dataclass
class VerificationReport:
    stats_extracted: list[StatVerification] = field(default_factory=list)
    raw_response_mistral: str = ""
    error: Optional[str] = None

    @property
    def stats_verified(self) -> list[StatVerification]:
        """Stats verified (incluant verified_by_official_source Sprint 7).

        Note : pour distinguer les 2 sous-catégories, voir
        `stats_verified_strict` et `stats_verified_by_source` séparément.
        """
        return [s for s in self.stats_extracted if s.verdict in VERIFIED_VERDICTS]

    @property
    def stats_verified_strict(self) -> list[StatVerification]:
        """Stats verified avec match strict dans fiches (verdict == 'verified')."""
        return [s for s in self.stats_extracted if s.verdict == "verified"]

    @property
    def stats_verified_by_source(self) -> list[StatVerification]:
        """Stats verified par source officielle (anti-hallu défensif unmute Sprint 7)."""
        return [s for s in self.stats_extracted if s.verdict == "verified_by_official_source"]

    @property
    def stats_with_disclaimer(self) -> list[StatVerification]:
        return [s for s in self.stats_extracted if s.verdict == "unsourced_with_disclaimer"]

    @property
    def stats_hallucinated(self) -> list[StatVerification]:
        return [s for s in self.stats_extracted if s.verdict == "unsourced_unsafe"]

    @property
    def summary(self) -> dict:
        return {
            "n_stats_total": len(self.stats_extracted),
            "n_verified": len(self.stats_verified),  # Sprint 7 : strict + by_source
            "n_verified_strict": len(self.stats_verified_strict),
            "n_verified_by_source": len(self.stats_verified_by_source),
            "n_with_disclaimer": len(self.stats_with_disclaimer),
            "n_hallucinated": len(self.stats_hallucinated),
            "error": self.error,
        }


class StatFactChecker:
    """Vérificateur de statistiques aval (v4, 100% Mistral stack).

    Usage :
        checker = StatFactChecker(client)
        report = checker.verify(answer, sources)
        print(report.summary)
        annotated = checker.annotate(answer, report)  # optionnel
    """

    def __init__(
        self,
        client: Mistral,
        model: str = FACT_CHECK_MODEL,
        fiches_max_chars: int = 12000,  # limite tokens prompt
    ):
        self.client = client
        self.model = model
        self.fiches_max_chars = fiches_max_chars

    def _has_chiffre_to_check(self, response: str) -> bool:
        """Gate : la réponse contient-elle au moins un % / € / chiffre stat ?

        Économise les appels Mistral si la réponse n'a rien à vérifier.
        """
        patterns = [
            r"\d+\s?%",        # pourcentages
            r"\d+\s?€",         # montants €
            r"\d{2,3}\s?[km]€", # 45k€, 3M€
            r"\bsalaire.{0,40}\d",  # salaire ... 1800
            r"\btaux.{0,40}\d",     # taux ... 85
        ]
        for p in patterns:
            if re.search(p, response, re.IGNORECASE):
                return True
        return False

    def _format_fiches_for_checker(self, sources: list[dict]) -> str:
        """Sérialise les top-K fiches retrievées en texte pour le checker."""
        lines = []
        for i, s in enumerate(sources[:10], 1):
            fiche = s.get("fiche") if "fiche" in s else s
            # Inclure les champs stats-rich qui sont le cœur du fact-check
            parts = [
                f"FICHE {i} :",
                f"  Nom : {fiche.get('nom', '')}",
                f"  Établissement : {fiche.get('etablissement', '')}",
                f"  Niveau : {fiche.get('niveau')} | Phase : {fiche.get('phase')}",
            ]
            if fiche.get("taux_acces_parcoursup_2025") is not None:
                parts.append(f"  Taux d'accès Parcoursup : {fiche['taux_acces_parcoursup_2025']}%")
            if fiche.get("nombre_places") is not None:
                parts.append(f"  Places : {fiche['nombre_places']}")
            if fiche.get("taux_admission") is not None:
                parts.append(f"  Taux admission MonMaster : {fiche['taux_admission']}")
            if fiche.get("n_candidats_pp") is not None:
                parts.append(f"  Candidats PP : {fiche['n_candidats_pp']}")
            if fiche.get("n_acceptes_total") is not None:
                parts.append(f"  Acceptés total : {fiche['n_acceptes_total']}")
            ip = fiche.get("insertion_pro")
            if isinstance(ip, dict):
                parts.append(f"  Insertion pro : {json.dumps(ip, ensure_ascii=False)}")
            detail = (fiche.get("detail") or "")[:400]
            if detail:
                parts.append(f"  Détail : {detail}")
            lines.append("\n".join(parts))
        text = "\n\n".join(lines)
        # Cap prompt size
        if len(text) > self.fiches_max_chars:
            text = text[: self.fiches_max_chars] + "\n[... tronqué ...]"
        return text

    def verify(
        self,
        response: str,
        sources: list[dict],
        skip_if_no_stats: bool = True,
    ) -> VerificationReport:
        """Vérifie les stats de `response` contre les `sources` retrievées.

        Args:
            response: texte généré par `pipeline.answer()`
            sources: liste des fiches retrievées top-K (schéma pipeline)
            skip_if_no_stats: si True, skip le call Mistral si aucun chiffre
                détecté par regex simple → retourne rapport vide.

        Returns:
            VerificationReport avec liste des stats + verdicts
        """
        report = VerificationReport()

        if skip_if_no_stats and not self._has_chiffre_to_check(response):
            return report

        fiches_text = self._format_fiches_for_checker(sources)
        user_msg = f"""## RÉPONSE À VÉRIFIER

{response}

---

## FICHES SOURCES (top-{min(len(sources), 10)} retrievées)

{fiches_text}
"""

        try:
            result = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": FACT_CHECK_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,  # déterministe pour reproductibilité
                max_tokens=3000,
                response_format={"type": "json_object"},
            )
            raw = result.choices[0].message.content or ""
            report.raw_response_mistral = raw
            parsed = json.loads(raw)
            for s in parsed.get("stats_extracted", []):
                report.stats_extracted.append(
                    StatVerification(
                        stat_text=s.get("stat_text", ""),
                        stat_value=s.get("stat_value"),
                        stat_unit=s.get("stat_unit"),
                        context_in_response=s.get("context_in_response", ""),
                        is_sourced_in_fiches=bool(s.get("is_sourced_in_fiches", False)),
                        source_fiche_excerpt=s.get("source_fiche_excerpt"),
                        verdict=s.get("verdict", "unsourced_unsafe"),
                    )
                )
        except json.JSONDecodeError as e:
            report.error = f"JSON parse error: {e}. Raw: {raw[:200]}"
        except Exception as e:  # noqa: BLE001
            report.error = f"{type(e).__name__}: {e}"

        return report

    def annotate(self, response: str, report: VerificationReport) -> str:
        """Annotate la réponse en ajoutant `(non vérifié dans les sources)`
        en fin de chaque phrase contenant une stat hallucinée.

        Stratégie non-destructive : on préserve la réponse, on ajoute
        juste un flag lisible. L'utilisateur voit la réponse + les
        annotations de doute.
        """
        if not report.stats_hallucinated:
            return response
        annotated = response
        for stat in report.stats_hallucinated:
            if stat.stat_text and stat.stat_text in annotated:
                replacement = f"{stat.stat_text} *(non vérifié dans les sources)*"
                annotated = annotated.replace(stat.stat_text, replacement, 1)
        return annotated
