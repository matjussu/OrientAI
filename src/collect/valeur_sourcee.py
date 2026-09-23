"""Enveloppe commune des champs de l'étape B : une valeur, sa source, son millésime, sa collecte.

Forme fixée par `results/donnee_etape_b/CONTRACT.md` (section 2). Un champ de l'étape B est
toujours présent sur une fiche concernée : `disponible` avec sa valeur, ou `non_disponible` avec
la raison en clair. Jamais absent, jamais une valeur par défaut.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.collect.sources_officielles import SOURCES, charger_verrou


@dataclass(frozen=True)
class SourceLue:
    """Source qui n'est pas un fichier téléchargé (page lue, tableau recopié dans le code)."""

    id: str
    libelle: str
    url: str
    licence: str
    lue_le: str
    # Autres pages où le même texte a été lu (source seconde, quand la première refuse les scripts).
    temoins: tuple[dict, ...] = ()


# Pages dont les montants sont recopiés dans le code (`src.collect.couts`).
SERVICE_PUBLIC_F36520 = SourceLue(
    "service_public_f36520",
    "Service-Public, fiche F36520 « Droits d'inscription » (page « vérifié le 20 août 2026 »), "
    "d'après l'arrêté du 19 avril 2019",
    "https://www.service-public.gouv.fr/particuliers/vosdroits/F36520/2",
    "Licence Ouverte (DILA)",
    "2026-09-23",
)
TABLEAU_DROITS_2026 = SourceLue(
    "tableau_droits_2026_2027",
    "Tableau ministériel « Montant des droits de scolarité au titre de l'année universitaire "
    "2026-2027, établissements publics relevant du ministre chargé de l'enseignement supérieur », "
    "republié par l'Université de Reims (PDF sha256 b2b8c9c003d29331...)",
    "https://www.univ-reims.fr/media-files/65970/i02-droits-inscription-2025-2026.pdf",
    "document administratif public",
    "2026-09-23",
)
CODE_TRAVAIL_L6211_1 = SourceLue(
    "code_travail_l6211_1",
    "Code du travail, article L6211-1 (version en vigueur depuis le 3 août 2023), Légifrance",
    "https://www.legifrance.gouv.fr/codes/id/LEGISCTA000006178183",
    "texte officiel",
    "2026-09-23",
    # Légifrance refuse les lectures automatiques ; Jarvis a relu la phrase mot pour mot sur le code
    # du travail numérique (version mise à jour le 03/08/2023) le 23/09/2026.
    temoins=({"url": "https://code.travail.gouv.fr/code-du-travail/l6211-1",
              "libelle": "Code du travail numérique, article L6211-1 (version mise à jour le 03/08/2023)",
              "lue_le": "2026-09-23", "lue_par": "Jarvis"},),
)
SOURCES_LUES = {s.id: s for s in (SERVICE_PUBLIC_F36520, TABLEAU_DROITS_2026, CODE_TRAVAIL_L6211_1)}


class Referentiel:
    """Décrit une source (verrouillée ou lue) sous la forme attendue par l'enveloppe."""

    def __init__(self, verrou: dict | None = None) -> None:
        self.verrou = charger_verrou() if verrou is None else verrou

    def source(self, source_id: str) -> tuple[dict, str]:
        """(bloc `source`, date de collecte) d'une source connue ; KeyError sinon."""
        if source_id in SOURCES_LUES:
            s = SOURCES_LUES[source_id]
            bloc = {"id": s.id, "libelle": s.libelle, "url": s.url, "licence": s.licence}
            if s.temoins:
                bloc["temoins"] = [dict(t) for t in s.temoins]
            return bloc, s.lue_le
        s = SOURCES[source_id]
        collecte = self.verrou[source_id]["telecharge_le"]
        return {"id": s.nom, "libelle": s.producteur, "url": s.url, "licence": s.licence}, collecte

    def disponible(self, valeur: dict, source_id: str, millesime: str, rattachement: str) -> dict:
        source, collecte = self.source(source_id)
        return {
            "statut": "disponible",
            "valeur": valeur,
            "raison": None,
            "source": source,
            "millesime": millesime,
            "collecte": collecte,
            "rattachement": rattachement,
        }

    def non_disponible(
        self,
        raison: str,
        source_id: str | None = None,
        millesime: str | None = None,
        rattachement: str | None = None,
    ) -> dict:
        if not raison:
            raise ValueError("une donnée non disponible dit pourquoi")
        source, collecte = self.source(source_id) if source_id else (None, None)
        return {
            "statut": "non_disponible",
            "raison": raison,
            "source": source,
            "millesime": millesime,
            "collecte": collecte,
            "rattachement": rattachement,
        }
