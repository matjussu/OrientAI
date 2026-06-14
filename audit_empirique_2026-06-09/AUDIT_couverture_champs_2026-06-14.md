# Audit exhaustif — couverture des champs (raw -> corpus -> exploitation)

Ordre : 2026-06-14-1245-claudette-orientai-audit-couverture-champs-exhaustif
Auteur : Claudette · Date : 2026-06-14 · Read-only (aucune modif code/data).

But : pour chaque source, mapper quels champs existent et lesquels sont réellement
EXPLOITÉS par le modèle, pour ne plus jamais redécouvrir un trou par hasard
(pattern fili_code : donnée présente, jamais transformée en champ exploité).

---

## 0. Les 4 canaux d'exploitation (un champ "exploité" = lu par au moins un)

| Canal | Fonction | Coût refresh | Champs lus (formation path / annex path) |
|---|---|---|---|
| **Dense FAISS** | `fiche_to_text` | ré-embed gaté ~5-10$ | formation: nom, etablissement, ville, type_diplome, niveau, phase, statut, labels, domaine, departement, region, admission_stats, profil_admis, detail, debouches(libellé), insertion_pro(taux+salaire), signature école, mots-clés métier — annex(`domain`≠none): `[domain]`+region+libellé+`text`[:1500] |
| **BM25 lexical** | `_fiche_to_search_text` | rebuild local **$0** | nom/libelle*/intitule/fap_libelle/subject, text, detail, etablissement, ville, region, departement, type_diplome, niveau, discipline, domaine, id, codes_rome, debouches(libellé), sigle |
| **fact_card** (serve) | `build_fact_card` | live, **$0** | ~45 champs : admission, debouches, discipline, duree, insertion_pro(+salaire), mention, niveau, profil_admis, region, selectivite_code, statut, taux_*, trends, type_diplome, ville, voies_acces... |
| **Filtre** | metadata_filter / SELECT / geo | live, **$0** | metadata_filter: **region, niveau, alternance, budget, secteur** — SELECT: nom, etablissement, ville, niveau (+ salaire cible) — geo_coherence: ville, region |

Note clé : 3 canaux sur 4 (BM25, fact_card, filtre) sont **gratuits** (rebuild/lecture
locale). Seul le dense exige le ré-embed gaté. Donc remplir/mapper un champ dans
BM25/fact_card/filtre = gain immédiat sans dépense.

---

## 1. CAUSE RACINE — pourquoi type_diplome vide (parcoursup + monmaster)

**fili_code EST persisté** : `parcoursup.py:416` écrit `"fili_code": _clean_str(row.get(FILI_COLUMN))`
dans la fiche. Donc PAS un problème de persistance (corrige mon spoiler initial).

**Le trou = absence d'étape de DÉRIVATION** :
- `parcoursup.py` (build fiche, lignes ~341-417) pose niveau, fili_code, fili_groupe,
  form_lib_voe_acc... mais **n'assigne JAMAIS `type_diplome`**. Aucune ligne
  `type_diplome = map(fili_code)`.
- `stage_normalize` (run_merge_v3) a `_canonicalize_region/_niveau/_statut` +
  `_infer_region_from_ville` : il **canonise ce qui existe déjà**, il ne CRÉE pas
  type_diplome depuis fili_code. Pas de `_derive_type_diplome`.
- monmaster : aucune règle `source=monmaster -> Master` (niveau=bac+5 présent mais
  jamais transformé).

=> La donnée discriminante (fili_code, niveau, source) était là ; l'étape qui la
transforme en champ exploité manquait. **C'est exactement la brique générique
qu'ajoute `derive_fields` (Stage 5.95, ordre 1230).** Le pattern n'est pas "donnée
absente" mais "transform absent". Cet audit cherche tous les autres cas du même type.

---

## 2. MATRICE — présent-mais-non-exploité par source

Légende exploitation : **INVISIBLE** = dans aucun canal · **text-only** = sérialisé
dans le blob `text` annex (retrievable sémantique mais ni structuré, ni filtre, ni
fact_card) · **serve-only** = fact_card mais pas retrieval.

| Source (n) | Champ présent non exploité | Statut | Valeur potentielle |
|---|---|---|---|
| **parcoursup** (13011) | `fili_code` 100% | ~~INVISIBLE~~ **RÉSOLU 1230** | typage (fait) |
| | `form_lib_voe_acc` 37% | INVISIBLE | libellé type+champ ("BTS - Services") -> signal retrieval/typage secours |
| | `selectivite_code` 100% | serve-only | sélectivité -> pourrait pondérer/filtrer |
| **monmaster** (7573) | `secteur_discipline` 100% | **INVISIBLE** | **alimente le filtre `secteur` (mort)** |
| | `parcours` 91% | INVISIBLE | spécialisation master -> dense/BM25 (retrieval "master X parcours Y") |
| | `mention` 100% | serve-only | concept central master (partiel via nom) |
| | `academie` 100% | INVISIBLE | signal géo secours |
| | `modalite_enseignement` 99% | INVISIBLE | présentiel/distance/alternance -> filtre modalité |
| **rncp** (5181) | `abrege_type` 56% | INVISIBLE | **comble type_diplome rncp (44% vide)** |
| | `codes_nsf` 100% | INVISIBLE | classification domaine (NSF) |
| **rncp_blocs** (4891) | `intitule` 100% | text-only | (déjà dans text) |
| **onisep** (4758) | `niveau_certification` 98% | INVISIBLE | **comble niveau (73% seulement)** |
| | `sigle_formation` 29% | INVISIBLE (sigle parké) | matching acronyme (BUT GEII...) |
| **inserjeunes_cfa** (4065) | `niveau` 0% (vide) | DÉRIVABLE | **`type_diplome_to_niveau()` existe déjà (inserjeunes.py:73), pas appliquée** |
| | `uai` 100% | INVISIBLE | join/geo secours |
| **inserjeunes_lycee_pro** (2693) | `taux_emploi_12m_moyen` 72%, `_24m_moyen` 66%, `taux_poursuite_etudes_moyen` 94% | text-only (PAS dans insertion_pro) | **stats emploi non exposées en structuré/fact_card** |
| **labonnealternance** (4008) | TOUT | **DORMANT** (`retrieval_eligible=False`) | ré-éligibilité = décision séparée (ordre 1230). geopoint+rome riches, tout exclu |
| **rome_api_v4** (1584) | `competences_par_enjeu`, `savoirs_par_categorie` 100% | text-only | (dans text) — pas structuré |
| **dares_metiers_2030** (1160) | postes_a_pourvoir, tension, effectifs... 87-90% | text-only | prospective emploi -> pas structuré/filtre |
| **onisep_ideo** (1075) | `secteurs` 100%, `centres_interet` 99% | text-only | **`secteurs`->filtre secteur ; `centres_interet`->matching intérêts AnalystAgent** |
| **onisep_metiers** (1075) | `gfe`, `rome_libelles` 86% | text-only | (dans text) |
| **ip_doc_doctorat** (240) | `taux_insertion`, `part_stable/cadre/temps_plein`... 100% | INVISIBLE (hors insertion_pro) | détail insertion doctorat (niche) |

---

## 3. LISTE RANKÉE — candidats enrichissement GRATUIT (par impact)

Impact = volume × valeur retrieval/UX × gratuité (BM25/filtre/fact_card sans ré-embed).

### TIER 1 — systémiques, larges, gratuits

1. **Activer la dimension filtre `secteur` (morte aujourd'hui)**.
   `metadata_filter.secteur` existe (5 critères v1) mais **0 fiche formation peuplée**
   (confirmé verdict J11). Signaux disponibles : monmaster `secteur_discipline` (7573,
   100%), onisep_ideo `secteurs` (1075, 100%), insersup "Secteur disciplinaire". Mapper
   -> `secteur` active un filtre entier inerte + le matching intérêts->secteurs de
   l'AnalystAgent. **~8600+ fiches, gratuit (filtre live).** Plus gros levier du lot.

2. **type_diplome rncp (44% vide) via `abrege_type` + niveau**. Étendre `derive_fields`
   à rncp (même brique que 1230). ~2261 fiches typables. Gratuit (BM25/fact_card).

3. **inserjeunes_lycee_pro : mapper `taux_emploi_12m/24m_moyen` + `poursuite` vers
   `insertion_pro`**. 2693 fiches : stats emploi présentes mais hors du bloc structuré
   -> invisibles à fact_card. Mapping -> données insertion citables. Gratuit.

### TIER 2 — ciblés

4. **inserjeunes_cfa `niveau` (0% -> dérivable)** : la fonction `type_diplome_to_niveau()`
   EXISTE (inserjeunes.py:73) mais n'est pas appliquée. 4065 fiches. Mini-pattern
   "code existe, pas câblé". Gratuit, trivial.
5. **onisep `niveau_certification` (98%) -> combler `niveau` (73%)**. 4758 fiches.
6. **monmaster `parcours` (91%) + `mention` -> dense/BM25**. Spécialisation master
   actuellement seulement via nom. Gain dense au ré-embed prévu (champ à ajouter =
   modif fiche_to_text ADR-gatée à A/B) ; BM25 immédiat.
7. **labonnealternance 4008 dormantes** : ré-éligibilité (décision volume/qualité
   séparée, déjà flaggée). geopoint+rome riches entièrement exclus.

### TIER 3 — niche / faible

8. parcoursup `form_lib_voe_acc` (libellé filière secours) + `selectivite_code`
   (serve-only -> signal retrieval). 9. doctorat `taux_insertion`/`part_*` (240, niche).
   10. dares/rome/ideo : exposer en STRUCTURÉ ce qui n'est aujourd'hui que dans `text`
   (filtrable/citable vs seulement sémantique). 11. NSF codes -> classification domaine.

---

## 4. Champs sous-exploités (ingérés + dans 1 canal mais pas là où ils auraient de la valeur)

- `discipline` (monmaster 100%) : dans BM25 + fact_card mais **PAS dense** (fiche_to_text
  ne lit pas discipline). Discipline = concept de recherche fort pour le master.
- `selectivite_code` (parcoursup 100%) : fact_card seulement, pas retrieval ni filtre
  (alors que "formations peu sélectives à X" est une requête naturelle).
- `codes_rome` : dans BM25 mais **pas exposé en filtre** (pas de filtre par métier-cible).
- Annex `text` (dares/rome/ideo) : tout le contenu structuré est aplati en `text`
  (retrievable) mais **rien n'est filtrable/citable en structuré** (tension, postes,
  secteurs...). Une requête "métiers en tension en Occitanie" passe par la sémantique,
  jamais par un filtre déterministe.

---

## 5. Méthode & limites

- Matrice présence : comptée sur les 52040 fiches de `data/processed/formations.json`
  (toutes sources, tous champs, exhaustif — pas un échantillon).
- Exploitation : lecture directe de `fiche_to_text`, `_fiche_to_search_text`,
  `fact_card`, `metadata_filter`, `structured_select`, `geo_coherence`.
- Raw-not-ingested : vérifié sur les 2 gros CSV (parcoursup 118 colonnes, insersup).
  Parcoursup : la plupart des colonnes à valeur sont ingérées ; droppées notables =
  `g_olocalisation_des_formations` (geo lat/lon — mais region déjà 99% remplie) et les
  ventilations fines voeux/classement par type de bac. Insersup : la collecte C2b a pris
  le salaire ; les taux d'emploi multi-horizons (6/12/18/24/30 mois) restent un candidat
  à vérifier côté attach.
- Reste à approfondir si besoin : diff colonne-à-colonne des 11 autres schémas raw
  (rncp/onisep/rome/dares...) — non bloquant, les gros leviers sont déjà identifiés
  dans la couche ingéré-mais-non-exploité.
