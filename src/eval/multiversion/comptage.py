"""Compteur de tokens autour du client Mistral de la prod (protocole results/multiversion/PROTOCOLE.md, section 2).

Tous les appels du chemin servi passent par le client unique donné à `make_production_pipeline` (mesuré le 25/09 :
`chat.complete`, `chat.stream_async`, `embeddings.create`, grep sur src/ hors eval et experimental). L'enveloppe les
laisse passer tels quels et relève l'usage rendu par l'API.

En stream, le générateur quitte la boucle à la balise de fin (`src/rag/generator.py`, `_CLOSE_TAG`), avant le bloc
qui porte l'usage. À la fermeture, l'enveloppe lit le reste du flux pour récupérer cet usage et chronomètre cette
lecture (`drain_s`). Un appel dont l'usage n'a pas été lu est compté « non mesuré », jamais zéro.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class Appel:
    modele: str
    type: str                 # complete | stream | embed
    entree: int | None
    sortie: int | None
    drain_s: float | None = None


@dataclass
class Releve:
    appels: list[Appel] = field(default_factory=list)
    _verrou: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def ajouter(self, appel: Appel) -> None:
        with self._verrou:
            self.appels.append(appel)

    def par_modele(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for a in self.appels:
            m = out.setdefault(a.modele, {"appels": 0, "entree": 0, "sortie": 0, "non_mesures": 0})
            m["appels"] += 1
            if a.entree is None:
                m["non_mesures"] += 1
                continue
            m["entree"] += a.entree
            m["sortie"] += a.sortie or 0
        return out


def _usage(obj) -> tuple[int | None, int | None]:
    u = getattr(obj, "usage", None)
    if u is None:
        return None, None
    return getattr(u, "prompt_tokens", None), getattr(u, "completion_tokens", None)


class _FluxCompte:
    def __init__(self, flux, modele: str, compteur: "ClientCompte"):
        self._flux, self._modele, self._compteur = flux, modele, compteur
        self._entree = self._sortie = None

    def _lire(self, event) -> None:
        e, s = _usage(getattr(event, "data", None))
        if e is not None:
            self._entree, self._sortie = e, s

    async def __aenter__(self):
        await self._flux.__aenter__()
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        event = await self._flux.__anext__()
        self._lire(event)
        return event

    async def __aexit__(self, exc_type, exc, tb):
        drain = None
        if exc_type is None and self._entree is None:
            t0 = time.perf_counter()
            try:
                async for event in self._flux:
                    self._lire(event)
            except Exception:  # noqa: BLE001 - un flux déjà fermé ne doit pas casser la réponse
                pass
            drain = round(time.perf_counter() - t0, 4)
        self._compteur.releve.ajouter(Appel(self._modele, "stream", self._entree, self._sortie, drain))
        return await self._flux.__aexit__(exc_type, exc, tb)


class _ChatCompte:
    def __init__(self, chat, compteur: "ClientCompte"):
        self._chat, self._compteur = chat, compteur

    def complete(self, **kw):
        r = self._chat.complete(**kw)
        e, s = _usage(r)
        self._compteur.releve.ajouter(Appel(kw.get("model", "?"), "complete", e, s))
        return r

    async def stream_async(self, **kw):
        return _FluxCompte(await self._chat.stream_async(**kw), kw.get("model", "?"), self._compteur)

    def __getattr__(self, nom):
        raise AttributeError(f"chat.{nom} n'est pas compté : l'ajouter à l'enveloppe avant de jouer la prod")


class _EmbedCompte:
    def __init__(self, emb, compteur: "ClientCompte"):
        self._emb, self._compteur = emb, compteur

    def create(self, **kw):
        r = self._emb.create(**kw)
        e, _ = _usage(r)
        self._compteur.releve.ajouter(Appel(kw.get("model", "?"), "embed", e, 0 if e is not None else None))
        return r


class ClientCompte:
    """Enveloppe du client Mistral. `nouveau_releve()` avant chaque tour ; un appel non enveloppé lève une erreur
    au lieu de passer sans être compté (un compteur qui rate un appel sous-estime sans le dire)."""

    def __init__(self, client):
        self._client = client
        self.chat = _ChatCompte(client.chat, self)
        self.embeddings = _EmbedCompte(client.embeddings, self)
        self.releve = Releve()

    def nouveau_releve(self) -> Releve:
        self.releve = Releve()
        return self.releve

    def __getattr__(self, nom):
        raise AttributeError(f"client.{nom} n'est pas compté : l'ajouter à l'enveloppe avant de jouer la prod")
