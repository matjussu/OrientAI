"""GPT-5.5 seul, sans fiche : la cible « ChatGPT seul » du contrat (section 12).

API sans recherche web (amendement A du protocole) : on mesure le modèle seul, pas l'app ChatGPT. Même prompt
système et paramètres par défaut que le run du 05/09 (`src/eval/battery/systems.py`, OpenAISystem), pour rester
comparable au 4,28 de ce jour-là.
"""
from __future__ import annotations

from src.eval.battery.config import MODELS, SYSTEM_PROMPT_BASELINE
from src.eval.battery.systems import check_complete


class ChatGPT:
    nom = "chatgpt"
    fils = 3

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI()
        self.modele = MODELS["gpt"]
        self.modeles = [self.modele]

    def empreinte(self) -> dict:
        return {"modele": self.modele, "prompt_systeme": "SYSTEM_PROMPT_BASELINE"}

    def ask(self, question: str, history: list[dict]) -> dict:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT_BASELINE}, *history, {"role": "user", "content": question}]
        r = self.client.chat.completions.create(model=self.modele, messages=msgs)
        check_complete(r.choices[0].finish_reason, self.modele)
        return {"reponse": r.choices[0].message.content, "sources": [], "source_positions": [],
                "usage": {self.modele: {"entree": r.usage.prompt_tokens, "sortie": r.usage.completion_tokens,
                                        "non_mesures": 0}},
                "trace": {"modele_rendu": r.model}, "modele": self.modele}


VERSION = ChatGPT
