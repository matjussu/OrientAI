# Concordance avec la page publique : rapport (25/09/2026)

Ordre `2026-09-25-1320-claudette-orientai-concordance-page-publique`. Contrat : `CONTRAT.md` de ce dossier (v0.1,
GO de Jarvis à 13h23, constats datés §11-12). Chaque chiffre cite son fichier.

## 1. Le contrôle (bloquant, 100 % des formations) : vert

`python -m src.eval.concordance` ; résultat `ecarts.json`.

- 3945 formations, couverture 100%, 25747 chiffres de page comparés à
  ce que voit le modèle (`lire_fiche`), **0 écart inexpliqué**, **0 doublon montré**.
- Cases : concordante 3202, page_sans_bloc_acces 388, page_vide 273, master_sans_fiche_annee_en_cours 82.
- **Témoins** (règle 9), joués dans le même run : chiffre de page +1 dans la base (`ORIENTIA_SABOTAGE_C=concordance_valeur`)
  : code 1, rougit ; doublon remis dans la sortie
  (`ORIENTIA_SABOTAGE_CONCORDANCE=doublon`) : code 1, rougit.
- Indépendance : le contrôle lit les pages avec `html.parser` et ses propres motifs ; test croisé avec le parseur du
  constructeur sur les 88 pages de l'inventaire de Jarvis, mêmes chiffres (`tests/test_concordance.py`). Contrôle
  positif du parseur contre l'inventaire : 962 lignes, 0 écart (`tests/test_pages_publiques.py`).
- Défaut trouvé par ce contrôle en cours de route : l'arrondi des taux MonMaster (18 écarts d'une unité), tranché par
  le rendu réel de deux fiches (demi supérieur), corrigé (`CONTRAT.md` §12).

## 2. Relevé

`manifeste_releve.json` : 3945 formations, 0 échec, 3643 fichiers (masters groupés
par établissement et mention), empreinte du cache `05492e1eff77`, 5654 s à une requête par
1,5 s au plus. Cache hors dépôt : `data/raw/pages_publiques/`.

## 3. Formations absentes de la session en cours (jamais présentées comme actuelles)

`formations_absentes_session_en_cours.json` : 273 pages Parcoursup vides (psup 135, apprentissage 138) et
82 masters sans fiche MonMaster 2026. Champ `fiche_publique_annee_en_cours = absente`, montré au modèle.

Cause des pages vides **établie** (`pages_vides.json`) : relues une fois chacune, 0 revient pleine ; 0 dans la
cartographie ESR 2026 ; 264 dans celle de 2025 ; témoin de 20 pages pleines tirées avec
une graine fixe : 20/20 dans la cartographie 2026.

## 4. Places 2025 : la page contre l'open data (ajout A)

Le modèle voit les places de la page. L'open data (`capa_fin`) diffère sur **240 formations**, pas 4 :
ifsi 228, diplome_sante 6, autre 3, bts 2, ecole_ingenieur 1. Liste un par un : `ecarts.json`, clé
`places_page_contre_open_data`. Ce n'est pas un parseur : les deux parseurs lisent la même valeur de page. **Cause non
établie** ; la concentration sur les IFSI ne s'explique pas par la seule « capacité relevée pendant la procédure »
(supposé, non vérifié : capacités IFSI révisées après la procédure).

## 5. Chiffres vus par le modèle (ajout B)

Valeurs numériques disponibles par fiche, avant (base du 23/09, tout était montré) et après ce lot
(`ecarts.json`, `chiffres_vus_par_le_modele`) :

| Espace | Fiches | Avant : médiane (min à max) | Après : médiane (min à max) |
|---|---|---|---|
| psup | 2939 | 49 (23 à 81) | 41 (15 à 72) |
| psup_app | 526 | 8.0 (8 à 8) | 8.0 (8 à 8) |
| mm | 480 | 12.0 (6 à 12) | 12.0 (4 à 13) |

Le lot n'ajoute aucun chiffre (places et vœux 2026 stockés, non montrés, en attente de Matteo). Lignes d'insertion,
inchangées : médiane 1 par fiche. Champs montrés au modèle après ce lot :

- `psup` (67 champs) : `alternance`, `candidats_classes`, `candidats_ont_choisi_d_integrer`, `candidats_ont_postule`, `candidats_ont_pu_recevoir_une_proposition`, `capacites_mmopk_kinesitherapie_las`, `capacites_mmopk_kinesitherapie_pass`, `capacites_mmopk_kinesitherapie_total`, `capacites_mmopk_maieutique_las`, `capacites_mmopk_maieutique_pass`, `capacites_mmopk_maieutique_passerelles`, `capacites_mmopk_maieutique_total`, `capacites_mmopk_medecine_las`, `capacites_mmopk_medecine_pass`, `capacites_mmopk_medecine_passerelles`, `capacites_mmopk_medecine_total`, `capacites_mmopk_odontologie_las`, `capacites_mmopk_odontologie_pass`, `capacites_mmopk_odontologie_passerelles`, `capacites_mmopk_odontologie_total`, `capacites_mmopk_pharmacie_las`, `capacites_mmopk_pharmacie_pass`, `capacites_mmopk_pharmacie_passerelles`, `capacites_mmopk_pharmacie_total`, `capacites_mmopk_total`, `cout`, `cout.cvec_eur`, `cout.droits_inscription_eur`, `cout.fourchette_max_eur`, `cout.fourchette_min_eur`, `cout.gratuit_boursiers`, `cout.gratuit_en_apprentissage`, `cout.scolarite_annuel_eur`, `cout.scolarite_total_eur`, `effectif_cohorte_national`, `insertion`, `part_acces_general`, `part_acces_pro`, `part_acces_techno`, `part_admis_debut_pp`, `part_boursiers`, `part_femmes`, `part_meme_academie`, `part_mention_ab`, `part_mention_b`, `part_mention_sans_mention`, `part_mention_tb`, `part_mention_tbf`, `part_neobacheliers`, `passage_mmopk_1_an_national`, `passage_mmopk_1_ou_2_ans_national`, `passage_mmopk_2_ans_national`, `passage_mmopk_kinesitherapie_national`, `passage_mmopk_maieutique_national`, `passage_mmopk_medecine_national`, `passage_mmopk_odontologie_national`, `passage_mmopk_pharmacie_national`, `passage_pass_las_ensemble_national`, `places`, `repartition_admis_autres`, `repartition_admis_bac_general`, `repartition_admis_bac_pro`, `repartition_admis_bac_techno`, `sante.capacites_universite`, `sante.passage_national`, `taux_acces`, `voeux_phase_principale`
- `psup_app` (8 champs) : `cout`, `cout.gratuit_pour_l_apprenti`, `places`, `propositions_envoyees_bilan_final`, `refus_apres_examen`, `refus_faute_de_place`, `voeux_recherche_contrat`, `voeux_toutes_phases_bilan_final`
- `mm` (14 champs) : `acceptes_total`, `alternance`, `candidatures_campagne_precedente`, `capacite_accueil`, `part_acceptes_but`, `part_acceptes_femmes`, `part_acceptes_licence_generale`, `part_acceptes_licence_pro`, `part_acceptes_meme_etablissement`, `propositions_total`, `rang_dernier_appele`, `taux_acces`, `taux_candidatures_classees`, `taux_propositions_parmi_classes`

## 6. Juge

Rejugement des 113 réponses de la référence : addendum du `RAPPORT.md` de `results/multiversion/2026-09-25_reference/`.
