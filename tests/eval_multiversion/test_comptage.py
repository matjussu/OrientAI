"""Enveloppe de comptage du client Mistral (src/eval/multiversion/comptage.py), sur un faux client sans réseau.

Falsification : un flux dont l'usage n'arrive qu'APRÈS la balise de fin (cas réel du générateur) doit être compté
grâce à la lecture de fermeture ; sans elle (levier : on coupe la lecture), l'appel doit sortir « non mesuré »,
jamais zéro.
"""
import asyncio
from types import SimpleNamespace as NS

import pytest

from src.eval.multiversion import comptage
from src.eval.multiversion.comptage import ClientCompte


def _chunk(texte=None, usage=None):
    return NS(data=NS(choices=[NS(delta=NS(content=texte))], usage=usage))


class FauxFlux:
    def __init__(self, events):
        self.events, self.ferme = list(events), False

    async def __aenter__(self):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)

    async def __aexit__(self, *a):
        self.ferme = True


class FauxChat:
    def __init__(self, events):
        self.events = events

    def complete(self, **kw):
        return NS(usage=NS(prompt_tokens=100, completion_tokens=20))

    async def stream_async(self, **kw):
        self.flux = FauxFlux(self.events)
        return self.flux


def _client(events):
    return NS(chat=FauxChat(events), embeddings=NS(create=lambda **kw: NS(usage=NS(prompt_tokens=7))))


EVENTS = [_chunk("<reponse_finale>Bonjour"), _chunk("</reponse_finale>"), _chunk(None, NS(prompt_tokens=900,
                                                                                            completion_tokens=50))]


async def _generateur(client):
    # Comme src/rag/generator.py : quitte la boucle à la balise de fin, sans lire le bloc d'usage.
    async with await client.chat.stream_async(model="mistral-medium-2604", messages=[]) as flux:
        async for ev in flux:
            if "</reponse_finale>" in (ev.data.choices[0].delta.content or ""):
                return


def test_stream_quitte_avant_usage_est_quand_meme_compte():
    c = ClientCompte(_client(list(EVENTS)))
    asyncio.run(_generateur(c))
    assert c.releve.par_modele() == {"mistral-medium-2604": {"appels": 1, "entree": 900, "sortie": 50,
                                                             "non_mesures": 0}}
    assert c.releve.appels[0].drain_s is not None


def test_sans_lecture_de_fermeture_l_appel_est_non_mesure(monkeypatch):
    async def sans_lecture(self, exc_type, exc, tb):
        self._compteur.releve.ajouter(comptage.Appel(self._modele, "stream", self._entree, self._sortie))
        return await self._flux.__aexit__(exc_type, exc, tb)
    monkeypatch.setattr(comptage._FluxCompte, "__aexit__", sans_lecture)
    c = ClientCompte(_client(list(EVENTS)))
    asyncio.run(_generateur(c))
    assert c.releve.par_modele()["mistral-medium-2604"]["non_mesures"] == 1


def test_complete_et_embed_comptes():
    c = ClientCompte(_client([]))
    c.chat.complete(model="mistral-small-2603", messages=[])
    c.embeddings.create(model="mistral-embed-2312", inputs=["x"])
    assert c.releve.par_modele() == {
        "mistral-small-2603": {"appels": 1, "entree": 100, "sortie": 20, "non_mesures": 0},
        "mistral-embed-2312": {"appels": 1, "entree": 7, "sortie": 0, "non_mesures": 0}}


def test_appel_non_enveloppe_leve_au_lieu_de_passer_sans_compte():
    c = ClientCompte(_client([]))
    with pytest.raises(AttributeError):
        c.chat.complete_async
    with pytest.raises(AttributeError):
        c.fim
