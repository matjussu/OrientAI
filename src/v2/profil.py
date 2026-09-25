"""Le profil de l'élève (contrat du cerveau, section 4 ; CONTRAT-etape3, section 3).

Retenu le temps de la conversation, côté serveur, réinjecté au modèle à chaque message. Pas de nom, pas d'e-mail,
pas de lycée nominatif : `extra="forbid"` refuse tout champ hors liste.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Statut = Literal["lyceen", "etudiant", "parent", "reorientation"]
Niveau = Literal["premiere", "terminale", "bac_obtenu", "bac+1", "bac+2", "bac+3", "bac+4", "bac+5"]
VoieBac = Literal["generale", "sti2d", "st2s", "stmg", "stl", "std2a", "stav", "sthr", "s2tmd", "professionnelle"]
# Enseignements de spécialité de la voie générale et les deux options de maths. Liste écrite de mémoire le 25/09,
# non relue contre eduscol : supposée. Une spécialité absente est refusée avec les valeurs proches.
Specialite = Literal["mathematiques", "physique_chimie", "svt", "nsi", "ses", "hggsp", "hlp", "llcer", "llca",
                     "sciences_ingenieur", "biologie_ecologie", "arts", "eppcs", "maths_complementaires",
                     "maths_expertes"]


class _Champs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statut: Statut | None = None
    niveau_actuel: Niveau | None = None
    voie_bac: VoieBac | None = None
    specialite_bac_pro: str | None = Field(None, max_length=80, description="spécialité d'un bac pro, ex. CIEL, ASSP")
    specialites: list[Specialite] | None = Field(None, max_length=4)
    moyenne: float | None = Field(None, ge=0, le=20)
    moyenne_detail: str | None = Field(None, max_length=80, description="ex. « 16 en maths »")
    commune: str | None = Field(None, max_length=80, description="nom de la commune de l'élève")
    mobilite_km: int | None = Field(None, ge=0, le=300, description="distance maximale acceptée, en km")
    pret_a_partir: bool | None = None
    budget: Literal["serre", "moyen", "indifferent"] | None = None
    alternance: Literal["souhaitee", "indifferente", "exclue"] | None = None
    interets: list[str] | None = Field(None, max_length=10)
    a_eviter: list[str] | None = Field(None, max_length=10, description="ce que l'élève exclut (jamais une inclusion)")

    @field_validator("interets", "a_eviter")
    @classmethod
    def _courts(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and any(len(x) > 60 for x in v):
            raise ValueError("chaque entrée fait au plus 60 caractères")
        return v


class MettreAJourProfil(_Champs):
    """Enregistre ce que l'élève a dit de lui. Ne renseigner que ce qu'il a dit ; un champ absent reste inchangé."""


class Profil(_Champs):
    code_insee: str | None = None
    formations_citees: list[str] = Field(default_factory=list)

    def fusionner(self, maj: MettreAJourProfil, code_insee: str | None = None) -> "Profil":
        donnees = self.model_dump()
        donnees.update({k: v for k, v in maj.model_dump().items() if v is not None})
        if maj.commune is not None:
            donnees["code_insee"] = code_insee
        return Profil(**donnees)

    def citer(self, ids: list[str]) -> None:
        for i in ids:
            if i not in self.formations_citees:
                self.formations_citees.append(i)

    def pour_le_modele(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v not in (None, [], "")}
