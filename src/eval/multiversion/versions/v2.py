"""Le cerveau v2 minimal (étape 3, `docs/cerveau/etape3/CONTRAT-etape3.md`), joué par le lanceur multi-version.

Le lanceur appelle `ask(question, history)` avec l'historique affiché, sans identifiant de conversation. L'état du v2
(profil, valeurs rendues par les outils) est donc rangé sous l'empreinte de cet historique : un premier tour
(historique vide) ouvre un état neuf, le tour suivant le retrouve sous l'empreinte de l'historique complété. Les
conversations peuvent ainsi se jouer en parallèle.

Comptage : un client compté (`ClientCompte`) et un pipeline par fil, parce que le relevé du client est unique.
Une panne garde l'usage déjà consommé (attribut `usage` de l'exception, lu par le lanceur).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path

from src.eval.multiversion.comptage import ClientCompte
from src.v2 import prompt as prompt_v0
from src.v2.outils import Outils
from src.v2.pipeline import MODELE, MODELE_FILTRE, SERVEUR, EtatConversation, Pipeline

RACINE = Path(__file__).resolve().parents[4]


def _cle_mistral() -> str:
    """La seule clé lue : MISTRAL_API_KEY, de l'environnement sinon du .env, sans charger les autres variables du
    .env dans le processus (piège de la section 14 du contrat du cerveau)."""
    if os.environ.get("MISTRAL_API_KEY"):
        return os.environ["MISTRAL_API_KEY"]
    from dotenv import dotenv_values
    cle = dotenv_values(RACINE / ".env").get("MISTRAL_API_KEY")
    if not cle:
        raise SystemExit("MISTRAL_API_KEY absente de l'environnement et du .env")
    return cle


def _cle(history: list[dict]) -> str:
    return hashlib.sha256(json.dumps(history, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class V2:
    nom = "v2"
    fils = 3

    def __init__(self):
        self.outils = Outils()
        self.modele = MODELE
        self.modeles = [MODELE, MODELE_FILTRE]
        self._local = threading.local()
        self._etats: dict[str, EtatConversation] = {}
        self._verrou = threading.Lock()

    def _fil(self) -> tuple[ClientCompte, Pipeline]:
        if getattr(self._local, "pipeline", None) is None:
            from mistralai.client import Mistral
            # 60 s : au palier 1, 96 appels, le plus long a pris 24 s ; un appel resté pendu jusqu'aux 180 s d'avant a
            # fait un tour de 202 s (F-QMAT-12). La nouvelle tentative du pipeline prend le relais.
            client = ClientCompte(Mistral(api_key=_cle_mistral(), server_url=SERVEUR, timeout_ms=60_000))
            self._local.client, self._local.pipeline = client, Pipeline(client, outils=self.outils)
        return self._local.client, self._local.pipeline

    def empreinte(self) -> dict:
        paquet = hashlib.sha256()
        for p in sorted((RACINE / "src/v2").glob("*")):
            if p.is_file() and p.suffix in (".py", ".json"):
                paquet.update(p.name.encode() + p.read_bytes())
        manifeste = json.loads((RACINE / "data/processed/base_etape_c.manifest.json").read_text(encoding="utf-8"))
        return {"modele": MODELE, "modele_filtre": MODELE_FILTRE, "serveur": SERVEUR, "prompt_sha": prompt_v0.SHA[:12],
                "src_v2_sha": paquet.hexdigest()[:12], "base_empreinte": manifeste["sortie"]["empreinte_canonique"][:12]}

    @staticmethod
    def arret(tours: list[dict]) -> str | None:
        """Arrêts automatiques du contrat (section 9), en plus du plafond : garantie « chiffres adossés » rouge sur
        un tour ; plus de 20 % de conversations en panne parmi les 10 premières du run (ou les 3 premières, si le
        palier n'en a que 3 : toutes en panne)."""
        rouges = [f"{t['id']}.{t['turn']}" for t in tours if (t.get("trace") or {}).get("garantie_adosses") is False]
        if rouges:
            return f"garantie « chiffres adossés » rouge : {', '.join(rouges[:5])}"
        ordre = list(dict.fromkeys(t["id"] for t in tours))
        en_panne = {t["id"] for t in tours if t.get("error")}
        premieres = ordre[:10]
        if len(premieres) >= 10 and sum(c in en_panne for c in premieres) > 2:
            return f"{sum(c in en_panne for c in premieres)} conversations en panne sur les 10 premières"
        if len(premieres) >= 3 and all(c in en_panne for c in premieres[:3]):
            return "les 3 premières conversations sont en panne"
        return None

    def ask(self, question: str, history: list[dict]) -> dict:
        client, pipeline = self._fil()
        releve = client.nouveau_releve()
        with self._verrou:
            etat = self._etats.pop(_cle(history), None)
        if etat is None:
            etat = EtatConversation(historique=list(history))
        try:
            r = pipeline.repondre(question, etat)
        except Exception as e:
            e.usage = releve.par_modele()
            raise
        with self._verrou:
            self._etats[_cle(list(history) + [{"role": "user", "content": question},
                                              {"role": "assistant", "content": r["reponse"]}])] = etat
        return {"reponse": r["reponse"], "sources": [
                    {"titre": s["id"], "etablissement": None, "ville": None, "source": s["source_id"], "score": None,
                     "texte": ""} for s in r["sources"]],
                "source_positions": [], "usage": releve.par_modele(), "appels": [vars(a) for a in releve.appels],
                "trace": r["trace"], "modele": MODELE}


VERSION = V2
