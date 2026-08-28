"""Calendrier Parcoursup + MonMaster 2026 — Vague 3.4 du plan corpus v6.

Audit ground-truth 50q v6 baseline (2026-05-08) : recall@5 catégorie
calendaire = **0%** sur 5 questions ("Quand commencent les vœux Parcoursup ?",
"Date limite vœux ?", "Phase complémentaire ?", "Calendrier MonMaster ?",
"Résultats admission ?"). Cause racine : aucun corpus `domain=calendrier`
dans v6.

## Dates officielles 2026 — VÉRIFIÉES (WebSearch 2026-05-08)

### Parcoursup 2026
Sources :
- https://www.education.gouv.fr/parcoursup-2026-ouverture-le-19-janvier-de-la-phase-d-inscription-et-de-formulation-des-voeux-468674
- https://www.parcoursup.fr/index.php?desc=calendrier

| Date | Étape |
|------|-------|
| 17 déc. 2025 | Consultation de l'offre de formation |
| **19 janvier 2026** | Ouverture inscription + formulation vœux |
| **12 mars 2026** | Date limite formulation vœux (10 max non hiérarchisés) |
| **1er avril 2026** | Date limite confirmation vœux + finalisation dossier |
| 2 juin 2026 | Début phase d'admission |
| 11 juin 2026 | Ouverture phase complémentaire |
| 10 septembre 2026 | Fin phase complémentaire |

### MonMaster 2026
Sources :
- https://information.monmaster.gouv.fr/calendrier/
- https://www.enseignementsup-recherche.gouv.fr/fr/mon-master-le-calendrier-de-la-procedure-pour-l-annee-universitaire-2026-2027-100230

| Date | Étape |
|------|-------|
| **2 février 2026** | Ouverture inscription (création compte + dossier commun) |
| **17 février → 17 mars 2026** | Phase de candidature (dépôt) |
| 21 mars 2026 | Début examen des dossiers + convocations |
| **3 juin → 16 juin 2026** | Phase d'admission (1ʳᵉ vague de réponses) |
| **19 juin → 19 juillet 2026** | Phase complémentaire |

## Note de fraîcheur

Les dates 2026 sont vérifiées via sources officielles `.gouv.fr` au 2026-05-08.
Les dates 2027 ne sont pas encore publiées (octobre-novembre N-1 typiquement).
Mise à jour annuelle nécessaire — automatisable via scraping en Vague 4.

## Format des entrées

```json
{
  "id": "calendrier:parcoursup-2026:ouverture-voeux",
  "domain": "calendrier",
  "source": "parcoursup_calendrier_officiel",
  "annee": 2026,
  "plateforme": "Parcoursup",
  "phase": "voeux",
  "date_debut": "2026-01-19",
  "date_fin": null,
  "libelle": "...",
  "text": "<paragraphe naturel pour embedding>",
  "url": "https://www.parcoursup.fr/...",
  "provenance": {"tier": "tier_1", "source_label": "...", "last_updated": "..."}
}
```

## Usage

```bash
python -m src.collect.build_calendrier_corpus
# → écrit data/processed/calendrier_corpus.json
```
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT_PATH = Path("data/processed/calendrier_corpus.json")
PARCOURSUP_URL = "https://www.parcoursup.fr/index.php?desc=calendrier"
MONMASTER_URL = "https://information.monmaster.gouv.fr/calendrier/"
DSE_URL = "https://www.etudiant.gouv.fr/fr/bourse-et-logement-constituez-votre-dossier-social-etudiant-dse-409"
DSE_LOGEMENT_URL = "https://trouverunlogement.lescrous.fr/"
DSE_PLATEFORME_URL = "https://messervices.etudiant.gouv.fr/"
PARCOURSUP_OFFICIAL_RELEASE = "https://www.education.gouv.fr/parcoursup-2026-ouverture-le-19-janvier-de-la-phase-d-inscription-et-de-formulation-des-voeux-468674"
MONMASTER_OFFICIAL_RELEASE = "https://www.enseignementsup-recherche.gouv.fr/fr/mon-master-le-calendrier-de-la-procedure-pour-l-annee-universitaire-2026-2027-100230"
DSE_OFFICIAL_RELEASE = "https://www.lescrous.fr/dse/"
LAST_UPDATED = "2026-05-08"


_PLATFORM_DEFAULT_URLS: dict[str, str] = {
    "Parcoursup": PARCOURSUP_URL,
    "MonMaster": MONMASTER_URL,
    "DSE": DSE_URL,
}

_PLATFORM_OFFICIAL_RELEASES: dict[str, str] = {
    "Parcoursup": PARCOURSUP_OFFICIAL_RELEASE,
    "MonMaster": MONMASTER_OFFICIAL_RELEASE,
    "DSE": DSE_OFFICIAL_RELEASE,
}


def _entry(
    fragment_id: str,
    plateforme: str,
    phase: str,
    libelle: str,
    text: str,
    date_debut: str,
    date_fin: str | None = None,
    annee: int = 2026,
    url: str | None = None,
    source_label: str | None = None,
) -> dict[str, Any]:
    """Construit une entrée corpus calendrier."""
    plate_slug = plateforme.lower()
    return {
        "id": f"calendrier:{plate_slug}-{annee}:{fragment_id}",
        "domain": "calendrier",
        "source": f"{plate_slug}_calendrier_officiel",
        "annee": annee,
        "plateforme": plateforme,
        "phase": phase,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "libelle": libelle,
        "text": text,
        "url": url or _PLATFORM_DEFAULT_URLS.get(plateforme, PARCOURSUP_URL),
        "provenance": {
            "tier": "tier_1",
            "source_label": source_label or f"{plateforme} officiel",
            "last_updated": LAST_UPDATED,
            "official_release": _PLATFORM_OFFICIAL_RELEASES.get(plateforme, ""),
        },
    }


# ─────────────── Parcoursup 2026 — dates officielles vérifiées ───────────────

PARCOURSUP_2026_ENTRIES: list[dict[str, Any]] = [
    _entry(
        "consultation-offre",
        "Parcoursup", "ouverture",
        "Consultation de l'offre de formation Parcoursup 2026",
        "Le 17 décembre 2025, les futurs étudiants peuvent consulter l'offre de formation Parcoursup 2026. Cette phase d'information préalable permet d'explorer les ~22 000 formations disponibles, lire leurs critères d'admission, leurs attendus, leurs taux d'accès, et préparer son projet d'orientation. C'est l'étape pour discuter avec son professeur principal et son Psy-EN avant de formuler les vœux.",
        date_debut="2025-12-17",
    ),
    _entry(
        "ouverture-voeux",
        "Parcoursup", "voeux",
        "Ouverture de la phase d'inscription et formulation des vœux Parcoursup 2026",
        "Les candidats Parcoursup 2026 peuvent s'inscrire et formuler leurs vœux à partir du 19 janvier 2026. Chaque candidat peut formuler jusqu'à 10 vœux principaux non hiérarchisés (= sans ordre de préférence indiqué) + 10 vœux supplémentaires en apprentissage. Pas besoin de choisir l'ordre maintenant, ce sera demandé lors de la phase d'admission.",
        date_debut="2026-01-19",
    ),
    _entry(
        "date-limite-voeux",
        "Parcoursup", "voeux",
        "Date limite de formulation des vœux Parcoursup 2026",
        "La date limite pour formuler les vœux sur Parcoursup 2026 est le 12 mars 2026. Au-delà de cette date, il n'est plus possible d'ajouter de nouveaux vœux principaux. Pour les formations en apprentissage, des vœux peuvent encore être formulés après le 1er avril 2026. Les candidats doivent valider leurs 10 vœux maximum avant cette deadline.",
        date_debut="2026-03-12",
    ),
    _entry(
        "date-limite-confirmation",
        "Parcoursup", "voeux",
        "Date limite de confirmation des vœux Parcoursup 2026",
        "Les candidats Parcoursup 2026 ont jusqu'au 1er avril 2026 pour confirmer leurs vœux et finaliser leur dossier (lettre de motivation, choix de spécialités, pièces justificatives). Sans cette confirmation, les vœux ne sont pas pris en compte par les formations. C'est l'étape critique avant la phase d'admission.",
        date_debut="2026-04-01",
    ),
    _entry(
        "phase-admission",
        "Parcoursup", "admission",
        "Phase d'admission Parcoursup 2026 — début des réponses",
        "La phase principale d'admission Parcoursup 2026 commence le 2 juin 2026. Les candidats reçoivent leurs propositions d'admission et doivent y répondre dans les délais (3-5 jours selon la phase). Trois réponses possibles par formation : oui (acceptation définitive), oui en attente (place en liste d'attente), non. Cette phase dure jusqu'à mi-juillet.",
        date_debut="2026-06-02",
    ),
    _entry(
        "phase-complementaire",
        "Parcoursup", "complementaire",
        "Phase complémentaire Parcoursup 2026",
        "La phase complémentaire Parcoursup 2026 ouvre le 11 juin 2026 et se termine le 10 septembre 2026. Elle permet aux candidats sans proposition d'admission ou en attente longue de formuler 10 nouveaux vœux dans les formations qui ont des places vacantes. Particulièrement utile pour les candidats refusés partout en phase principale. Les commissions d'accès à l'enseignement supérieur (CAES) accompagnent aussi les candidats à ce stade.",
        date_debut="2026-06-11",
        date_fin="2026-09-10",
    ),
    _entry(
        "fin-phase-complementaire",
        "Parcoursup", "complementaire",
        "Fin de la phase complémentaire Parcoursup 2026",
        "La phase complémentaire Parcoursup 2026 se termine le 10 septembre 2026. C'est la dernière échéance pour les candidats qui n'ont pas reçu de proposition d'admission. Au-delà, il faut se tourner vers les formations hors Parcoursup ou attendre la rentrée 2027.",
        date_debut="2026-09-10",
    ),
    _entry(
        "inscription-administrative",
        "Parcoursup", "inscription",
        "Inscription administrative dans l'établissement choisi (Parcoursup 2026)",
        "Une fois une proposition d'admission acceptée définitivement sur Parcoursup, le candidat doit procéder à l'inscription administrative dans l'établissement (université, école). Les modalités et dates précises sont communiquées par chaque établissement, généralement entre fin juillet et début septembre 2026. Cette étape valide définitivement la place et permet le paiement des frais.",
        date_debut="2026-07-15",
        date_fin="2026-09-15",
    ),
]


# ─────────────── MonMaster 2026 — dates officielles vérifiées ───────────────

MONMASTER_2026_ENTRIES: list[dict[str, Any]] = [
    _entry(
        "ouverture-inscription",
        "MonMaster", "ouverture",
        "Ouverture de la plateforme MonMaster 2026",
        "MonMaster 2026 ouvre le 2 février 2026 pour l'année universitaire 2026-2027. Les candidats à un Master peuvent à partir de cette date créer leur compte sur la plateforme et remplir leur dossier commun (CV, cursus post-bac, relevés de notes, projet professionnel). Cette étape est obligatoire avant de candidater. MonMaster est la plateforme nationale unique pour candidater en Master en France.",
        date_debut="2026-02-02",
    ),
    _entry(
        "depot-candidatures",
        "MonMaster", "candidatures",
        "Phase de dépôt des candidatures MonMaster 2026",
        "Les candidats déposent leurs candidatures sur MonMaster du 17 février au 17 mars 2026. Chaque candidat peut formuler jusqu'à 15 candidatures de Masters en formation initiale + 15 en alternance. Les pièces obligatoires : CV, lettre de motivation, projet professionnel, relevés de notes. La date limite ferme du 17 mars est stricte — pas de prolongation.",
        date_debut="2026-02-17",
        date_fin="2026-03-17",
    ),
    _entry(
        "examen-dossiers",
        "MonMaster", "examen",
        "Examen des dossiers et convocations MonMaster 2026",
        "À partir du 21 mars 2026, les établissements examinent les dossiers MonMaster 2026 et envoient des convocations aux entretiens ou épreuves écrites prévus pour certaines formations sélectives. Les candidats doivent rester attentifs à leur boîte mail et à la plateforme pendant cette phase pour ne pas manquer une convocation.",
        date_debut="2026-03-21",
    ),
    _entry(
        "phase-admission",
        "MonMaster", "admission",
        "Phase d'admission MonMaster 2026 — réponses des formations",
        "La phase d'admission MonMaster 2026 commence le 3 juin 2026 et se prolonge jusqu'au 16 juin 2026 pour la première vague de réponses. Les candidats reçoivent les réponses des formations : admis (avec délai 7 jours pour accepter), en liste d'attente, ou refusé. Plusieurs admissions simultanées possibles — le candidat doit n'en garder qu'une seule au final, et libère les autres places.",
        date_debut="2026-06-03",
        date_fin="2026-06-16",
    ),
    _entry(
        "phase-complementaire",
        "MonMaster", "complementaire",
        "Phase complémentaire MonMaster 2026",
        "La phase complémentaire MonMaster 2026 démarre le 19 juin 2026 et se termine le 19 juillet 2026. Elle permet aux candidats sans admission ou en attente de formuler de nouveaux vœux dans les Masters qui ont encore des places vacantes. C'est une seconde chance pour les candidats refusés en phase principale ou ayant changé d'avis.",
        date_debut="2026-06-19",
        date_fin="2026-07-19",
    ),
    _entry(
        "inscription-administrative",
        "MonMaster", "inscription",
        "Inscription administrative en Master post-MonMaster 2026",
        "Une fois une admission acceptée définitivement sur MonMaster, le candidat procède à l'inscription administrative auprès de l'université d'accueil. Les modalités et dates précises sont communiquées par chaque université (généralement entre juillet et septembre 2026). Cette étape inclut le paiement des frais d'inscription : 175 € par an pour le Master en université publique en 2025-2026 (boursiers exonérés).",
        date_debut="2026-07-01",
        date_fin="2026-09-30",
    ),
]


# ─────────────── DSE (Dossier Social Étudiant) 2026 — bourse + logement CROUS ───────────────
#
# Sources WebSearch officielles (2026-05-08) :
# - https://www.lescrous.fr/dse/
# - https://www.etudiant.gouv.fr/fr/bourse-et-logement-constituez-votre-dossier-social-etudiant-dse-409
# - https://messervices.etudiant.gouv.fr/
# - https://www.education.gouv.fr/bo/2026/Hebdo9/ESRS2604201C (BO modalités bourses 2026-2027)
#
# Le DSE est le dossier UNIQUE pour demander à la fois la bourse sur critères
# sociaux ET un logement en résidence CROUS. Plateforme : MesServices.etudiant.gouv.fr.

DSE_2026_ENTRIES: list[dict[str, Any]] = [
    _entry(
        "ouverture-dse",
        "DSE", "ouverture",
        "Ouverture du Dossier Social Étudiant (DSE) 2026",
        "Le Dossier Social Étudiant (DSE) 2026 ouvre le 2 mars 2026 sur la plateforme MesServices.Étudiants.gouv.fr. Le DSE est le dossier UNIQUE pour demander à la fois une bourse sur critères sociaux ET un logement en résidence CROUS pour l'année universitaire 2026-2027. Constituer son dossier dès l'ouverture est conseillé pour être prioritaire.",
        date_debut="2026-03-02",
        url=DSE_PLATEFORME_URL,
        source_label="Étudiant.gouv (DSE officiel)",
    ),
    _entry(
        "date-limite-recommandee",
        "DSE", "deadline",
        "Date limite recommandée DSE 2026 (priorité bourse + logement CROUS)",
        "La date limite recommandée pour finaliser son DSE 2026 est le 31 mai 2026. Les dossiers traités avant cette date sont prioritaires pour l'attribution de la bourse sur critères sociaux ET d'un logement en résidence CROUS. Au-delà du 31 mai, le DSE reste possible mais les chances d'obtenir un logement sont fortement réduites (places attribuées en priorité aux dossiers complets avant cette date).",
        date_debut="2026-05-31",
    ),
    _entry(
        "saisie-voeux-logement",
        "DSE", "logement",
        "Phase de saisie des vœux de logement CROUS 2026",
        "Du 5 mai 2026 (10h) au 1er juin 2026 (10h, heure de Paris), les étudiants peuvent saisir jusqu'à 10 vœux de logement CROUS sur trouverunlogement.lescrous.fr, toutes villes et CROUS confondus. Cette phase est OBLIGATOIRE en plus du DSE pour postuler à un logement spécifique en résidence universitaire. Les 10 vœux peuvent être hiérarchisés.",
        date_debut="2026-05-05",
        date_fin="2026-06-01",
        url=DSE_LOGEMENT_URL,
        source_label="trouverunlogement.lescrous.fr (CROUS)",
    ),
    _entry(
        "premier-cycle-attribution-logement",
        "DSE", "logement",
        "Premier cycle d'attribution des logements CROUS 2026",
        "Le premier cycle d'attribution des logements CROUS pour la rentrée 2026 a lieu le 2 juin 2026. Les étudiants ayant fait leur DSE et saisi leurs vœux de logement reçoivent les premières propositions. Deux autres cycles d'attribution suivent les semaines suivantes, jusqu'au 5 juillet 2026.",
        date_debut="2026-06-02",
        date_fin="2026-07-05",
        url=DSE_LOGEMENT_URL,
        source_label="lescrous.fr (CROUS officiel)",
    ),
    _entry(
        "vue-ensemble-dse-2026",
        "DSE", "general",
        "Calendrier général DSE + logement CROUS 2026 (vue d'ensemble)",
        "Le calendrier du Dossier Social Étudiant (DSE) 2026 pour bourse et logement CROUS se déroule en 4 phases : (1) ouverture DSE le 2 mars 2026 sur MesServices.etudiant.gouv.fr ; (2) saisie des vœux de logement du 5 mai au 1er juin 2026 sur trouverunlogement.lescrous.fr (10 vœux max) ; (3) date limite recommandée 31 mai 2026 pour être prioritaire bourse + logement ; (4) cycles d'attribution logement du 2 juin au 5 juillet 2026. Le DSE est le dossier UNIQUE pour bourse sur critères sociaux ET logement en résidence universitaire.",
        date_debut="2026-03-02",
        date_fin="2026-07-05",
    ),
]


# ─────────────── Vues d'ensemble (questions générales) ───────────────

OVERVIEW_ENTRIES: list[dict[str, Any]] = [
    _entry(
        "vue-ensemble-2026",
        "Parcoursup", "general",
        "Calendrier général Parcoursup 2026 (vue d'ensemble)",
        "Le calendrier Parcoursup 2026 se déroule en 6 phases clés : (1) consultation offre du 17 décembre 2025 au 19 janvier 2026 ; (2) inscription + formulation des vœux du 19 janvier au 12 mars ; (3) confirmation des vœux jusqu'au 1er avril ; (4) phase principale d'admission du 2 juin à mi-juillet ; (5) phase complémentaire du 11 juin au 10 septembre ; (6) inscription administrative dans l'établissement entre juillet et septembre. Toutes les dates précises sont sur parcoursup.fr.",
        date_debut="2025-12-17",
        date_fin="2026-09-15",
    ),
    _entry(
        "vue-ensemble-2026",
        "MonMaster", "general",
        "Calendrier général MonMaster 2026 (vue d'ensemble)",
        "Le calendrier MonMaster 2026 se déroule en 5 phases clés pour l'année universitaire 2026-2027 : (1) ouverture inscription + dossier commun le 2 février 2026 ; (2) phase de candidature du 17 février au 17 mars (15 vœux max formation initiale + 15 alternance) ; (3) examen des dossiers à partir du 21 mars (convocations entretiens) ; (4) phase d'admission du 3 au 16 juin ; (5) phase complémentaire du 19 juin au 19 juillet. Toutes les dates précises sont sur monmaster.gouv.fr.",
        date_debut="2026-02-02",
        date_fin="2026-09-30",
    ),
]


def build_calendrier_corpus() -> list[dict[str, Any]]:
    """Construit le corpus calendrier (Parcoursup + MonMaster + DSE + vues d'ensemble)."""
    entries = []
    entries.extend(PARCOURSUP_2026_ENTRIES)
    entries.extend(MONMASTER_2026_ENTRIES)
    entries.extend(DSE_2026_ENTRIES)
    entries.extend(OVERVIEW_ENTRIES)
    return entries


def main() -> int:
    entries = build_calendrier_corpus()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Calendrier corpus écrit : {OUT_PATH} ({len(entries)} entrées)")
    print(f"  Parcoursup 2026 : {len(PARCOURSUP_2026_ENTRIES)} dates (officielles WebSearch 2026-05-08)")
    print(f"  MonMaster 2026  : {len(MONMASTER_2026_ENTRIES)} dates (officielles WebSearch 2026-05-08)")
    print(f"  DSE CROUS 2026  : {len(DSE_2026_ENTRIES)} dates (bourse + logement, officielles)")
    print(f"  Vues d'ensemble : {len(OVERVIEW_ENTRIES)} entrées")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
