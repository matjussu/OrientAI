"""Critic loop anti-hallucination — Sprint 7 Action 3 levier 2.

Re-passe la réponse du LLM générateur à un fact-checker LLM (Mistral)
qui flag les chiffres non-sourcés et les retire ou les marque
`(estimation)`. Pattern : 2-pass generation pour réduire les
hallucinations résiduelles que le system prompt seul n'élimine pas.

## Diagnostic Sprint 6 (rappel verdict §3)

40% des claims unsupported = LLM hallucine (audit Claude Sonnet 4.5
n=20). Le critic loop attaque ce 40% en re-vérifiant chaque chiffre
avant de retourner la réponse à l'utilisateur·rice.

## Architecture

```
pipeline.answer(question) → response (raw)
        ↓
critic_loop.review(response, sources) → response_corrected
                                       (chiffres non-sourcés retirés
                                        ou marqués (estimation))
        ↓
return response_corrected
```

## Coût

1 call Mistral supplémentaire par query (~$0.02-$0.04). Pour le
bench triple-run 38q × 3 = 114 inférences supplémentaires =
~$2-$5 additionnel. Activable via flag, default OFF.

## Cohabitation avec StatFactChecker

Le critic loop et le StatFactChecker (`src/experimental/fact_checker.py`) sont
**complémentaires** :
- StatFactChecker : MESURE les hallucinations post-réponse
  (`{verified, verified_by_official_source, with_disclaimer, unsafe}`)
  pour le benchmark / verdict
- CriticLoop : CORRIGE les hallucinations en réécrivant la réponse
  pour la rendre plus sûre avant retour user

On peut combiner : critic_loop d'abord (corrige) puis fact_checker
ensuite (mesure ce qui reste).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from mistralai.client import Mistral


CRITIC_LOOP_MODEL = "mistral-small-latest"


CRITIC_LOOP_PROMPT = """Tu es un correcteur anti-hallucination spécialisé orientation.

## Mission

On te donne :
1. Une RÉPONSE produite par un LLM pour un·e étudiant·e
2. Les FICHES officielles utilisées comme source

Tu dois :
- Identifier chaque chiffre/statistique cité dans la RÉPONSE
- Pour chacun, vérifier s'il est présent dans les FICHES (ou dérivable
  d'une fourchette anti-hallu défensif `~X` + URL officielle)
- **Réécrire la RÉPONSE** en :
  - Préservant la structure et le ton
  - Préservant les chiffres VÉRIFIÉS dans les fiches
  - Retirant ou marquant `(estimation)` les chiffres NON-SOURCÉS
  - Conservant le format Plan A/B/C, listes, sections, etc.

## Règles strictes

- Ne JAMAIS inventer de nouveau chiffre
- Ne JAMAIS supprimer un chiffre VÉRIFIÉ même s'il semble étrange
- Préserver les marqueurs existants `(estimation)`, `(connaissance générale)`,
  `(non vérifié)`
- Pour les chiffres dans une fourchette anti-hallu défensif (ex
  fiche dit `~500€/an` + URL officielle), accepte le chiffre tel quel
  (citation fourchette OK)

## Schéma JSON strict de retour

```json
{
  "response_corrected": "<la réponse réécrite, en français complet>",
  "n_modifications": <int — nb de chiffres modifiés ou marqués>,
  "modifications_summary": "<bref résumé des changements faits>"
}
```

## Contraintes

- Ta réponse est UNIQUEMENT le JSON, pas de préambule
- Ne pas casser les listes / sections / structure markdown
- Si la RÉPONSE n'a aucun chiffre à vérifier, retourne :
  `{"response_corrected": <réponse identique>, "n_modifications": 0,
    "modifications_summary": "aucun chiffre à vérifier"}`
"""


@dataclass
class CriticReport:
    response_corrected: str
    response_original: str
    n_modifications: int = 0
    modifications_summary: str = ""
    error: Optional[str] = None


class CriticLoop:
    """Critic loop 1-pass : LLM relit la réponse et corrige les chiffres
    non-sourcés.

    Usage :
        critic = CriticLoop(client)
        report = critic.review(response, sources)
        cleaned = report.response_corrected
    """

    def __init__(
        self,
        client: Mistral,
        model: str = CRITIC_LOOP_MODEL,
        max_chars_fiches: int = 12000,
    ):
        self.client = client
        self.model = model
        self.max_chars_fiches = max_chars_fiches

    def _format_fiches(self, sources: list[dict]) -> str:
        """Sérialise top-K fiches pour le prompt critic loop."""
        lines = []
        for i, s in enumerate(sources[:10], 1):
            fiche = s.get("fiche") if "fiche" in s else s
            parts = [
                f"FICHE {i} :",
                f"  Nom : {fiche.get('nom', '')}",
            ]
            # Inclure le `text` complet si présent (cells multi-corpus
            # Sprint 6/7 contiennent souvent le text dense avec stats)
            text = fiche.get("text")
            if text:
                parts.append(f"  Contenu : {text[:600]}")
            else:
                # Fallback pour fiches formation classiques (formation.json)
                if fiche.get("etablissement"):
                    parts.append(f"  Établissement : {fiche['etablissement']}")
                if fiche.get("taux_acces_parcoursup_2025") is not None:
                    parts.append(f"  Taux d'accès : {fiche['taux_acces_parcoursup_2025']}%")
                if fiche.get("nombre_places") is not None:
                    parts.append(f"  Places : {fiche['nombre_places']}")
                detail = (fiche.get("detail") or "")[:300]
                if detail:
                    parts.append(f"  Détail : {detail}")
            lines.append("\n".join(parts))
        text = "\n\n".join(lines)
        if len(text) > self.max_chars_fiches:
            text = text[:self.max_chars_fiches] + "\n[... tronqué ...]"
        return text

    def review(
        self,
        response: str,
        sources: list[dict],
    ) -> CriticReport:
        """Re-passe la réponse au critic Mistral pour vérifier les chiffres.

        Args:
            response: réponse générée par le pipeline
            sources: top-K fiches retrievées (schéma pipeline)

        Returns:
            CriticReport avec response_corrected + n_modifications.
            En cas d'erreur API : response_corrected = response (passthrough).
        """
        report = CriticReport(
            response_corrected=response,
            response_original=response,
        )

        if not response.strip():
            return report

        fiches_text = self._format_fiches(sources)
        user_msg = f"""## RÉPONSE À VÉRIFIER

{response}

---

## FICHES SOURCES

{fiches_text}

Réécris la RÉPONSE en corrigeant les chiffres non-sourcés (marquer
`(estimation)` ou retirer). Réponds UNIQUEMENT en JSON.
"""

        try:
            result = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": CRITIC_LOOP_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=3500,
                response_format={"type": "json_object"},
            )
            raw = result.choices[0].message.content or ""
            parsed = json.loads(raw)
            corrected = parsed.get("response_corrected", "").strip()
            if corrected:
                report.response_corrected = corrected
            report.n_modifications = int(parsed.get("n_modifications", 0))
            report.modifications_summary = parsed.get("modifications_summary", "")
        except json.JSONDecodeError as e:
            report.error = f"JSON parse error: {e}"
            # Passthrough en cas d'erreur (préserve la réponse originale)
        except Exception as e:  # noqa: BLE001
            report.error = f"{type(e).__name__}: {e}"

        return report
