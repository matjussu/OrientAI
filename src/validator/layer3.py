"""Couche 3 Validator — fallback LLM souverain Mistral Small (V2).

Complémente les couches 1 (rules) + 2 (corpus-check) en cherchant les
hallucinations **subtiles non-règle-based** : chiffres fabriqués, coûts
sous-estimés, prestige marketing, claims non catchables par regex.

Stratégie :
- Appel Mistral Small (`mistral-small-latest`) avec prompt structuré
- Output JSON : liste de claims factuels jugés douteux + raison
- Budget cible <$0.001/call (input ~400 tokens / output ~200 tokens)
- Timeout 5s, graceful fallback si API down (return [] vide)

Souveraineté : Mistral Small est hébergé en France (cohérent V2 déployable
prod). **Évite Claude / GPT-4o en production** pour préserver narrative.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from src.rag.models import MISTRAL_SMALL


LAYER3_SYSTEM_PROMPT = """Tu es un assistant d'audit factuel spécialisé dans l'orientation scolaire \
et professionnelle française. On te donne la réponse d'un autre système d'orientation \
(destinée à un lycéen ou étudiant) et tu dois identifier **les affirmations factuelles \
douteuses ou non vérifiables** qui pourraient induire en erreur.

Types d'hallucinations à repérer (focus non-règle-based, car les règles \
lexicales sont déjà appliquées en amont) :
- **Chiffres fabriqués** : taux d'accès, salaires, places, pourcentages d'admis \
qui ne sonnent pas crédibles ou sont incohérents
- **Coûts privés sous-estimés** : BBA/MBA/écoles de commerce à <8k€/an, \
mastères spécialisés à <15k€/an
- **Prestige marketing** : formations présentées comme plus accessibles/prestigieuses \
que la réalité (ex: CentraleSupélec en "Plan A" pour un lycéen moyen)
- **Calendriers / deadlines** inexactes ou inventées
- **Débouchés professionnels** fantaisistes ou marketing
- **Distances géographiques** (ex: "Périgueux à 3h30 de Perpignan" alors que réel = 6h)

**NE PAS RELEVER** les erreurs déjà évidentes (bac S supprimé, ECN renommée EDN, etc.) — \
elles sont catchées par les règles en amont.

Réponds au format JSON strict :
{
  "suspect_claims": [
    {
      "claim": "<citation exacte ou paraphrase du claim douteux>",
      "reason": "<1 phrase expliquant pourquoi c'est douteux>",
      "severity": "warning"  // always "warning" depuis layer 3
    }
  ]
}

Si aucune hallucination subtile détectée : `{"suspect_claims": []}`. Ne pas inventer.
"""


@dataclass
class Layer3Warning:
    claim: str
    reason: str
    severity: str = "warning"


def _extract_json(raw: str) -> dict:
    """Parse best-effort : premier bloc {...} dans la réponse."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"suspect_claims": []}


class Layer3Validator:
    """Validator couche 3 via Mistral Small (LLM souverain français).

    Usage :
        layer3 = Layer3Validator(client=Mistral(api_key=...))
        warnings = layer3.check(answer_text)  # list[Layer3Warning]

    Graceful : si client=None OR appel échoue, retourne [] sans crash.
    """

    def __init__(
        self,
        client=None,
        model: str = MISTRAL_SMALL,
        max_tokens: int = 600,
        timeout_ms: int = 5000,
    ):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.timeout_ms = timeout_ms

    def check(self, answer: str) -> list[Layer3Warning]:
        """Retourne liste de warnings subtils détectés, ou [] si skip/erreur."""
        if not self.client or not answer.strip():
            return []

        try:
            user_prompt = f"Voici la réponse à auditer :\n\n{answer}"
            resp = self.client.chat.complete(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": LAYER3_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content or ""
        except Exception:
            # Graceful degradation : quota, timeout, 5xx... layer 3 non-bloquant
            return []

        data = _extract_json(text)
        claims = data.get("suspect_claims") or []
        if not isinstance(claims, list):
            return []

        warnings: list[Layer3Warning] = []
        for item in claims:
            if not isinstance(item, dict):
                continue
            claim = item.get("claim", "").strip()
            reason = item.get("reason", "").strip()
            if claim and reason:
                warnings.append(
                    Layer3Warning(
                        claim=claim,
                        reason=reason,
                        severity=item.get("severity", "warning"),
                    )
                )
        return warnings
