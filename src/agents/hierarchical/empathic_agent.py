"""EmpathicAgent — foreground blocking conversational agent (Sprint 9).

Responsable de la posture conseiller :
- Active listening (reformulation systématique en ouverture)
- Reconnaissance émotion (si pertinent)
- Questions ouvertes (tour 1-2) OU 3 options pondérées (tour 3+)

Charge le system prompt depuis `prompts/persona_conseiller_v1.txt`. Une
seule call Mistral par tour, target latency ≤ 3s en mode listening
(pas de RAG, pas de critic loop, pas de fact-check post).

Quand le SynthesizerAgent fournit une base factuelle (tour 3+), le
EmpathicAgent re-emballe cette base dans la posture conseiller plutôt
que de la rendre brute à l'utilisateur·ice.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from mistralai.client import Mistral

from src.agent.retry import call_with_retry
from src.agents.hierarchical.schemas import EmpathicResponse, UserSessionProfile
from src.agents.hierarchical.session import Session
from src.rag.models import MISTRAL_MEDIUM


_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
_PERSONA_PROMPT_PATH = _PROMPTS_DIR / "persona_conseiller_v1.txt"


def load_persona_prompt() -> str:
    """Charge le persona system prompt depuis le fichier .txt."""
    return _PERSONA_PROMPT_PATH.read_text(encoding="utf-8")


@dataclass
class EmpathicAgent:
    """Foreground blocking agent — produit la réponse user-facing.

    Latency budget : ≤ 3s en mode listening (tour 1-2). En mode reco
    (tour 3+ avec base factuelle SynthesizerAgent), latency dominée par
    le SynthesizerAgent en amont.
    """

    client: Mistral
    model: str = MISTRAL_MEDIUM
    temperature: float = 0.4
    max_tokens: int = 1500
    timeout_ms: int = 30_000
    max_retries: int = 2
    initial_backoff: float = 1.5
    _system_prompt: str | None = None

    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = load_persona_prompt()
        return self._system_prompt

    def _profile_context_block(self, profile: UserSessionProfile) -> str:
        """Sérialise le profil en bloc texte injecté en system context.

        Skip si le profil est structurellement vide (aucun champ scalaire
        ni liste populée). Le `tour_count` seul ne déclenche pas
        l'injection — au tour 1 sans analyst run, on n'injecte rien.
        """
        is_empty = (
            profile.niveau_scolaire is None
            and profile.age_estime is None
            and profile.region is None
            and not profile.interets_detectes
            and not profile.contraintes
            and not profile.valeurs
            and not profile.questions_ouvertes
        )
        if is_empty:
            return ""
        lines = ["## CONTEXTE PROFIL UTILISATEUR (intra-session, mis à jour à chaque tour)"]
        if profile.niveau_scolaire:
            lines.append(f"- Niveau scolaire : {profile.niveau_scolaire}")
        if profile.age_estime is not None:
            lines.append(f"- Âge estimé : {profile.age_estime}")
        if profile.region:
            lines.append(f"- Région : {profile.region}")
        if profile.interets_detectes:
            lines.append(f"- Intérêts détectés : {', '.join(profile.interets_detectes)}")
        if profile.contraintes:
            lines.append(f"- Contraintes : {', '.join(profile.contraintes)}")
        if profile.valeurs:
            lines.append(f"- Valeurs / motivations : {', '.join(profile.valeurs)}")
        if profile.questions_ouvertes:
            qs = "; ".join(profile.questions_ouvertes[:3])
            lines.append(f"- Zones floues à explorer prioritairement : {qs}")
        lines.append(f"- Tour conversation : {profile.tour_count}")
        return "\n".join(lines)

    def _build_messages(
        self,
        session: Session,
        factual_base: str | None = None,
    ) -> list[dict]:
        """Construit les messages Mistral chat.complete.

        - system : persona prompt + bloc profil dynamique
        - history : tours précédents (user + assistant)
        - dernier user : message courant
        - si factual_base fourni : injecté en bloc system additionnel
          ("Le SynthesizerAgent a préparé la base factuelle suivante...")
        """
        system_parts = [self.system_prompt]
        profile_block = self._profile_context_block(session.profile)
        if profile_block:
            system_parts.append(profile_block)
        if factual_base:
            system_parts.append(
                "## BASE FACTUELLE FOURNIE PAR LE SYNTHESIZERAGENT\n\n"
                "Ce qui suit est le résultat du pipeline RAG factuel "
                "(retrieval ONISEP/Parcoursup/etc.). Tu DOIS le "
                "re-emballer dans ta posture conseiller (reformulation "
                "+ 3 options pondérées + question finale). NE PAS le "
                "restituer brut — adapte au registre conversationnel.\n\n"
                f"{factual_base}"
            )
        messages = [{"role": "system", "content": "\n\n".join(system_parts)}]
        messages.extend(session.history_messages())
        return messages

    def respond(
        self,
        session: Session,
        factual_base: str | None = None,
    ) -> EmpathicResponse:
        """Produit la réponse pour le tour courant (dernier user message ouvert).

        Args:
            session: la session courante (le dernier turn doit être ouvert,
                avec assistant=None).
            factual_base: si non-None, base factuelle produite par le
                SynthesizerAgent à re-emballer en mode reco.

        Returns:
            EmpathicResponse contenant le texte raw + flag reco_mode_active.
        """
        if not session.turns:
            raise ValueError("EmpathicAgent.respond: session sans tour ouvert")

        messages = self._build_messages(session, factual_base=factual_base)

        t0 = time.time()
        response = call_with_retry(
            lambda: self.client.chat.complete(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ),
            max_retries=self.max_retries,
            initial_backoff=self.initial_backoff,
        )
        elapsed_s = time.time() - t0

        text = (response.choices[0].message.content or "").strip()

        return EmpathicResponse(
            reformulation="",  # parsing structuré laissé en backlog Sprint 10
            exploration_or_reco=text,
            reco_mode_active=factual_base is not None,
            raw_text=text,
        )
