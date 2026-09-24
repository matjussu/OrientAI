"""Banc E : la consigne d'outil explicite n'atteint que le format C, et le client vise l'endpoint EU."""
from src.eval import grille_e
from src.eval.grille_d import PHRASE_OUTIL


class _Formats:
    def texte_a(self, i):
        return f"texte A {i}"

    def carte_b(self, i):
        return f"carte B {i}"

    def carte_c(self, i):
        return f"carte C {i}"


def _joueur(format_, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "cle-de-test")
    expo = {"conversations": {"X": {"exposees": ["psup:1"]}}}
    return grille_e.JoueurE(format_, "mistral-small-2603", _Formats(), expo)


def test_consigne_explicite_au_format_c_seulement(monkeypatch):
    c = _joueur("C", monkeypatch).bloc_fiches(["psup:1"])
    a = _joueur("A", monkeypatch).bloc_fiches(["psup:1"])
    assert grille_e.PHRASE_OUTIL_E in c and PHRASE_OUTIL not in c
    assert grille_e.PHRASE_OUTIL_E not in a and "texte A psup:1" in a
    assert "carte C psup:1" in c


def test_client_sur_endpoint_eu(monkeypatch):
    j = _joueur("A", monkeypatch)
    assert j.client.sdk_configuration.server_url == "https://api.eu.mistral.ai"


def test_prix_publies_pour_les_quatre_modeles():
    assert set(grille_e.MODELES) == {"mistral-medium-2604", "zai-glm-5-2", "zai-glm-5-3", "mistral-small-2603"}
    assert all("lu le 24/09" in note for _, note in grille_e.PRIX.values())
