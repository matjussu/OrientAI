"""AnalystAgent — background parallel profile updater (Sprint 9).

Responsable de la mise à jour incrémentale du UserSessionProfile à
chaque tour. Tourne en parallèle de l'EmpathicAgent (Coordinator
dispatch via ThreadPoolExecutor) — son résultat ne bloque PAS la
réponse user-facing, il enrichit le profil pour le tour suivant.

Pattern : Mistral function-calling ciblé sur un seul tool
`update_session_profile`, force tool_choice="any" (single-call mode).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

from mistralai.client import Mistral

from src.agent.retry import call_with_retry
from src.agent.tool import Tool
from src.agents.hierarchical.schemas import UserSessionProfile
from src.agents.hierarchical.session import Session
from src.rag.models import MISTRAL_SMALL


ANALYST_SYSTEM_PROMPT = """Tu es AnalystAgent d'OrientIA. Ta seule mission est d'analyser
le DERNIER message de l'utilisateur·ice (en tenant compte de l'historique
fourni) pour mettre à jour son profil intra-session.

Tu invoques l'outil `update_session_profile` avec les NOUVELLES informations
détectées dans le dernier message — pas une re-extraction complète, juste
le delta. Le merge est fait côté code.

Règles :
- Si rien de nouveau détecté → appelle quand même l'outil avec des champs
  vides / null (le tool gère le no-op).
- Pour `interets_detectes` : ne mentionne QUE les nouveaux intérêts vus
  dans CE tour (pas ceux déjà connus). Vocabulaire court (1-3 mots
  snake_case ou français simple).
- Pour `contraintes` : format strict 'clé:valeur' (region:occitanie,
  budget:moderate, mobilite:limitee, handicap:dys, etc.)
- Pour `valeurs` : motivations PROFONDES détectées dans le langage du
  user (ex 'impact_societal', 'stabilite_emploi', 'autonomie_quotidien',
  'creativite').
- Pour `questions_ouvertes` : 1-3 zones floues que l'EmpathicAgent
  devrait explorer prochainement.
- Pour `confidence` : 0-1, niveau de clarté du profil après ce tour.
- Tu N'ÉCRIS PAS de réponse narrative — tu invoques l'outil, c'est tout.
"""


PROFILE_UPDATE_TOOL_PARAMS = {
    "type": "object",
    "properties": {
        "niveau_scolaire": {
            "type": ["string", "null"],
            "description": "Niveau scolaire détecté (libre-forme structurée). Ex 'terminale_spe_maths_physique', 'l1_droit_redoublement', 'professionnel_actif_marketing'. Null si pas détecté ce tour.",
        },
        "age_estime": {
            "type": ["integer", "null"],
            "description": "Âge estimé si déductible. Null si non détectable.",
        },
        "region": {
            "type": ["string", "null"],
            "description": "Région française mentionnée (libellé canonique, inclut DROM). Null si non mentionnée.",
        },
        "interets_detectes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "NOUVEAUX intérêts/appétences détectés ce tour (1-3 mots).",
        },
        "contraintes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "NOUVELLES contraintes détectées ce tour (format 'clé:valeur').",
        },
        "valeurs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "NOUVELLES valeurs/motivations détectées ce tour.",
        },
        "questions_ouvertes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Zones floues à explorer prochainement (1-3 questions courtes).",
        },
        "confidence": {
            "type": "number",
            "description": "Confidence agrégée 0-1 sur la clarté du profil après ce tour.",
        },
    },
    "required": ["interets_detectes", "contraintes", "valeurs", "questions_ouvertes", "confidence"],
}


def _profile_update_tool_func(**kwargs) -> dict:
    """Validation passthrough du payload tool. Retourne le dict normalisé."""
    return {
        "niveau_scolaire": kwargs.get("niveau_scolaire"),
        "age_estime": kwargs.get("age_estime"),
        "region": kwargs.get("region"),
        "interets_detectes": kwargs.get("interets_detectes") or [],
        "contraintes": kwargs.get("contraintes") or [],
        "valeurs": kwargs.get("valeurs") or [],
        "questions_ouvertes": kwargs.get("questions_ouvertes") or [],
        "confidence": float(kwargs.get("confidence", 0.0)),
    }


PROFILE_UPDATE_TOOL = Tool(
    name="update_session_profile",
    description=(
        "Met à jour le UserSessionProfile intra-session avec les "
        "NOUVELLES informations détectées dans le dernier message "
        "user. Merge incrémental côté code — passe le delta uniquement."
    ),
    parameters=PROFILE_UPDATE_TOOL_PARAMS,
    func=_profile_update_tool_func,
)


@dataclass
class AnalystAgent:
    """Background profile updater — Mistral function-calling.

    Tourne en parallèle de l'EmpathicAgent. Latency typique : 2-4s
    (mistral-small-latest, single tool call). Le Coordinator l'attend
    avant de boucler le tour, pour que le profil soit à jour pour le
    tour suivant.
    """

    client: Mistral
    model: str = MISTRAL_SMALL
    timeout_ms: int = 30_000
    max_retries: int = 2
    initial_backoff: float = 1.5

    def update_profile(self, session: Session) -> dict:
        """Analyse le DERNIER message user de la session et retourne le delta.

        Le caller (Coordinator) applique le delta via
        `session.profile.merge_update(delta)`.

        Returns:
            dict du delta (mêmes clés que UserSessionProfile, certaines
            null). Vide en cas d'erreur (passthrough non-bloquant).
        """
        if not session.turns:
            return {}

        history = session.history_messages()
        # Inject latest user message (tour ouvert ou clos peu importe)
        # — on veut qu'AnalystAgent voit le dernier signal user.

        messages = [{"role": "system", "content": ANALYST_SYSTEM_PROMPT}]
        # Inclure jusqu'aux 6 derniers échanges pour contexte
        messages.extend(history[-12:])

        try:
            response = call_with_retry(
                lambda: self.client.chat.complete(
                    model=self.model,
                    messages=messages,
                    tools=[PROFILE_UPDATE_TOOL.to_mistral_schema()],
                    tool_choice="any",
                ),
                max_retries=self.max_retries,
                initial_backoff=self.initial_backoff,
            )
            msg = response.choices[0].message
            if not msg.tool_calls:
                return {}
            tc = msg.tool_calls[0]
            if tc.function.name != PROFILE_UPDATE_TOOL.name:
                return {}
            args = json.loads(tc.function.arguments)
            return PROFILE_UPDATE_TOOL.call(**args)
        except (json.JSONDecodeError, Exception):
            # Passthrough non-bloquant — l'AnalystAgent ne doit jamais
            # casser la conversation. Profile reste tel quel ce tour.
            return {}
