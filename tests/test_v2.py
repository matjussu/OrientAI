"""Cerveau v2 minimal (CONTRAT-etape3, section 8) : bornes des outils, profil, vérificateur, boucle, gate F.

Chaque garantie a son test de sabotage (règle 9, levier ORIENTIA_SABOTAGE_V2) : la vérification qui la protège doit
rougir quand on la casse. Aucun test ne charge le .env ni n'appelle d'API : le modèle et le filtre sont des doublures.
Les tests qui lisent la base C sont sautés quand elle n'est pas construite (CI).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.base_c import outils as bc
from src.v2 import verificateur as vf
from src.v2.outils import ESSENTIEL, SIGLES, Outils, Resultat, normaliser, notion
from src.v2.pipeline import MESSAGE_PLAFOND, PLAFOND_OUTILS, EtatConversation, Pipeline, phrase_etape
from src.v2.profil import MettreAJourProfil, Profil

VRAIE_BASE = Path(bc.BASE_DEFAUT)
base_requise = pytest.mark.skipif(not VRAIE_BASE.exists(), reason="base de l'étape C non construite")


@pytest.fixture(scope="module")
def outils():
    if not VRAIE_BASE.exists():
        pytest.skip("base de l'étape C non construite")
    return Outils()


# ── Outils : bornes ────────────────────────────────────────────────────────────────────────
@base_requise
@pytest.mark.parametrize("args, ok", [
    ({"types": ["but"], "limite": 50}, True), ({"types": ["but"], "limite": 51}, False),
    ({"types": ["but"], "limite": 0}, False),
    ({"pres_de": {"commune": "Lens", "rayon_km": 300}}, True), ({"pres_de": {"commune": "Lens", "rayon_km": 301}}, False),
    ({"types": ["but"], "taux_acces_min": 100}, True), ({"types": ["but"], "taux_acces_min": 101}, False),
    ({"session": "2025"}, True), ({"session": "2026"}, False),
])
def test_chercher_formations_bornes(outils, args, ok):
    r = outils.executer("chercher_formations", args)
    assert (r.erreur is None) == ok, r.texte


@base_requise
def test_valeur_hors_liste_nomme_les_valeurs_proches(outils):
    r = outils.executer("chercher_formations", {"types": ["butt"]})
    assert r.erreur == "parametres_invalides"
    assert "valeurs proches" in r.texte and "'but'" in r.texte


@base_requise
def test_parametre_inconnu_refuse(outils):
    r = outils.executer("chercher_formations", {"type": ["but"]})
    assert r.erreur == "parametres_invalides" and "types" in r.texte


@base_requise
def test_commune_homonyme_et_introuvable(outils):
    homonyme = outils.executer("chercher_formations", {"pres_de": {"commune": "Saint-Denis", "rayon_km": 10}})
    assert homonyme.erreur == "filtre_invalide" and "homonyme" in homonyme.texte
    inconnue = outils.executer("chercher_formations", {"pres_de": {"commune": "Clermont-Ferant", "rayon_km": 10}})
    assert inconnue.erreur == "filtre_invalide" and "Clermont-Ferrand" in inconnue.texte


@base_requise
def test_recherche_dit_total_troncature_et_ecartees(outils):
    r = outils.executer("chercher_formations", {"types": ["bts"], "taux_acces_min": 50, "limite": 3})
    assert r.meta["tronque"] and r.meta["nb_resultats"] > 3 and len(r.ids) == 3
    assert "liste tronquée aux 3 premières" in r.texte
    assert "ecartees_non_disponible" in r.meta


@base_requise
@pytest.mark.parametrize("args, ok", [
    ({"ids": ["psup:7596"]}, False), ({"ids": ["psup:7596", "psup:47455"]}, True),
    ({"ids": ["psup:7596", "psup:47455", "psup:47147", "psup:5482", "psup:32042"]}, True),
    ({"ids": ["psup:7596", "psup:47455", "psup:47147", "psup:5482", "psup:32042", "psup:32116"]}, False),
    ({"ids": ["psup:7596", "psup:7596"]}, False),
])
def test_comparer_bornes(outils, args, ok):
    assert (outils.executer("comparer", args).erreur is None) == ok


@base_requise
def test_comparer_id_et_champ_inconnus(outils):
    r = outils.executer("comparer", {"ids": ["psup:7596", "psup:0"]})
    assert r.erreur and "psup:0" in r.texte and "trouver_formation" in r.texte
    r = outils.executer("comparer", {"ids": ["psup:7596", "psup:47455"], "champs": ["taux_acce"]})
    assert r.erreur and "taux_acces" in r.texte


@base_requise
def test_comparer_memes_champs_memes_sessions(outils):
    r = outils.executer("comparer", {"ids": ["psup:7596", "psup:47455"]})
    lignes = [l for l in r.texte.splitlines() if l.startswith("- Taux d'accès, session")]
    assert len(lignes) == 3 and all("[psup:7596]" in l and "[psup:47455]" in l for l in lignes)
    assert {v["id"] for v in r.valeurs} == {"psup:7596", "psup:47455"}


@base_requise
@pytest.mark.parametrize("texte, commune, attendu", [
    ("BUT info Aubière", None, "psup:7596"), ("licence maths-info UCA", "Clermont-Ferrand", "psup:47455"),
    ("double licence maths info", "Clermont-Ferrand", "psup:47147"), ("MP2I Clemenceau", "Nantes", "psup:32116"),
    ("licence informatique", "Nantes", "psup:32042"), ("licence info parcours info maths", "Nantes", "psup:39126"),
    ("BUT informatique Nantes", None, "psup:5482"), ("BUT info Villetaneuse", None, "psup:11236"),
    ("BUT info Montreuil", None, "psup:11349"), ("double licence maths info Montpellier", None, "psup:31726"),
    ("licence info Montpellier", None, "psup:31257"), ("BUT info Montpellier", None, "psup:4524"),
    ("PASS Grenoble", None, "psup:30790"), ("LAS Grenoble santé biotechnologies", None, "psup:30911"),
    ("licence IMA accès santé Grenoble", None, "psup:31941"), ("MPSI lycée du Parc", None, "psup:8182"),
    ("MP2I lycée du Parc", None, "psup:31680"), ("MPSI La Martinière Monplaisir", None, "psup:8550"),
    ("MP2I La Martinière Monplaisir", None, "psup:39554"),
    ("double licence informatique mathématiques Paris Cité", None, "psup:47242"),
    ("portail maths info Paris Cité", None, "psup:47258"),
])
def test_trouver_formation_famille_nom_du_gate_f(outils, texte, commune, attendu):
    """Les 21 formations nommées du gate F (famille nom), retrouvées dans les 10 candidats."""
    args = {"texte": texte} | ({"commune": commune} if commune else {})
    r = outils.executer("trouver_formation", args)
    assert attendu in r.ids, r.texte


@base_requise
def test_trouver_formation_bornes_et_zero_candidat(outils):
    assert outils.executer("trouver_formation", {"texte": "x"}).erreur == "parametres_invalides"
    assert outils.executer("trouver_formation", {"texte": "de la"}).erreur == "filtre_invalide"
    r = outils.executer("trouver_formation", {"texte": "zzzqqq"})
    assert r.ids == [] and "aucune formation" in r.texte
    assert len(outils.executer("trouver_formation", {"texte": "BTS"}).ids) == 10


def test_normalisation_sigles_et_chiffres_colles():
    assert normaliser("I.U.T. de Lyon1") == "iut de lyon 1"
    assert normaliser("Côte d'Azur") == "cote d azur"


@base_requise
def test_chaque_lecture_de_sigle_rencontre_la_base(outils):
    """La source d'une lecture de sigle est la base : chaque lecture doit y rencontrer au moins une formation."""
    for sigle, lectures in SIGLES.items():
        for lec in lectures:
            mots = lec.split()
            assert any(all(m in f["mots"] for m in mots) for f in outils.index), (sigle, lec)


# ── lire_fiche : l'essentiel par défaut ────────────────────────────────────────────────────
def _essentiel_tenu(outils, id_: str) -> bool:
    r = outils.executer("lire_fiche", {"id": id_})
    notions_rendues = {notion(v["cle"]) for v in r.valeurs if not v["cle"].startswith("insertion.")}
    return r.meta["valeurs_rendues"] < r.meta["valeurs_fiche"] and notions_rendues <= ESSENTIEL


@base_requise
def test_lire_fiche_rend_l_essentiel_par_defaut(outils):
    for id_ in ("psup:7596", "psup:36433", "mm:1603218DH2WG"):
        assert _essentiel_tenu(outils, id_), id_
    r = outils.executer("lire_fiche", {"id": "psup:7596"})
    assert "autres chiffres sur cette fiche (lire_fiche avec detail=true)" in r.texte
    assert r.meta["valeurs_rendues"] == 11


@base_requise
def test_lire_fiche_detail_rend_tout(outils):
    r = outils.executer("lire_fiche", {"id": "psup:7596", "detail": True})
    assert r.meta["valeurs_rendues"] == r.meta["valeurs_fiche"] == 43


@base_requise
def test_sabotage_essentiel_tout_fait_rougir(outils, monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "essentiel_tout")
    assert not _essentiel_tenu(outils, "psup:7596")


@base_requise
def test_valeurs_structurees_egales_au_texte(outils):
    """Chaque valeur que le vérificateur accepte est écrite dans le texte rendu au modèle."""
    r = outils.executer("lire_fiche", {"id": "psup:7596"})
    for v in r.valeurs:
        n = str(int(v["valeur"])) if v["valeur"].is_integer() else f"{v['valeur']}".replace(".", ",")
        assert n in r.texte, v


# ── Profil ─────────────────────────────────────────────────────────────────────────────────
def test_profil_refuse_nom_et_bornes():
    with pytest.raises(ValueError):
        MettreAJourProfil(nom="Léa")
    with pytest.raises(ValueError):
        MettreAJourProfil(moyenne=21)
    with pytest.raises(ValueError):
        MettreAJourProfil(mobilite_km=301)
    with pytest.raises(ValueError):
        MettreAJourProfil(interets=["x" * 61])


def test_profil_fusion_garde_ce_qui_est_dit():
    p = Profil().fusionner(MettreAJourProfil(voie_bac="generale", specialites=["mathematiques", "nsi"]))
    p = p.fusionner(MettreAJourProfil(commune="Nantes"), code_insee="44109")
    assert p.voie_bac == "generale" and p.specialites == ["mathematiques", "nsi"] and p.code_insee == "44109"
    p.citer(["psup:1", "psup:1", "psup:2"])
    assert p.formations_citees == ["psup:1", "psup:2"]


# ── Vérificateur ───────────────────────────────────────────────────────────────────────────
VALEURS = [{"valeur": 34.0, "unite": "pct", "id": "psup:7596", "cle": "taux_acces@2025", "source_id": "s"},
           {"valeur": 96.0, "unite": "places", "id": "psup:7596", "cle": "places@2025", "source_id": "p"}]


def _chiffre_invente_attrape() -> bool:
    v = vf.verifier("Le taux d'accès est de 34 %, tes chances sont de 80 %.", VALEURS)
    return [c["valeur"] for c in v["non_adosses"]] == [80.0]


def test_verificateur_attrape_un_chiffre_invente():
    assert _chiffre_invente_attrape()


def test_sabotage_verificateur_laisse_passer_fait_rougir(monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "verificateur_laisse_passer")
    assert not _chiffre_invente_attrape()


def test_verificateur_tableau_et_chiffre_de_l_eleve():
    t = "| Formation | Taux d'accès (%) | Places |\n|---|---|---|\n| BUT | 34 | 96 |\n| Licence | 55 | 200 |"
    v = vf.verifier(t, VALEURS)
    assert sorted(c["valeur"] for c in v["non_adosses"]) == [55.0, 200.0]
    v = vf.verifier("Le 6 % que tu as vu n'est pas un taux de réussite.", VALEURS, eleve=[(6.0, "pct")])
    assert v["eleve"] and not v["non_adosses"]


def _phrase_retiree() -> bool:
    t = "Le taux d'accès est de 34 %. Tes chances sont de 80 %. Bonne chance !"
    texte, retirees = vf.retirer_phrases(t, VALEURS)
    return retirees == ["Tes chances sont de 80 %."] and not vf.verifier(texte, VALEURS)["non_adosses"]


def test_retrait_de_la_phrase_non_adossee():
    assert _phrase_retiree()


def test_sabotage_garder_phrase_fait_rougir(monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "garder_phrase")
    assert not _phrase_retiree()


def test_retrait_garde_les_puces_et_retire_la_ligne_de_tableau():
    t = "- Places : 97 places.\n- Taux : 34 %.\n\n| Formation | Taux d'accès (%) |\n|---|---|\n| BUT | 34 |\n| L | 55 |"
    texte, retirees = vf.retirer_phrases(t, VALEURS)
    assert "- Taux : 34 %." in texte and "97" not in texte and "| L | 55 |" not in texte and "| BUT | 34 |" in texte
    assert len(retirees) == 2


# ── Boucle : doublures du modèle, des outils et du filtre ─────────────────────────────────
def _msg(texte="", appels=()):
    calls = [SimpleNamespace(id=f"c{i}", function=SimpleNamespace(name=n, arguments=json.dumps(a)))
             for i, (n, a) in enumerate(appels)]
    return SimpleNamespace(model="zai-glm-5-3", choices=[SimpleNamespace(
        message=SimpleNamespace(content=texte, tool_calls=calls or None), finish_reason="stop")])


class ModeleFaux:
    def __init__(self, reponses):
        self.reponses, self.recus = list(reponses), []
        self.chat = self

    def complete(self, **kw):
        self.recus.append(kw)
        return self.reponses.pop(0)


class OutilsFaux:
    index: list = []

    def __init__(self):
        self.executes = []

    def executer(self, nom, arguments, etat=None):
        self.executes.append(nom)
        return Resultat(texte="[psup:7596] taux d'accès 34 %", ids=["psup:7596"], valeurs=list(VALEURS))


class FiltreFaux:
    def __init__(self, label="in_scope"):
        self.label = label

    def classify(self, message, history=None):
        return SimpleNamespace(label=self.label, via="faux", reason="test",
                               pre_written_response="Appelle le 3114." if self.label != "in_scope" else None)


def _pipeline(reponses, label="in_scope"):
    modele, outils = ModeleFaux(reponses), OutilsFaux()
    return Pipeline(modele, outils=outils, classifieur=FiltreFaux(label), sommeil=lambda s: None), modele, outils


def test_plafond_de_6_appels():
    huit = [("lire_fiche", {"id": f"psup:{i}"}) for i in range(8)]
    p, modele, outils = _pipeline([_msg(appels=huit), _msg("Le taux d'accès est de 34 %.")])
    r = p.repondre("question", EtatConversation())
    assert len(outils.executes) == PLAFOND_OUTILS == 6
    refus = [m for m in modele.recus[1]["messages"] if m["role"] == "tool" and m["content"] == MESSAGE_PLAFOND]
    assert len(refus) == 2
    assert "tools" not in modele.recus[1]           # dernier appel sans outil
    assert r["trace"]["plafond_atteint"] and r["trace"]["garantie_adosses"]


def test_reecriture_puis_retrait_de_la_phrase():
    p, modele, _ = _pipeline([
        _msg(appels=[("lire_fiche", {"id": "psup:7596"})]),
        _msg("Le taux d'accès est de 34 %. Tes chances sont de 80 %."),
        _msg("Le taux d'accès est de 34 %. Je dirais 75 % de chances."),
    ])
    r = p.repondre("question", EtatConversation())
    assert "Ces chiffres ne sont dans aucun résultat" in modele.recus[2]["messages"][-1]["content"]
    assert r["reponse"] == "Le taux d'accès est de 34 %."
    assert r["trace"]["phrases_retirees"] == ["Je dirais 75 % de chances."]
    assert r["trace"]["garantie_adosses"] and r["sources"] == [{"id": "psup:7596", "source_id": "s"}]


def test_reecriture_reussie_ne_retire_rien():
    p, _, _ = _pipeline([_msg("Tu as 80 % de chances."), _msg("Je n'ai pas encore lu de fiche.")])
    r = p.repondre("question", EtatConversation())
    assert r["reponse"] == "Je n'ai pas encore lu de fiche." and r["trace"]["phrases_retirees"] == []


def test_filtre_court_circuite_avant_le_modele():
    p, modele, _ = _pipeline([], label="urgent")
    r = p.repondre("je vais mal", EtatConversation())
    assert r["reponse"] == "Appelle le 3114." and modele.recus == [] and r["trace"]["court_circuit"]


def test_etat_garde_les_valeurs_entre_les_tours():
    etat = EtatConversation()
    p, _, _ = _pipeline([_msg(appels=[("lire_fiche", {"id": "psup:7596"})]), _msg("Taux : 34 %."),
                         _msg("Comme dit, 34 %.")])
    p.repondre("q1", etat)
    r = p.repondre("q2", etat)                      # aucun outil au tour 2 : le 34 % reste adossé
    assert r["trace"]["garantie_adosses"] and len(etat.historique) == 4


def test_phrase_d_etape_construite_par_le_code():
    assert phrase_etape("chercher_formations", {"types": ["but"], "filieres": ["Informatique"],
                                                "pres_de": {"commune": "Lens", "rayon_km": 50}}) \
        == "je cherche les formations BUT Informatique près de Lens (50 km)"


# ── Version v2 et lanceur ──────────────────────────────────────────────────────────────────
def test_arrets_automatiques():
    from src.eval.multiversion.versions.v2 import V2
    ok = {"trace": {"garantie_adosses": True}, "error": None, "turn": 0}
    assert V2.arret([ok | {"id": f"c{i}"} for i in range(10)]) is None
    assert "rouge" in V2.arret([ok | {"id": "a"}, {"id": "b", "turn": 0, "error": None,
                                                    "trace": {"garantie_adosses": False}}])
    pannes = [ok | {"id": f"c{i}", "error": "x" if i < 3 else None} for i in range(10)]
    assert "10 premières" in V2.arret(pannes)
    assert "3 premières" in V2.arret([ok | {"id": f"c{i}", "error": "x"} for i in range(3)])


def test_banc_gate_f_charge_par_le_lanceur():
    from src.eval.multiversion.lanceur import charger_banc
    items, sha = charger_banc("gatef")
    assert len(items) == 30 and sum(len(i["turns"]) for i in items) == 32 and sha.startswith("5c78dc6e9001")


@base_requise
def test_detecteur_gate_f_controle_positif(outils):
    from src.eval.multiversion.gate_f import Detecteur
    d = Detecteur(outils)
    rep = "Regarde le BUT informatique de l'I.U.T Clermont Auvergne - site d'Aubière."
    assert d.cites_hors(rep, ["psup:7596"]) == []
    assert d.cites_hors(rep + " Et aussi Nantes Université.", ["psup:7596"]) == ["nantes universite"]


def test_adosses_v2_recompte_depuis_la_trace():
    """Contrôle a posteriori du lanceur, indépendant du vérificateur : un chiffre inventé est compté."""
    from src.eval.multiversion.mesures import adosses_v2
    t0 = {"id": "c", "turn": 0, "question": "j'ai vu 6 % en ligne", "answer": "Taux : 34 %. Le 6 % n'est pas un taux.",
          "trace": {"outils": [{"valeurs": VALEURS}]}}
    t1 = {"id": "c", "turn": 1, "question": "et les places ?", "answer": "96 places, et 12 % de boursiers.",
          "trace": {"outils": []}}
    r = adosses_v2([t1, t0])
    assert r["chiffres_cites"] == 4
    assert r["non_adosses"] == [{"id": "c", "turn": 1, "valeur": 12.0, "unite": "pct"}]
    assert [c["status"] for c in r["par_tour"][("c", 0)]] == ["adosse", "eleve"]


@base_requise
def test_objet_envoye_en_chaine_json_est_decode(outils):
    """GLM 5.3 envoie « pres_de » en chaîne JSON (palier 0, 25/09) : accepté, et une vraie chaîne reste une chaîne."""
    r = outils.executer("chercher_formations", {"types": ["but"], "filieres": ["Informatique"],
                                               "pres_de": json.dumps({"commune": "Lens", "rayon_km": 60})})
    assert r.erreur is None and "psup:7520" in r.ids
    r = outils.executer("trouver_formation", {"texte": "[BUT] info Lens"})
    assert r.erreur is None and r.meta["requete_normalisee"] == "but info lens"


def test_reponse_vide_relancee_une_fois():
    p, modele, _ = _pipeline([_msg(""), _msg("Voici une première orientation.")])
    r = p.repondre("question", EtatConversation())
    assert r["reponse"] == "Voici une première orientation." and r["trace"]["relance_vide"]
    assert modele.recus[1]["messages"][-1]["content"].startswith("Rédige maintenant ta réponse")
