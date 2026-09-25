"""Statistiques de l'export état des lieux."""
from src.eval.multiversion.export import _p90, _tokens_lisibles


def test_p90_jamais_sous_la_mediane_et_valeurs_connues():
    import statistics
    for xs in ([27.19, 19.92], [34.46, 19.92], list(range(1, 11)), [5.0], list(range(1, 68))):
        assert _p90(xs) >= statistics.median(xs)
    assert _p90([34.46, 19.92]) == 34.46          # 2 valeurs : le maximum
    assert _p90(list(range(1, 11))) == 9          # 10 valeurs : la 9e
    assert _p90(list(range(1, 101))) == 90        # 100 valeurs : la 90e
    assert _p90([]) is None


def test_appels_de_recherche_exportes_sous_leur_nom():
    u = {"gpt-5.5": {"entree": 10, "sortie": 2, "non_mesures": 0}, "openai-web-search": {"entree": 4, "sortie": 0}}
    assert _tokens_lisibles(u)["openai-web-search"] == {"appels": 4}
    assert _tokens_lisibles(u)["gpt-5.5"] == u["gpt-5.5"]
