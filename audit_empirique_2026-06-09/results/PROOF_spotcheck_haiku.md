# Spot-check du juge Haiku (validation en session, Claudette/Max)

Date : 2026-06-09. But : valider que le juge Haiku (bulk, script) juge correctement, par un contrôle inter-juge en session (Max, sans coût API). 10 cas stratifiés.

## Verdicts (accord Claudette vs Haiku)

| id | Question | Verdict Haiku | Mon verdict (Max) | Accord |
|---|---|---|---|---|
| fact-024 | date Parcoursup 2026 | hallu (1er avril inventé, [S2] vide) | hallu confirmée (date inventée, probablement fausse) | OUI |
| fact-025 | date Parcoursup 2025 | hallu (même 1er avril 2026) | hallu confirmée | OUI |
| fact-003 | salaire BUT TC Bordeaux | metric_substitution + hallu | substitution confirmée (insertion d'autres BUT) | OUI |
| hp-010 | études kiné | grnd 0.8, hallu (~3% IFMK inventé) | correct : 3 formations sourcées + 1 stat inventée | OUI |
| fact-004 | places BUT GEA Lille | grounded 1.0 (173 places=source) | confirmé sourcé | OUI |
| fact-009 | places droit Montpellier | grounded 1.0 | confirmé sourcé | OUI |
| fact-002 | insertion BUT GEII IdF | metric_substitution (refuse alors que S1 a le taux 6m) | confirmé : FAUX refus, donnée présente | OUI |
| fact-012 | insertion maths Brest | metric_substitution (S1 a 45.83%) | confirmé : FAUX refus | OUI |
| fact-001 | taux accès BUT Info Lyon | honest_refusal | confirmé (sur-refus mais honnête) | OUI |
| fact-005 | frais BTS SIO Toulouse | honest_refusal | confirmé | OUI |

Accord : 10/10. Le juge Haiku est FIABLE sur cet échantillon, et n'over-flag PAS l'hallucination : chaque flag est justifié (date inventée, stat nationale inventée, chiffres non sourcés). La bascule Sonnet->Haiku ne dégrade pas la qualité de jugement.

## NOUVEAU finding révélé par le juge (à intégrer Phase A)

Le juge a mis en évidence un mode d'échec que l'audit 42q n'avait pas isolé : le **FAUX REFUS sur donnée disponible**. Sur fact-002 et fact-012, le système répond "je n'ai pas le taux d'insertion à 6 mois" ALORS QUE la source contient `insertion_pro.taux_emploi_6m` (0.4737, 0.4583). Il refuse/substitue une donnée qu'il A. Ce n'est pas un trou de data (L3) mais un problème de GÉNÉRATION/lecture : le prompt ne lit pas le bloc insertion_pro, ou le format FactCard ne l'expose pas au générateur.

Implication Phase A2 : au-delà d'"interdire la substitution", il faut s'assurer que le générateur EXPLOITE les champs insertion présents (exposer insertion_pro.taux_emploi_* dans la FactCard). Une partie du sur-refus/substitution vient de données présentes mais non lues, pas de données absentes.
