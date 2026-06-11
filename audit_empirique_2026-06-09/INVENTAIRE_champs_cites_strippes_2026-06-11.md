# Inventaire complet — champs cités-par-le-modèle mais strippés au juge (3e occurrence)

Jalon 2 ordre 2000. Demande Jarvis : inventaire complet pour capitaliser le pattern.

## Cause racine (le pattern qui se répète)

Le générateur et le juge voient DEUX projections différentes de la même fiche :

- **Générateur** reçoit `FactCard.to_dict()` via `format_sources_for_llm` (src/rag/fact_card.py).
- **Juge** reçoit `_serialize_sources -> _extract_fiche` filtré par `_FICHE_KEEP` sur la
  fiche RAW (audit_empirique_2026-06-09/run_battery.py).

À chaque fois que `fact_card` expose un nouveau champ, `_FICHE_KEEP` doit être re-synchronisé
manuellement, sinon le juge devient aveugle sur ce que le générateur a réellement cité ->
faux flags (hallucination sur une citation pourtant sourcée, ou mismatch raté).

Occurrences du pattern :
1. Bloc A (2026-06-09) : taux_admission/capacite/n_candidats_pp/... -> fixé.
2. C2a (2026-06-09) : voies_acces -> fixé.
3. **text_libre + name-cascade + salaire INSEE (2026-06-11, ce jalon)** -> fixé ci-dessous.

## Inventaire complet des champs exposés-générateur MAIS strippés-juge (avant ce fix)

Mesuré empiriquement sur les partitions que les questions salaire retrievent
(insee_salaire 59, metier 4894, rncp 10072 fiches) :

| # | champ raw | exposé au générateur via | impact |
|---|---|---|---|
| 1 | **`text` / `detail`** | FactCard.text_libre | SYSTÉMIQUE — 100% des fiches INSEE/metier/RNCP. Toute citation de texte libre : salaire INSEE, descriptions métier, intitulés/descriptions RNCP. C'est ICI que le modèle LIT le salaire (fact_card ne l'extrait pas en chiffres structurés). |
| 2 | name-cascade : `libelle_metier`, `nom_metier`, `libelle`, `intitule`, `libelle_diplome`, `libelle_formation`, `fap_libelle`, `subject`, `discipline`, `grande_discipline` | FactCard.formation (_pick_formation_name) | Sans ça le juge voit `"?"` pour l'identité de la source (fiches metier/INSEE/stats sans `nom`). C'est pourquoi S2/S3/S5 de metier-002 se sérialisaient en `"?"`. |
| 3 | salaire INSEE structuré : `salaire_net_median_annuel`, `salaire_net_median_mensuel`, `salaire_net_q1_mensuel`, `salaire_net_q3_mensuel`, `salaire_brut_median_annuel`, `cs_libelle`, `cs_code`, `pcs_group_label`, `effectif_total`, `discipline_agregee`, `taux_insertion`, `part_cadre` | lus par le générateur via `text` (pas en chiffres) | Le juge peut désormais vérifier le CHIFFRE et le QUALIFICATIF brut/net (net ET brut explicitement étiquetés en source) -> instrument du garde-fou salaire volet b. |
| 4 | mineurs : `duree`, `frais_annuels`, `selectivite_code`, `domain`, `url`, `provenance` | FactCard (champs directs) | citations ponctuelles (durée formation, frais, sélectivité). |

Déjà synchronisés (aucune action) : `insertion_pro` (le juge dérive taux_emploi_*/salaire_median_embauche),
`trends` (tendance_acces), `voies_acces` (dispositifs_reconversion), `profil_admis`,
`taux_admission`/`capacite`/`n_candidats_pp`/`n_acceptes_total`/`rang_dernier_appele`/`alternance`.

## Fix appliqué (additif, ce jalon)

`_FICHE_KEEP` étendu avec items 1-4 ci-dessus. `_extract_fiche` tronque `text`/`detail` à
600 chars (parité avec fact_card.text_libre, capture la chaîne salaire INSEE complète sans
gonfler le contexte juge). Vérifié : fiche INSEE sérialise maintenant `text` + salaire_net_*
+ cs_libelle ; fiche metier sérialise `text` + nom. Le juge n'est plus semi-aveugle.

Additif strict : on AJOUTE des champs à la vue du juge, on n'en retire aucun -> instrument
strictement moins aveugle = strictement meilleur. Les mesures subset before/after utilisent
ce MÊME instrument des deux côtés (constance respectée).

## Fix DURABLE proposé (séparé, hors deadline)

Faire que `_serialize_sources` produise directement `fiche_to_fact_card(fiche).to_dict()` :
le juge verrait EXACTEMENT le contexte du générateur, ce qui tue le pattern de re-synchro
manuelle pour de bon. Changement structurel -> `/propose-dev` post-VivaTech (pas sous deadline).
