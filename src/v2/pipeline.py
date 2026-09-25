"""Le pipeline v2 (contrat du cerveau, section 2 ; CONTRAT-etape3, section 2) : 4 étages, une boucle écrite par nous.

    message -> 1. filtre (ScopeClassifier du v1, inchangé)
            -> 2. cerveau : GLM 5.3 + outils, au plus 6 appels d'outils par message
            -> 3. vérificateur de chiffres (1 réécriture, puis phrase retirée et tracée)
            -> 4. réponse, émise une fois vérifiée

Pas de framework d'agents (Matteo 10708). Chaque étape est tracée au format « État des lieux » (section 7 du parent).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable

from src.eval.grille_d import texte_reponse
from src.rag.models import MISTRAL_SMALL
from src.v2 import prompt as prompt_v0
from src.v2.outils import Outils, catalogue
from src.v2.profil import Profil
from src.v2.verificateur import REPONSE_VIDE, chiffres_eleve, message_reecriture, retirer_phrases, verifier

MODELE = "zai-glm-5-3"          # banc E, PR #186 ; identifiant exact, jamais l'alias zai-glm-5 / zai-glm-latest
MODELE_FILTRE = MISTRAL_SMALL   # « mistral-small-2603 », passé en paramètre au ScopeClassifier (non modifié)
SERVEUR = "https://api.eu.mistral.ai"
PLAFOND_OUTILS = 6              # choix Q5 du parent
MAX_APPELS_MODELE = 14          # garde-fou : 6 outils + réécriture laissent de la marge ; au-delà, panne tracée
TEMPERATURE = 0.3               # celle des bancs D et E (src/eval/grille_d.py)
FENETRE_HISTORIQUE = 6          # messages rejoués, comme la plateforme (src/eval/battery/config.py HISTORY_WINDOW)
MESSAGE_PLAFOND = ("plafond de 6 recherches atteint pour ce message : cet appel n'a pas été exécuté. Réponds avec ce "
                   "que tu as déjà, et dis-le à l'élève.")
IDS_CITES = ("trouver_formation", "lire_fiche", "comparer")
RELANCE_VIDE = "Rédige maintenant ta réponse à l'élève avec ce que tu as, sans appeler d'outil."


@dataclass
class EtatConversation:
    profil: Profil = field(default_factory=Profil)
    historique: list[dict] = field(default_factory=list)   # messages affichés (élève, assistant)
    valeurs: list[dict] = field(default_factory=list)      # valeurs chiffrées rendues par les outils, tous tours
    messages_eleve: list[str] = field(default_factory=list)
    ids_rendus: list[str] = field(default_factory=list)


class PanneModele(RuntimeError):
    pass


def phrase_etape(nom: str, args: dict, outils: Outils | None = None) -> str:
    """Phrase affichée pendant l'attente (choix Q2), construite par le code, jamais par le modèle."""
    a = args if isinstance(args, dict) else {}
    lieu = ""
    if isinstance(a.get("pres_de"), dict):
        lieu = f" près de {a['pres_de'].get('commune')} ({a['pres_de'].get('rayon_km')} km)"
    elif a.get("communes"):
        lieu = " à " + ", ".join(map(str, a["communes"]))
    elif a.get("departements"):
        lieu = " dans le département " + ", ".join(map(str, a["departements"]))
    if nom == "chercher_formations":
        quoi = " ".join(filter(None, [" ".join(x.upper() if len(x) <= 4 else x for x in a.get("types") or []),
                                      " ".join(a.get("filieres") or []), a.get("intitule_contient")]))
        return f"je cherche les formations {quoi}{lieu}".replace("  ", " ").strip()
    if nom == "chercher_masters":
        return f"je cherche les masters {a.get('mention_contient') or ''}{lieu}".replace("  ", " ").strip()
    if nom == "trouver_formation":
        return f"je retrouve « {a.get('texte', '')} »"
    if nom == "lire_fiche":
        if a.get("ids"):
            return f"je lis {len(a['ids'])} fiches"
        f = next((x for x in (outils.index if outils else []) if x["id"] == str(a.get("id", "")).strip("[] ")), None)
        return f"je lis la fiche {f['intitule']}, {f['etablissement']}" if f else f"je lis la fiche {a.get('id')}"
    if nom == "comparer":
        return f"je compare {len(a.get('ids') or [])} formations"
    if nom == "trouver_commune":
        return f"je cherche la commune {a.get('nom', '')}"
    if nom == "lister_valeurs":
        return f"je regarde les valeurs possibles de {a.get('champ', '')}"
    if nom == "mettre_a_jour_profil":
        return "je note ce que tu m'as dit"
    return f"j'utilise {nom}"


class Pipeline:
    def __init__(self, client, outils: Outils | None = None, classifieur=None, modele: str = MODELE,
                 sommeil: Callable[[float], None] = time.sleep):
        from src.rag.scope_classifier import ScopeClassifier
        self.client = client
        self.outils = outils or Outils()
        self.classifieur = classifieur or ScopeClassifier(client=client, model=MODELE_FILTRE)
        self.modele = modele
        self.catalogue = catalogue()
        self.sommeil = sommeil

    # appel au modèle, avec nouvelles tentatives (429 mesuré sur GLM au banc D : attente plus longue)
    def _appel(self, messages: list[dict], outils: bool, trace: dict):
        kw = {"tools": self.catalogue, "tool_choice": "auto"} if outils else {}
        essais = 0
        while True:
            essais += 1
            try:
                t0 = time.time()
                r = self.client.chat.complete(model=self.modele, messages=messages, temperature=TEMPERATURE, **kw)
                trace["appels_modele"].append({"secondes": round(time.time() - t0, 2), "outils_permis": outils,
                                               "finish_reason": r.choices[0].finish_reason, "modele_rendu": r.model,
                                               "essais": essais})
                if r.model and r.model != self.modele:
                    raise PanneModele(f"modèle rendu {r.model!r} différent du modèle demandé {self.modele!r}")
                return r
            except PanneModele:
                raise
            except Exception as e:  # noqa: BLE001 - nouvelle tentative bornée, puis panne remontée au lanceur
                limite = "429" in str(e)
                if essais < (7 if limite else 3):
                    self.sommeil(min(120, 10 * 2 ** (essais - 1)) if limite else 5 * essais)
                    continue
                raise PanneModele(f"{type(e).__name__}: {e}") from e

    def _boucle(self, msgs: list[dict], etat: EtatConversation, trace: dict, compteur: dict,
                on_etape: Callable[[str], None] | None) -> str:
        """Tant que le modèle demande des outils : exécuter (au plus 6 par message), rendre, rappeler."""
        while True:
            if len(trace["appels_modele"]) >= MAX_APPELS_MODELE:
                raise PanneModele(f"plus de {MAX_APPELS_MODELE} appels au modèle pour un message")
            permis = compteur["outils"] < PLAFOND_OUTILS
            r = self._appel(msgs, permis, trace)
            m = r.choices[0].message
            texte, pensee = texte_reponse(m)
            trace["appels_modele"][-1]["caracteres_texte"], trace["appels_modele"][-1]["raisonnement"] = len(texte), pensee
            if not m.tool_calls or not permis:
                if texte.strip() or trace.get("relance_vide"):
                    return texte
                # Réponse vide sans appel d'outil (constaté au palier 0 du 25/09, après le plafond) : une relance.
                trace["relance_vide"] = True
                msgs.append({"role": "user", "content": RELANCE_VIDE})
                continue
            msgs.append({"role": "assistant", "content": texte, "tool_calls": m.tool_calls})
            for tc in m.tool_calls:
                nom, brut = tc.function.name, tc.function.arguments
                if compteur["outils"] >= PLAFOND_OUTILS:
                    trace["plafond_atteint"] = True
                    trace["outils"].append({"nom": nom, "arguments": brut, "execute": False, "erreur": "plafond"})
                    msgs.append({"role": "tool", "name": nom, "tool_call_id": tc.id, "content": MESSAGE_PLAFOND})
                    continue
                compteur["outils"] += 1
                try:
                    args = json.loads(brut) if isinstance(brut, str) else (brut or {})
                except ValueError:
                    args = {}
                etape = phrase_etape(nom, args, self.outils)
                trace["etapes"].append(etape)
                if on_etape:
                    on_etape(etape)
                t0 = time.time()
                res = self.outils.executer(nom, brut, etat)
                etat.valeurs += res.valeurs
                etat.ids_rendus += [i for i in res.ids if i not in etat.ids_rendus]
                if nom in IDS_CITES and not res.erreur:
                    etat.profil.citer(res.ids)
                trace["outils"].append({"nom": nom, "arguments": args if args else brut, "execute": True,
                                        "ids_rendus": res.ids, "valeurs": res.valeurs, "meta": res.meta,
                                        "texte": res.texte,
                                        "erreur": res.erreur, "secondes": round(time.time() - t0, 3)})
                msgs.append({"role": "tool", "name": nom, "tool_call_id": tc.id, "content": res.texte})

    def repondre(self, message: str, etat: EtatConversation,
                 on_etape: Callable[[str], None] | None = None) -> dict:
        t0 = time.time()
        trace: dict = {"profil_avant": etat.profil.pour_le_modele(), "outils": [], "etapes": [], "appels_modele": [],
                       "brouillons": [], "verifications": [], "phrases_retirees": [], "plafond_atteint": False,
                       "latence_s": {}}
        historique = etat.historique[-FENETRE_HISTORIQUE:]
        etat.messages_eleve.append(message)

        # 1. filtre
        scope = self.classifieur.classify(message, history=historique or None)
        trace["filtre"] = {"label": scope.label, "via": scope.via, "reason": scope.reason}
        trace["latence_s"]["filtre"] = round(time.time() - t0, 2)
        if scope.label != "in_scope":
            return self._fin(message, scope.pre_written_response, etat, trace, t0, court_circuit=True)

        # 2. cerveau
        t1 = time.time()
        msgs = [{"role": "system", "content": prompt_v0.systeme(etat.profil.pour_le_modele())}, *historique,
                {"role": "user", "content": message}]
        compteur = {"outils": 0}
        brouillon = self._boucle(msgs, etat, trace, compteur, on_etape)
        trace["brouillons"].append(brouillon)

        # 3. vérificateur : une réécriture, puis retrait des phrases
        eleve = chiffres_eleve(etat.messages_eleve)
        v = verifier(brouillon, etat.valeurs, eleve)
        trace["verifications"].append(v)
        final = brouillon
        if v["non_adosses"]:
            msgs += [{"role": "assistant", "content": brouillon},
                     {"role": "user", "content": message_reecriture(v["non_adosses"])}]
            final = self._boucle(msgs, etat, trace, compteur, on_etape)
            trace["brouillons"].append(final)
            v2 = verifier(final, etat.valeurs, eleve)
            trace["verifications"].append(v2)
            if v2["non_adosses"]:
                final, retirees = retirer_phrases(final, etat.valeurs, eleve)
                trace["phrases_retirees"] = retirees
                if not final.strip():
                    final = REPONSE_VIDE
        trace["latence_s"]["cerveau_et_verification"] = round(time.time() - t1, 2)
        return self._fin(message, final, etat, trace, t0)

    def _fin(self, message: str, reponse: str, etat: EtatConversation, trace: dict, t0: float,
             court_circuit: bool = False) -> dict:
        eleve = chiffres_eleve(etat.messages_eleve)
        vf = verifier(reponse, etat.valeurs, eleve)
        trace["verification_finale"] = vf
        trace["garantie_adosses"] = not vf["non_adosses"]
        trace["court_circuit"] = court_circuit
        trace["profil_apres"] = etat.profil.pour_le_modele()
        trace["ids_rendus_conversation"] = list(etat.ids_rendus)
        trace["latence_s"]["total"] = round(time.time() - t0, 2)
        etat.historique += [{"role": "user", "content": message}, {"role": "assistant", "content": reponse}]
        sources = {}
        for c in vf["adosses"]:
            for p in c["porteurs"]:
                sources.setdefault((p["id"], p["source_id"]), {"id": p["id"], "source_id": p["source_id"]})
        return {"reponse": reponse, "sources": list(sources.values()), "trace": trace}
