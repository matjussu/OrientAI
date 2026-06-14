# Audit raw — 11 schémas bruts restants (complément #140)

Ordre : 2026-06-14-1307-claudette-orientai-audit-raw-schemas-restants
Auteur : Claudette · Date : 2026-06-14 · Read-only.

Complète #140 (qui couvrait parcoursup + insersup + la couche ingéré-mais-non-exploité)
par le diff colonne-par-colonne des 11 sources restantes : raw -> corpus -> exploitation.

**Test STRICT appliqué (consigne Jarvis)** : un candidat n'est "gratuit" que si le signal
existe SUR LES FICHES QUI MANQUENT LA CIBLE — pas un taux de présence agrégé. Ce test a
tué cfa niveau (cf §3) et validé onisep niveau / lycée_pro insertion.

---

## 0. CONCLUSION HEADLINE — il n'y a quasi PAS de couche "raw-not-ingested"

Diff raw vs fiche corpus, par source :

| Source | raw-not-ingested | Verdict |
|---|---|---|
| monmaster | AUCUN | tout ingéré |
| rncp | abrege_intitule(→type_diplome), intitule(→nom), numero_fiche(→rncp), niveau_intitule, validation_partielle, date_dernier_jo | renommés ou bas-valeur |
| rncp_blocs | AUCUN | tout ingéré |
| onisep | AUCUN | tout ingéré |
| inserjeunes_cfa | taux_emploi/part_*/valeur_ajoutee... (→ **insertion_pro** nested), niveau_orientia (**vide**) | nested dans insertion_pro |
| inserjeunes_lycee_pro | AUCUN (top-level) | mais stats hors insertion_pro (cf candidat #1) |
| labonnealternance | AUCUN | tout ingéré (mais source dormante) |
| rome | AUCUN | tout ingéré (text + structuré) |
| dares | AUCUN | tout ingéré |
| onisep_metiers | AUCUN | tout ingéré |
| onisep_ideo | competences/nature_travail/condition_travail/vie_professionnelle... (→ **text** folded), secteurs_activite(→secteurs), metiers_associes | foldés dans text ou renommés |
| ip_doc_doctorat | annee(→annee_cohorte), niveau_orientia, part_femmes | renommés/niche |

**Résultat : les collectes sont EXHAUSTIVES.** Tout "raw-not-ingested" se résout en
champ renommé, nested (insertion_pro), foldé dans `text`, ou vide à la source. Aucune
donnée brute n'est perdue à l'ingestion.

=> Le trou de couverture data n'est PAS un problème d'ingestion. C'est :
1. **Exploitation** : champ ingéré mais ne coule vers aucun des 4 canaux (déjà cartographié #140).
2. **Transform absent** : champ présent mais aucune étape ne le dérive (fili_code, type_enregistrement — corrigés 1230/1305).

L'effort d'enrichissement doit viser le WIRING vers les canaux et les TRANSFORMS, PAS
la re-collecte. C'est la réponse rassurante à "ne rien oublier de la data non utilisée" :
la data non utilisée n'est pas perdue, elle est non-câblée — et désormais inventoriée.

---

## 1. Candidats gratuits SUPPLÉMENTAIRES (post test strict, format #140)

### TIER 1 — passent le test strict, gratuits

1. **lycée_pro : stats emploi -> insertion_pro**. 1943 fiches ont `taux_emploi_12m_moyen`,
   2542 ont `taux_poursuite_etudes_moyen` AU TOP-LEVEL, mais **0 fiche n'a de bloc
   insertion_pro** -> invisibles à fact_card (alors que ces stats SONT le cœur insertion).
   Mapper top-level -> insertion_pro = stats citables. Gratuit (fact_card). **Strict : PASS.**
2. **onisep : niveau_certification -> niveau**. niveau vide sur 1276 onisep ; **1274
   ont niveau_certification** ('4','5','6'...). Mapper le niveau de certification RNCP
   (3→cap-bep, 4→bac, 5→bac+2, 6→bac+3, 7→bac+5, 8→bac+8 ; '0'→vide). ~1274 fiches.
   Gratuit (filtre niveau + BM25). **Strict : PASS.**

### TIER 2

3. **monmaster discipline -> dense**. `discipline` (100%) est déjà dans BM25 + fact_card
   mais PAS dans fiche_to_text (dense). `parcours` (91%) dans aucun canal. Gain BM25
   immédiat (parcours), dense = ajout à fiche_to_text (modif ADR-gatée à A/B).

### TIER 3 — niche / gated

4. ideo `metiers_associes` (cross-ref métiers proches, exploration carrière — structuré,
   pas juste text). 5. lba re-éligibilité (4008 dormantes, geopoint+rome riches —
   décision volume séparée). 6. doctorat `part_femmes`/`part_*` (niche, 240). 7. rncp
   `validation_partielle` (obtenable par blocs — info niche). 8. ideo gendered labels.

### DÉJÀ TRAITÉ / MORT (rappel)

- fili_code -> type_diplome : DONE (1230). rncp sur-demande -> Titre pro : DONE (1305).
- **cfa niveau : MORT** (cf §3). secteur : PARQUÉ post-VivaTech (taxonomies, verdict 1306).

---

## 2. Distinction raw-not-ingested vs ingéré-mais-non-exploité

- **raw-not-ingested** : ~inexistant (cf §0). Les collectes prennent tout.
- **ingéré-mais-non-exploité** : c'est LÀ que sont les gains (cf #140 §2-3 + §1 ci-dessus).
  Champs dans la fiche mais hors des 4 canaux (secteur, parcours, modalite_enseignement,
  academie...) ou présents mais non-dérivés vers un champ exploité (le pattern transform).

---

## 3. Le test strict en action — cfa niveau (vérif de ma propre conclusion)

`inserjeunes_cfa` a un champ `niveau_orientia` dans le raw -> à la présence-de-champ
naïve (#140-style), ça ressemblait à un signal pour combler le niveau cfa (0%). **Test
strict : `niveau_orientia` = None sur les 11314 records bruts.** Le champ existe, la
donnée non. Conclusion DROP confirmée (cohérent avec merge.py:681 "niveau: None côté
source, CFA agrégé"). C'est exactement le piège que le test strict évite : présence du
CHAMP ≠ présence du SIGNAL. Même nature que les 2 faux candidats 1305.

---

## 4. Méthode & limites

- Diff exhaustif des clés top-level raw (data/processed/<source>.json) vs clés de la fiche
  corpus, sur les 11 sources. Les mappings nested (insertion_pro) et foldés (text) sont
  signalés (un diff top-level seul les compterait à tort comme "non ingérés").
- Test strict appliqué à chaque candidat de fill avant ranking.
- Limite : je n'ai pas ré-audité parcoursup/insersup (faits #140). lba traité comme
  dormant (re-éligibilité = décision séparée). Le contenu réel des champs foldés dans
  `text` (rome competences, dares stats, ideo descriptions) est retrievable sémantiquement
  mais non structuré/filtrable — exposition structurée = candidat Tier 3 par source.
