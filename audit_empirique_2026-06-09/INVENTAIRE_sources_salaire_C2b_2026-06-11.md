# C2b — Inventaire faisabilité sources salaire (livrable 1)

Ordre : 2026-06-11-1957-claudette-orientai-c2b-collecte-salaire
Auteur : Claudette · Date : 2026-06-11 (soir, scoping seul ; collecte = session fraîche demain)

## Cible technique (déjà câblée)

`insertion_pro.salaire_median_embauche` (int, € mensuel) + `taux_cdi`, formaté par
`src/rag/embeddings.py::_format_insertion_pro` (schéma Céreq) -> **embeddé** dans
fiche_to_text -> retrievable. Rempli sur **0** fiche aujourd'hui (les agrégats Céreq
par niveau ont été retirés par ADR-054 pour grossièreté). Le pipeline attend la donnée,
il manque la COLLECTE à une granularité joignable.

Clés de jointure disponibles sur le corpus (52040 fiches) : nom 76%, domaine 76%,
niveau 67%, rncp 24%, codes_rome 23%, codes_nsf 19%, cod_aff_form 25%.

## Sources évaluées

| Source | Salaire ? | Granularité | Net/Brut | Jointure | Verdict |
|---|---|---|---|---|---|
| **InserSup** (local `data/raw/insersup.csv`, 839k lignes) | **OUI** — "Salaire mensuel net médian en équivalent temps plein" à 6/12/18/24/30 mois + quartiles Q1/Q3 | **Fine** : établissement × type de diplôme × domaine disciplinaire | **NET** explicite (label source) | établissement + diplôme + discipline ; **`insersup_attach.py` (25KB) joint DÉJÀ InserSup aux fiches** pour les taux | **PRIMAIRE — recommandé** |
| **Céreq Enq. Génération** (local `OpenData_Cereq-Enq_Generation-Donnees_DIPLOME.xlsx`) | OUI — colonne `revenu_travail` (+ % cadres, secteurs) | **Grossière** : 44 lignes, niveau × grande spécialité (industrielle/tertiaire/services) | à confirmer (probablement net) | niveau + spécialité | **FALLBACK proxy** — reproduit l'ADR-054, à éviter en primaire |
| **InserJeunes** (lycée pro + CFA, data.gouv) | **NON** — uniquement taux d'emploi 6/12/18/24m (confirmé corpus 6758 fiches + recherche data.gouv) | fine (établissement+formation) mais sans salaire | — | — | **PAS une source salaire** |
| **DARES "Les métiers en 2030"** (local xlsx) | NON (perspectives de recrutement par FAP) | FAP (famille métier) | — | — | **Hors sujet** (prospective emploi, pas salaire/formation) |

## Recommandation : attaquer InserSup en premier

Meilleur ratio couverture/fiabilité de jointure ET effort le plus faible :
1. **Donnée locale, prête** : salaire net médian par établissement+diplôme, déjà téléchargée.
2. **Machinerie de jointure existante** : `insersup_attach.py` matche déjà InserSup aux fiches (pour les taux d'insertion). C2b = **étendre cet attach** pour capter les colonnes salaire net médian (cols 63-67) -> `insertion_pro.salaire_median_embauche` + provenance `insersup` + année cohorte. Pas de nouvelle machinerie de jointure à écrire.
3. **Cible** : ~7573 fiches MonMaster (master, établissement+discipline+niveau) + licence pro/DUT si couverts par InserSup. Couverture précise à mesurer en session 2.
4. **Garde-fou RÈGLE 6** : net explicitement étiqueté depuis la source -> pas de mélange brut/net silencieux. Le salaire formation réel primera sur le proxy PCS.

Céreq Génération reste un fallback proxy (niveau×spécialité) pour les fiches SANS match
InserSup, MAIS reproduit la grossièreté ADR-054 -> à n'envisager qu'en dernier, étiqueté
"agrégat niveau" explicite. Décision à trancher après mesure de couverture InserSup.

CAP/BTS/apprentissage : pas de salaire public exploitable (InserJeunes = taux seuls).
Lacune structurelle à assumer, pas un échec de collecte.

## Doctorat (point de l'ordre)

~240 fiches doctorat portent un salaire MAIS hors `insertion_pro` (champ dédié,
`insertion_pro=None`) -> `_format_insertion_pro` ne les surface PAS, d'où "noyés".
Quick win session 2 : mapper ce champ vers `insertion_pro.salaire_median_embauche`
(localiser le nom exact du champ). Pas un fix ce soir.

## Chiffrage re-embed (GATÉ Matteo, à confirmer session 2)

`insertion_pro` est dans le texte embeddé -> populer le salaire sur ~7573 fiches MonMaster
rend leur embedding stale -> **re-embed partiel ~7500 fiches ≈ 16% de l'index** (47k).
Estimation grossière Mistral embed : ~1-2 € (à confirmer au token près avant exécution).
À CHIFFRER précisément et faire VALIDER avant tout re-embed. Le re-run 497q reste gaté.

## Plan session 2 (livrables 2-5, /clear demain)

1. Étendre `insersup_attach.py` : parser + joindre salaire net médian InserSup -> insertion_pro (provenance + année + net étiqueté).
2. Mesurer couverture réelle (combien de fiches gagnent un salaire) + valider GE (pas de NaN, bornes).
3. Mapper le salaire doctorat (~240) vers insertion_pro.
4. Mesure d'impact par-question sur le subset salaire (cas étiquetés gel + queue) — déterministe sur sources figées.
5. Chiffrer le re-embed partiel au token près + demander GO Matteo (gaté). PR séparée, suite verte, pas de merge sans audit Jarvis.

Sources : [InserJeunes data.gouv](https://www.data.gouv.fr/datasets/inserjeunes-voie-professionnelle-scolaire-par-etablissement-relevant-du-ministere-de-leducation-nationale) (taux seuls, confirmé sans salaire).
