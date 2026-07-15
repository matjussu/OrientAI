# Audit Phase 0 v5 — Gate 1 (2026-05-10)

> Phase C.3 du plan corpus v5 (ADR-057). Vérifie que `formations_v5.json`
> satisfait les métriques de Gate 1 avant Gate 2 (mini-bench v4.1) et
> Gate 3 (spot-check manuel).

## Verdict global : ⚠ NO-GO — métrique critique au rouge non-structurel

- Métriques vertes : 4
- Métriques orange : 3
- Métriques rouge : 1 (dont 0 bloquantes)

## Résumé corpus

- **Path** : `data/processed/formations.json`
- **Total fiches** : 47220
- **Formations principales** : 33776
- **Annexes (avec `domain`)** : 13444

## Métriques détaillées

| Métrique | Valeur | Cible | Statut |
|---|---:|---|:-:|
| `total_fiches` | 47220 | ≥40000 | ✓ |
| `doublons_pct` | 0.0 | <5% | ✓ |
| `cereq_residual` | 0 | 0 (ADR-054) | ✓ |
| `domain_coverage_pct` | 28.5 | ≥28% | ✓ |
| `url_verifiable_pct` | 33.2 | ≥40% | ⚠ |
| `sans_region_formations_pct` | 41.5 | ≤10% | ✗ |
| `sans_niveau_formations_pct` | 20.9 | ≤15% | ⚠ |
| `median_chiffres_density` | 2.0 | ≥3 | ⚠ |
| `insertion_pro_pct` | 31.3 | 30-40% (informatif) | ℹ |

## Limites structurelles connues (orange acceptable)

Ces métriques peuvent être orange sans bloquer Phase C, car elles
viennent de limites structurelles du data sous-jacent (Phase 3 du
plan v5 corrigera) :

1. **Sans région ~41%** : 14 007 fiches RNCP/ONISEP/LBA sont des fiches
   nationales sans implantation géographique structurellement (titres
   anonymes, descriptions génériques, offres distantes). Le mapping
   ville→région du Stage 5 NORMALIZE fonctionne mais ces fiches
   n'ont pas de `ville` à mapper.
2. **URL ~33%** : amélioration Phase 3.8 prévue (fallback ONISEP search).
3. **insertion_pro ~25%** : voulu défensif ADR-054. Les fiches qui n'ont
   pas de match InserSup spécifique laissent `null` plutôt que d'agréger
   un Cereq trompeur. R1 du contrat strict v4 fait son travail.

## Distribution domain (top 10)

| Domain | Fiches |
|---|---:|
| `__none__` | 33776 |
| `competences_certif` | 4891 |
| `formation_insertion` | 2693 |
| `metier` | 2150 |
| `metier_detail` | 1584 |
| `metier_prospective` | 1160 |
| `insertion_pro` | 608 |
| `parcours_bacheliers` | 151 |
| `insee_salaire` | 59 |
| `crous` | 45 |
| `financement_etudes` | 28 |
| `calendrier` | 21 |

## Distribution tier (ADR-055)

| Tier | Fiches |
|---|---:|
| `tier_1` | 47207 |
| `tier_2` | 13 |

## Sources principales (top 10)

| Source | Fiches |
|---|---:|
| `parcoursup` | 8191 |
| `monmaster` | 7573 |
| `rncp` | 5181 |
| `rncp_blocs` | 4891 |
| `onisep` | 4758 |
| `inserjeunes_cfa` | 4065 |
| `labonnealternance` | 4008 |
| `inserjeunes_lycee_pro` | 2693 |
| `rome_api_v4` | 1584 |
| `dares_metiers_2030` | 1160 |

## Critère Gate 1 (résumé)

✓ **GO Gate 2** si :
- 0 métrique rouge bloquante (Cereq résiduel)
- 0 métrique rouge non-bloquante

⚠ **GO conditionnel** si :
- Seules des métriques orange sont présentes ET sont expliquées par
  des limites structurelles documentées (régions, URLs, insertion).

❌ **NO-GO** si :
- Cereq résiduel (ADR-054 violé)
- Doublons >10% (Stage 3 cassé)
- Domain coverage <20% (corpora annexes pas intégrés)
- Total fiches <30k (data manquant)
