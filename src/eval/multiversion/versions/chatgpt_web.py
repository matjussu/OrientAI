"""GPT-5.5 AVEC recherche web : au plus près de ChatGPT tel que tout le monde l'utilise (proposé par Jarvis le 25/09,
en attente du choix de Matteo ; protocole v0.2).

Responses API, outil `web_search`, `tool_choice` auto : le modèle décide lui-même de chercher, comme dans l'app. Même
prompt système qu'au 05/09 (en `instructions`). Localisation approximative France : l'app connaît le pays de
l'élève ; sans elle, l'outil suppose les États-Unis (défaut `country: US` de la doc, lu le 25/09 via context7,
developers.openai.com/api/docs/guides/tools-web-search).

Facturation (doc et page de prix, lues le 25/09) : les tokens au prix du modèle, plus 10 USD pour 1 000 appels dont
l'action est `search` (`open_page` et `find_in_page` ne sont pas facturés comme appels). Les appels de recherche sont
comptés dans `usage` sous la clé `openai-web-search` (config.PRICES).

Sources : les `url_citation` de la réponse (rang, titre, url). Pas de position corpus : les chiffres adossés à NOS
fiches ne sont pas calculables pour cette version (dit comme tel au rapport, jamais 0 %).
"""
from __future__ import annotations

from src.eval.battery.config import MODELS, SYSTEM_PROMPT_BASELINE

RECHERCHE = "openai-web-search"


def lire_reponse(r) -> dict:
    """Texte, sources citées et appels de recherche d'une réponse Responses API (séparé pour être testé sans réseau)."""
    texte, sources, vues, appels, actions = [], [], set(), 0, []
    for item in r.output or []:
        if item.type == "web_search_call":
            action = getattr(getattr(item, "action", None), "type", None)
            actions.append(action)
            appels += action == "search"
        elif item.type == "message":
            for part in item.content or []:
                if getattr(part, "type", None) != "output_text":
                    continue
                texte.append(part.text)
                for a in part.annotations or []:
                    if getattr(a, "type", None) == "url_citation" and a.url not in vues:
                        vues.add(a.url)
                        sources.append({"titre": a.title, "etablissement": None, "ville": None, "source": "web",
                                        "url": a.url, "score": None, "texte": ""})
    return {"texte": "".join(texte), "sources": sources, "recherches": appels, "actions": actions}


class ChatGPTWeb:
    nom = "chatgpt_web"
    fils = 3

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI()
        self.modele = MODELS["gpt"]
        self.modeles = [self.modele, RECHERCHE]

    def empreinte(self) -> dict:
        return {"modele": self.modele, "prompt_systeme": "SYSTEM_PROMPT_BASELINE", "outil": "web_search",
                "localisation": "FR"}

    def ask(self, question: str, history: list[dict]) -> dict:
        r = self.client.responses.create(
            model=self.modele, instructions=SYSTEM_PROMPT_BASELINE,
            input=[*history, {"role": "user", "content": question}],
            tools=[{"type": "web_search", "user_location": {"type": "approximate", "country": "FR"}}],
            tool_choice="auto")
        if r.status != "completed":
            raise RuntimeError(f"reponse {r.status} : {r.incomplete_details}")
        lu = lire_reponse(r)
        return {"reponse": lu["texte"], "sources": lu["sources"], "source_positions": [],
                "usage": {self.modele: {"entree": r.usage.input_tokens, "sortie": r.usage.output_tokens,
                                        "non_mesures": 0},
                          RECHERCHE: {"entree": lu["recherches"], "sortie": 0, "non_mesures": 0}},
                "trace": {"modele_rendu": r.model, "recherches": lu["recherches"], "actions_web": lu["actions"]},
                "modele": self.modele}


VERSION = ChatGPTWeb
