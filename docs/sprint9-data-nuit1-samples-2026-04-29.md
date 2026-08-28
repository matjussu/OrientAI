# Sample Q&A keep+flag nuit 1 — Sprint 9-data 2026-04-29

**Date génération doc** : 2026-04-29 (post-fix bug stop condition)
**Source pipeline** : nuit 28-29/04, `data/golden_qa/golden_qa_v1.jsonl` (1020 jobs traités)
**Filtre** : `decision in (keep, flag)`, soit **45 Q&A sur 1020** = 4.4% rendement utilisable
**Détail** : 36 keep + 9 flag, score moyen **86.5/100**
**Modèles** : research Haiku 4.5 + draft Opus 4.7 + critique-refine Opus 4.7 (stratégie hybride v3)
**Bug nuit 1** : voir `docs/SPRINT9_DATA_VERDICT.md` §12 (root cause + fix appliqué commit 548834a)

---

## Stats globales

| # | prompt_id | iter | category | score | décision | latence |
|---|---|---|---|---|---|---|
| 1 | `A1` | 0 | `lyceen_post_bac` | **84** | `flag` | 127.2s |
| 2 | `A1` | 1 | `lyceen_post_bac` | **92** | `keep` | 85.7s |
| 3 | `A1` | 2 | `lyceen_post_bac` | **78** | `flag` | 91.1s |
| 4 | `A1` | 3 | `lyceen_post_bac` | **84** | `flag` | 94.7s |
| 5 | `A1` | 4 | `lyceen_post_bac` | **86** | `keep` | 94.8s |
| 6 | `A1` | 5 | `lyceen_post_bac` | **86** | `keep` | 79.3s |
| 7 | `A1` | 6 | `lyceen_post_bac` | **88** | `keep` | 96.2s |
| 8 | `A1` | 7 | `lyceen_post_bac` | **86** | `keep` | 85.2s |
| 9 | `A1` | 8 | `lyceen_post_bac` | **78** | `flag` | 74.1s |
| 10 | `A1` | 9 | `lyceen_post_bac` | **86** | `keep` | 100.9s |
| 11 | `A1` | 10 | `lyceen_post_bac` | **87** | `keep` | 101.3s |
| 12 | `A1` | 11 | `lyceen_post_bac` | **86** | `keep` | 79.6s |
| 13 | `A1` | 12 | `lyceen_post_bac` | **86** | `keep` | 66.5s |
| 14 | `A1` | 13 | `lyceen_post_bac` | **86** | `keep` | 82.3s |
| 15 | `A1` | 14 | `lyceen_post_bac` | **78** | `flag` | 73.2s |
| 16 | `A1` | 15 | `lyceen_post_bac` | **84** | `flag` | 86.5s |
| 17 | `A1` | 16 | `lyceen_post_bac` | **91** | `keep` | 71.8s |
| 18 | `A1` | 17 | `lyceen_post_bac` | **78** | `flag` | 75.5s |
| 19 | `A1` | 18 | `lyceen_post_bac` | **86** | `keep` | 79.8s |
| 20 | `A1` | 19 | `lyceen_post_bac` | **86** | `keep` | 88.7s |
| 21 | `A2` | 0 | `lyceen_post_bac` | **84** | `flag` | 86.8s |
| 22 | `A2` | 1 | `lyceen_post_bac` | **86** | `keep` | 80.2s |
| 23 | `A2` | 2 | `lyceen_post_bac` | **86** | `keep` | 86.0s |
| 24 | `A2` | 3 | `lyceen_post_bac` | **86** | `keep` | 95.4s |
| 25 | `A2` | 4 | `lyceen_post_bac` | **91** | `keep` | 52.1s |
| 26 | `A2` | 5 | `lyceen_post_bac` | **92** | `keep` | 55.4s |
| 27 | `A2` | 6 | `lyceen_post_bac` | **88** | `keep` | 94.6s |
| 28 | `A2` | 7 | `lyceen_post_bac` | **89** | `keep` | 49.0s |
| 29 | `A2` | 8 | `lyceen_post_bac` | **86** | `keep` | 84.8s |
| 30 | `A2` | 9 | `lyceen_post_bac` | **86** | `keep` | 91.2s |
| 31 | `A2` | 10 | `lyceen_post_bac` | **92** | `keep` | 94.7s |
| 32 | `A2` | 11 | `lyceen_post_bac` | **92** | `keep` | 73.1s |
| 33 | `A2` | 12 | `lyceen_post_bac` | **91** | `keep` | 62.7s |
| 34 | `A2` | 13 | `lyceen_post_bac` | **92** | `keep` | 48.8s |
| 35 | `A2` | 14 | `lyceen_post_bac` | **86** | `keep` | 128.9s |
| 36 | `A2` | 15 | `lyceen_post_bac` | **92** | `keep` | 86.0s |
| 37 | `A2` | 16 | `lyceen_post_bac` | **88** | `keep` | 99.7s |
| 38 | `A2` | 17 | `lyceen_post_bac` | **91** | `keep` | 70.6s |
| 39 | `A2` | 18 | `lyceen_post_bac` | **86** | `keep` | 94.3s |
| 40 | `A2` | 19 | `lyceen_post_bac` | **86** | `keep` | 49.2s |
| 41 | `A3` | 0 | `lyceen_post_bac` | **86** | `keep` | 106.8s |
| 42 | `A3` | 1 | `lyceen_post_bac` | **86** | `keep` | 74.9s |
| 43 | `A3` | 2 | `lyceen_post_bac` | **86** | `keep` | 87.6s |
| 44 | `A3` | 3 | `lyceen_post_bac` | **86** | `keep` | 50.5s |
| 45 | `A3` | 4 | `lyceen_post_bac` | **84** | `flag` | 74.4s |

**Boundaries** : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`

---

## Q&A #1 — `A1` iter 0 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `flag` (score **84**, recommandée critique `keep`)
**Latence** : 127.2s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique mais les maths abstraites me saoulent — t'aurais des pistes concrètes loin de la prépa MPSI ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un profil scientifique solide, mais le format très théorique de la prépa te freine et tu cherches des voies plus appliquées. C'est une interrogation légitime — beaucoup de profils maths-physique se reconnaissent là-dedans.
>
> Voici trois pistes à peser selon ce qui résonne chez toi :
>
> • **Écoles d'ingénieurs post-bac (parcours intégré 2+3 ans)** — une part notable de l'offre d'écoles d'ingénieurs est accessible directement après le bac, avec un format souvent moins compétitif que la prépa et une montée progressive en complexité. Tu travailles des maths appliquées, et certaines écoles proposent des spécialisations hybrides (robotique, IA, jeu vidéo, bio-informatique).
>
> • **BUT scientifiques (informatique, mesures physiques, génie biologique)** — accessibles sur Parcoursup, ils offrent un format pro, un rythme cours/projet équilibré, et des passerelles possibles vers une école d'ingénieur ensuite si l'envie revient. Coût modéré, sélectivité variable selon les IUT.
>
> • **Formations hybrides spécialisées (Cnam, écoles d'ingé agro, cursus modulables)** — le Cnam propose des parcours en IA, robotique, finance quantitative ou bio-informatique, parfois modulables et compatibles avec d'autres études. Du côté des écoles agricoles à cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon), tu trouveras des voies concrètes pour qui aime le terrain et l'application.
>
> Pour creuser : qu'est-ce qui t'attire le plus quand tu te projettes dans ton futur métier — résoudre des problèmes techniques en équipe, créer un produit visible, ou explorer un domaine appliqué (santé, environnement, jeu) ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **18/25** = **84/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre '23 000+ formations' (chiffre précis non sourcé dans la draft) et l'affirmation 'environ la moitié de l'offre' attribuée à l'Onisep (formulation à risque). Reformulé en termes plus prudents sans chiffres précis. Conservé la structure conseiller (reformulation + 3 options pondérées + question ouverte finale).

_Décision recommandée par critique : `keep` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #2 — `A1` iter 1 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **92**, recommandée critique `keep`)
**Latence** : 85.7s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?

**Question (refined par Phase 4)** :
> Quelles écoles d'ingénieur post-bac valent vraiment le coup par rapport à la prépa ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un profil scientifique solide mais la prépa MPSI ne te fait pas rêver, et tu cherches des voies ingé plus directes, plus concrètes, idéalement un peu hybrides. C'est une question hyper légitime — tu n'es vraiment pas seul·e à te la poser.
>
> Voici 3 pistes à mettre en balance, sans hiérarchie :
>
> **Écoles d'ingénieurs post-bac (cursus intégré 2+3 ans)**
> Une partie significative de l'offre ingé française est accessible directement après le bac via Parcoursup. Tu évites la pression concours de la prépa, le rythme est plus progressif. À regarder de près : sélectivité variable selon les écoles, écart important entre frais publics et privés, et surtout l'accréditation CTI (le label officiel du diplôme d'ingénieur reconnu par l'État).
>
> **BUT (Bachelor Universitaire de Technologie)**
> Voie technologique appliquée, très orientée projets et stages, avec passerelle possible vers une école d'ingé en admissions parallèles ensuite. Bonne insertion documentée, frais publics modérés, profil concret qui colle à ce que tu décris. Bémol : la suite ingé demande un dossier solide tout au long du cursus.
>
> **Parcours hybrides spécialisés (bio-info, finance quant, robotique, IA, jeu vidéo)**
> Des bachelors ou cursus type Cnam qui croisent plusieurs disciplines, parfois en alternance ou modulables. Très alignés avec ton goût pour l'hybridation et le non-mainstream. Attention : la reconnaissance, la sélectivité et le coût varient énormément d'une école à l'autre — vérifier les données InserSup quand elles existent et la présence d'une accréditation reconnue reste clé.
>
> Si tu devais décrire un truc concret que tu aurais envie de construire, comprendre ou résoudre dans 5 ans, ça ressemblerait à quoi ? C'est souvent ça qui fait vraiment le tri entre ces 3 voies.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **24/25** / hallucination **21/25** = **92/100**

**Corrections suggérées par le critique** :
> Retiré la mention 'environ la moitié' (chiffre non sourcé) remplacée par formulation qualitative. Précisé que CTI est le label officiel sans surenchère. Légère normalisation du ton et resserrage de la question finale.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #3 — `A1` iter 2 (catégorie `lyceen_post_bac`, axe 1, seed_idx 2)

**Décision** : `flag` (score **78**, recommandée critique `flag`)
**Latence** : 91.1s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?

**Question (refined par Phase 4)** :
> Bio-info, finance quant, jeu vidéo me parlent vraiment : quelles voies post-bac concrètes je peux explorer sans passer par la prépa ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu cherches un profil scientifique appliqué à des domaines concrets et hybrides, sans passer par la case prépa MPSI. C'est une intention tout à fait défendable — il y a plus de portes que ce qu'on présente souvent par défaut.
>
> 🎯 **Écoles d'ingénieurs post-bac (cycle intégré 5 ans)**
> - Accessibles directement après le bac via Parcoursup, sans prépa intermédiaire
> - Certaines proposent des parcours orientés IA, bio-informatique ou informatique appliquée — à vérifier école par école sur leur fiche Parcoursup
> - Recrutement souvent sur dossier + entretien, moins ciblé concours qu'une prépa
>
> 🎯 **BUT (Bachelor Universitaire de Technologie) informatique, statistique ou génie biologique**
> - En IUT public, sur Parcoursup, formation pro de 3 ans avec stages
> - Débouchés consultables via InserJeunes / InserSup pour te faire une idée concrète
> - Peut servir de tremplin vers une école d'ingé en admission parallèle si tu veux prolonger
>
> 🎯 **Licences universitaires hybrides (info-maths, MIASHS, bio-info)**
> - Plus théoriques que le BUT, mais ouvrent vers des masters spécialisés (data, finance quant, bio-info)
> - Voie souple si tu veux te laisser le temps de préciser ton domaine avant la spécialisation
> - À regarder fiche par fiche sur Parcoursup pour les contenus réels
>
> Entre la bio-info, la finance quant et le jeu vidéo, qu'est-ce qui te tire le plus aujourd'hui : le côté résolution de problèmes mathématiques, le côté création d'un produit qui tourne, ou le côté impact appliqué sur un domaine métier ? Ça m'aiderait à affiner les pistes avec toi.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **19/25** / posture **21/25** / cohérence **22/25** / hallucination **16/25** = **78/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre '23 000+ formations' et 'environ la moitié des écoles' (chiffres précis non sourcés dans le draft). Retiré 'école du numérique et de l'IA' présenté comme nom officiel Cnam (formulation imprécise). Reformulé pour rester factuel sur l'existence des voies sans inventer de proportions.

_Décision recommandée par critique : `flag` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #4 — `A1` iter 3 (catégorie `lyceen_post_bac`, axe 1, seed_idx 3)

**Décision** : `flag` (score **84**, recommandée critique `keep`)
**Latence** : 94.7s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles sont les meilleures formations en cybersécurité en France ?

**Question (refined par Phase 4)** :
> Je m'intéresse à la cybersécurité mais la prépa MPSI ne me tente pas du tout — quelles voies post-bac existent pour bosser dans ce domaine ?

**Answer (refined par Phase 4)** :

> Si je te suis bien, tu veux te diriger vers la cybersécurité sans passer par la case prépa MPSI. C'est un chemin tout à fait jouable — ce domaine s'est ouvert ces dernières années à plusieurs voies post-bac, chacune avec sa logique propre.
>
> Voici trois pistes qui pourraient te correspondre, à pondérer selon ce que tu cherches :
>
> • **BUT Informatique ou Réseaux & Télécoms (parcours cybersécurité)** : cursus en 3 ans à l'université (IUT), accessible sur Parcoursup. Frais publics réduits, beaucoup de pratique avec stages et projets concrets. Tu gardes la porte ouverte vers une école d'ingé ou un master ensuite si tu veux pousser plus loin la spécialisation.
>
> • **Écoles d'ingénieurs post-bac avec spécialisation cyber** : plusieurs écoles proposent un cursus intégré en 5 ans (2 ans de prépa intégrée + 3 ans de cycle ingénieur), accessible sur dossier après le bac. Sélectif mais moins frontal que la prépa MPSI classique. Frais très variables selon le statut (publiques abordables, privées plus chères).
>
> • **Cursus universitaires ou Cnam orientés numérique/sécurité** : le Cnam propose des formations modulables, parfois compatibles avec un emploi ou une alternance. À l'université, certaines licences info ouvrent ensuite sur des masters cybersécurité. Logique plus progressive, intéressant si tu veux mixer théorie et terrain.
>
> Pour t'aider à cibler : qu'est-ce qui t'attire le plus dans la cybersécurité — le côté technique pur (pentest, réseaux, crypto), la gouvernance et l'analyse de risque, ou la dimension recherche/innovation ? Et est-ce que tu te vois plutôt dans un cadre théorique long (école d'ingé) ou plus appliqué dès le départ (BUT, alternance) ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **22/25** / cohérence **22/25** / hallucination **19/25** = **84/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre 'environ la moitié des écoles d'ingénieurs accessibles post-bac' (non sourcé). Précisé que les BUT durent 3 ans (BUT = Bachelor Universitaire de Technologie). Reformulé pour éviter toute prescription implicite et rééquilibré les 3 options sans hiérarchie cachée.

_Décision recommandée par critique : `keep` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #5 — `A1` iter 4 (catégorie `lyceen_post_bac`, axe 1, seed_idx 4)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 94.8s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

**Question (refined par Phase 4)** :
> Pour la cybersécurité, je suis bon en maths/physique mais la prépa MPSI ne me motive pas. Est-ce qu'il faut absolument viser ENSEIRB-MATMECA ou EPITA, ou il y a d'autres voies post-bac sérieuses ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un profil scientifique solide et la cybersécurité t'attire, mais le format prépa MPSI ne te motive pas — tu cherches des voies post-bac plus directes ou plus concrètes, sans renoncer au sérieux du parcours.
>
> C'est une question saine à se poser maintenant, parce qu'il y a vraiment plusieurs portes d'entrée crédibles, pas une seule.
>
> Voici trois pistes à comparer, sans hiérarchie a priori :
>
> • **École d'ingé post-bac avec spé cyber ou systèmes d'info** (type EPITA, ESIEA, ENSIBS, et certaines écoles du concours Avenir Bac ou Geipi-Polytech) — admission via dossier + entretien et/ou concours, parcours intégré 5 ans. Plus de continuité que la prépa, mais sélectivité et frais variables (souvent élevés en privé, plus modérés dans le public type ENSIBS). Lisibilité correcte côté employeurs cyber.
>
> • **BUT Réseaux & Télécoms ou BUT Informatique parcours cybersécurité** — voie publique via Parcoursup, 3 ans, profil plus appliqué que la prépa. Double débouché possible : insertion directe en bac+3, ou poursuite en école d'ingé / master cyber. Tu peux comparer les promos via les indicateurs InserJeunes (taux d'insertion à 6, 12, 18, 24 mois) qui sont publics par établissement.
>
> • **Bachelor cyber ou cursus en alternance** (écoles privées spécialisées, ou Cnam pour des formats modulables) — plus pro et concret, souvent en alternance dès bac+1 ou bac+3, profil moins académique mais reconnu sur certains segments du marché. À regarder de près sur la reconnaissance du diplôme (visa, grade, RNCP) et le coût net après alternance.
>
> À noter : l'ENSEIRB-MATMECA reste une très bonne école, mais elle se rejoint majoritairement après prépa, donc elle sort un peu de ton scope actuel. EPITA est accessible post-bac et cohérente avec ce que tu décris.
>
> Qu'est-ce qui pèse le plus pour toi dans ce choix : entrer vite dans la pratique et l'alternance, garder une assise théorique forte pour évoluer plus tard, ou maîtriser le coût et le risque financier sur la durée ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré chiffre '23 000 formations Parcoursup' (non sourcé précis) et 'environ la moitié des écoles d'ingé accessibles post-bac' (formulation vague attribuée à ONISEP). Précisé que ENSEIRB-MATMECA a aussi une admission post-bac via concours Avenir Bac/Geipi pour ne pas écarter à tort. Allégé légèrement la liste d'écoles privées pour éviter la lecture comme reco implicite.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #6 — `A1` iter 5 (catégorie `lyceen_post_bac`, axe 1, seed_idx 5)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 79.3s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Bon en code mais CS classique me lasse, y'a quoi d'autre comme voies ?

**Question (refined par Phase 4)** :
> Bon en code mais CS classique me lasse, y'a quoi d'autre comme voies ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, t'as déjà les bases en code mais l'idée d'aller pure CS ou prépa MPSI te parle pas — tu cherches du concret, du transversal, là où le code sert à autre chose qu'à lui-même. Question hyper saine à te poser maintenant.
>
> Trois pistes à explorer, sans hiérarchie :
>
> • **BUT informatique (Parcoursup)** — formation appliquée sur 3 ans, alternance possible en cours de cursus, parcours qui peuvent t'orienter vers cybersécurité, data, dev web ou science des données. Insertion documentée via InserSup. Moins théorique qu'un cursus universitaire classique, plus orienté projets et stages.
>
> • **Écoles d'ingénieurs post-bac (parcours intégré 2+3 ans)** — une partie significative de l'offre est directement accessible après le bac, sans passer par la prépa MPSI (recensé sur l'ONISEP). Plusieurs proposent des spés hybrides qui pourraient te parler : bio-informatique, robotique, jeu vidéo, IA appliquée. Sélectivité variable selon les écoles, frais souvent modérés en public, plus élevés en privé.
>
> • **Formations modulables type Cnam ou bachelors hybrides** — le Cnam propose des cursus dans le numérique avec des parcours en robotique, IA, bio-informatique, finance quantitative. Format souvent hybride et modulable, qui peut se construire en parallèle d'études ou en formation continue. Plus original, mais demande de la maturité dans la construction du parcours.
>
> Avant d'aller plus loin : qu'est-ce qui t'attire le plus dans le code aujourd'hui — la dimension applicative (résoudre un truc concret), la dimension création (jeu vidéo, design interactif), ou la dimension technique pure (algos, IA) ? Ça aide à distinguer entre ces voies.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre '~100 écoles' non sourcé précisément (formulation adoucie). Précisé que 'école du numérique et de l'IA Cnam' est présentée comme exemple d'offre Cnam sans nom officiel inventé. Légère condensation pour fluidité.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #7 — `A1` iter 6 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `keep` (score **88**, recommandée critique `keep`)
**Latence** : 96.2s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique, j'ai de bonnes notes mais je sature complètement des maths trop abstraites. La prépa MPSI me fait peur, t'as des alternatives concrètes à me proposer ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as les capacités scientifiques mais tu cherches du concret, des projets, de l'application — pas deux années supplémentaires de théorie pure. C'est un besoin légitime, et plein de profils scientifiques solides s'épanouissent mieux dans des cursus plus appliqués.
>
> Voici trois pistes à explorer, sans hiérarchie :
>
> • **Écoles d'ingénieurs post-bac (parcours intégré)**
> Il existe un large panel d'écoles directement accessibles après le bac, en cursus intégré sur 5 ans. Tu fais ta « prépa » dans l'école, avec des projets concrets dès la première année — tu apprends en faisant, ce qui peut mieux coller à un profil qui sature de l'abstrait. Sélectivité variable, frais variables aussi selon statut public/privé : à regarder école par école sur Parcoursup.
>
> • **BUT (Bachelor Universitaire de Technologie)**
> Cursus public en 3 ans, très orienté concret : projets, stages, alternance possible en 2e/3e année. Spécialités hybrides côté scientifique comme informatique, mesures physiques, génie mécanique et productique, génie civil. Coût modéré. Tu peux aussi rejoindre une école d'ingénieur ensuite en admission parallèle si l'envie vient — pratique pour garder les options ouvertes.
>
> • **Formations hybrides spécialisées**
> Le Cnam propose des cursus modulables côté technique. Côté écoles agricoles et du vivant, certains établissements mêlent sciences expérimentales et ingénierie appliquée (agronomie, environnement, bio-ingénierie). Cursus moins mainstream, qui peuvent te démarquer si tu trouves un croisement qui te parle vraiment.
>
> Une question pour avancer : quand tu penses « concret », tu te vois plutôt sur des projets techniques (robotique, code, méca) ou sur des applications terrain (agro, santé, environnement) ? Ça aiderait à resserrer le champ avec toi.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **24/25** / cohérence **23/25** / hallucination **19/25** = **88/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre '100 écoles' (approximatif/non sourçable strictement) et le '23 000+ formations Parcoursup' (chiffre précis non vérifié). Reformulé en formulations qualitatives. Allégé légèrement pour densifier.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #8 — `A1` iter 7 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 85.2s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?

**Question (refined par Phase 4)** :
> Quelles écoles d'ingénieur post-bac valent vraiment le coup par rapport à la prépa, surtout si MPSI ne me tente pas ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu cherches une voie scientifique exigeante mais sans passer par le moule MPSI — quelque chose de plus concret, peut-être hybride. C'est une question légitime quand la prépa classique ne te parle pas.
>
> Quelques pistes à explorer, à pondérer selon ton profil :
>
> • **Écoles d'ingénieur post-bac (cursus intégré 5 ans)** : tu entres directement après le bac, avec des projets et stages dès les premières années. Plusieurs réseaux existent (INSA, UT, Polytech, écoles à cursus intégré reconnues par la CTI — Commission des Titres d'Ingénieur). La sélectivité varie fortement d'un établissement à l'autre, donc à regarder école par école sur Parcoursup, pas en bloc.
>
> • **BUT (Bachelor Universitaire de Technologie)** : trois ans très appliqués, accessibles via Parcoursup. Tu peux soit viser l'emploi direct, soit poursuivre vers une école d'ingénieur en admission parallèle après le BUT. Voie souvent plus accessible et concrète, qui colle à un profil qui préfère "faire" que théoriser.
>
> • **Filières hybrides ou spécialisées** : écoles d'ingénieur dans le domaine du vivant (agronomie, environnement) qui croisent science et ingénierie, ou cursus universitaires avec doubles licences (maths-info, physique-chimie, sciences-éco) qui te laissent plus de latitude pour mixer. Demande plus d'autonomie pour construire ton parcours, mais terrain idéal si tu veux croiser plusieurs domaines.
>
> Qu'est-ce qui pèse le plus pour toi en ce moment — la sélectivité à l'entrée, le côté concret/projet dès la première année, ou la possibilité de mixer plusieurs domaines dans le parcours ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Retrait du chiffre non sourcé 'environ la moitié des écoles' (risque hallucination). Précision que les noms d'écoles (INSA, UT, Polytech) sont des exemples de réseaux, pas des recommandations. Allègement du jargon ('CTI' explicité), formulation finale plus ouverte.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #9 — `A1` iter 8 (catégorie `lyceen_post_bac`, axe 1, seed_idx 2)

**Décision** : `flag` (score **78**, recommandée critique `flag`)
**Latence** : 74.1s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?

**Question (refined par Phase 4)** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu cherches des voies scientifiques concrètes qui croisent plusieurs disciplines (bio + info, maths + finance, code + création), sans forcément passer par la case prépa MPSI. C'est un profil de plus en plus reconnu, et plusieurs portes d'entrée existent post-bac.
>
> Voici 3 pistes à mettre en balance :
>
> • **Écoles d'ingénieurs post-bac (cycle préparatoire intégré + cycle ingénieur)** — Une part significative des écoles d'ingénieurs habilitées par la CTI sont accessibles directement après le bac, avec un cycle préparatoire intégré de 2 ans suivi de 3 ans de cycle ingénieur. Selon les écoles, on trouve des dominantes bio-info, finance quantitative ou informatique appliquée au jeu. Sélectivité et frais variables (public/privé), à vérifier sur la fiche Parcoursup de chaque école.
>
> • **BUT et cursus universitaires hybrides via Parcoursup** — Parcoursup référence des BUT informatique, génie biologique, MMI (métiers du multimédia et de l'internet, dimension création numérique / jeu), ainsi que des licences scientifiques pluridisciplinaires. Format plus court (3 ans), orientation pro marquée, coûts généralement inférieurs aux écoles privées. À comparer aux licences MIASHS ou doubles licences maths-info pour la voie quantitative.
>
> • **Formations modulables type Cnam ou cursus en alternance** — Le Cnam propose des parcours en informatique, data, finance et sciences du vivant, accessibles en formation initiale ou en parallèle d'un cursus principal. Utile si tu veux tester une thématique sans t'engager sur 5 ans, ou enrichir un cursus universitaire. Format souple, public, à creuser via leur site officiel.
>
> Pour t'aider à trier : qu'est-ce qui pèse le plus pour toi aujourd'hui — l'environnement étudiant (campus école vs fac), le rythme (théorique vs très appliqué dès la 1ʳᵉ année), ou la possibilité de combiner explicitement plusieurs domaines dans un même cursus ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **19/25** / posture **22/25** / cohérence **22/25** / hallucination **15/25** = **78/100**

**Corrections suggérées par le critique** :
> Retiré la mention 'École du numérique et de l'IA' du Cnam (libellé non vérifié) et le chiffre '23 000 formations' Parcoursup (non sourcé précisément). Atténué 'environ une école sur deux' en formulation prudente. Conservé la posture conseiller et les 3 options pondérées.

_Décision recommandée par critique : `flag` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #10 — `A1` iter 9 (catégorie `lyceen_post_bac`, axe 1, seed_idx 3)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 100.9s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles sont les meilleures formations en cybersécurité en France ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique, je m'intéresse à la cybersécurité mais la prépa MPSI ne me tente pas trop. Quelles voies post-bac peuvent me mener vers ce domaine ?

**Answer (refined par Phase 4)** :

> Si je comprends bien, tu vises la cybersécurité mais tu n'as pas envie de t'enfermer dans le rythme d'une prépa scientifique classique. C'est une démarche cohérente : plusieurs chemins post-bac mènent au même domaine sans passer par MPSI.
>
> Voici 3 pistes à explorer :
>
> **BUT Réseaux & Télécoms ou BUT Informatique (parcours cybersécurité)** — sur Parcoursup
> Formation publique en IUT (3 ans, bac+3), frais modérés, sélectivité qui varie selon les sites. Pédagogie concrète : TP, projets, stages. À noter : pour la plupart des postes cyber, une poursuite en école d'ingé ou master spécialisé après le BUT reste recommandée.
>
> **Écoles d'ingénieur post-bac avec dominante cyber/sécurité des systèmes** — parcours intégré 2+3 ans
> Une partie significative des écoles d'ingé sont accessibles directement après le bac, sans passer par la prépa. Le rythme et les modalités d'admission varient (concours, dossier, entretien). Coût très variable selon le statut public/privé — à vérifier école par école sur Parcoursup.
>
> **Formations hybrides type Cnam** — modulables, post-bac ou en parallèle
> Le Cnam propose des cursus numérique/info avec certificats modulables. Intéressant si tu veux tester avant de t'engager à fond, ou combiner avec une autre formation. Plus autonome, moins encadré qu'une école classique — ça demande de la rigueur perso.
>
> Pour creuser concrètement, tu peux regarder les fiches Parcoursup des formations qui te parlent (programmes détaillés, taux de réussite) et consulter InserSup pour comparer l'insertion à la sortie.
>
> Une question pour t'aider à affiner : qu'est-ce qui t'attire le plus dans la cybersécurité — la dimension technique pure (pentest, défense de systèmes), l'analyse de menaces et de données, ou plutôt l'angle stratégique/gouvernance du risque ? Selon où tu te projettes, certaines voies seront plus adaptées que d'autres.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la formulation 'L'ONISEP rappelle qu'environ la moitié des écoles…' (paraphrase non-sourçable précisément, risque hallucination). Adouci 'parcours intégré moins compétitif' en formulation prudente. Ajouté nuance que les BUT mènent à bac+3 (poursuite bac+5 nécessaire pour postes cyber visés). Reformulation initiale plus naturelle.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #11 — `A1` iter 10 (catégorie `lyceen_post_bac`, axe 1, seed_idx 4)

**Décision** : `keep` (score **87**, recommandée critique `keep`)
**Latence** : 101.3s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

**Question (refined par Phase 4)** :
> Comment comparer ENSEIRB-MATMECA et EPITA pour la cybersécurité quand on veut pas passer par une prépa MPSI ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu vises la cybersécurité comme spécialité et tu veux peser deux écoles très différentes — une publique reconnue, une privée post-bac — sans passer par la case prépa MPSI.
>
> C'est une question saine à se poser : ces deux voies n'ont pas du tout le même profil de coût, de rythme et de filtre d'entrée.
>
> Voici trois pistes à explorer :
>
> • **EPITA, école privée post-bac.** Tu intègres directement après le bac via Parcoursup, sans prépa, mais les frais de scolarité sont élevés sur l'ensemble du cursus (école privée). Programme dense orienté info et cybersécurité dès les premières années. À creuser si tu veux te spécialiser tôt et que le budget familial peut encaisser le privé.
>
> • **ENSEIRB-MATMECA via un cycle préparatoire intégré type Bordeaux INP / La Prépa des INP.** L'ONISEP rappelle qu'une partie des écoles d'ingénieurs est accessible après le bac via des parcours intégrés 2+3 ans, présentés comme alternative à la prépa MPSI. Frais publics modérés, dossier solide en terminale exigé, spécialisation cyber/électronique en cycle ingénieur. À explorer si tu veux du public costaud sans bachoter en CPGE — vérifie sur Parcoursup la voie d'accès exacte côté ENSEIRB.
>
> • **Voie progressive : BUT R&T ou informatique, puis admission parallèle en école d'ingé cyber.** Les BUT te laissent le temps de confirmer ton goût pour la cyber avant d'attaquer un cycle ingénieur, et restent diplômants en eux-mêmes — un filet de sécurité réel si tu hésites encore.
>
> Avant de trancher, jette un œil aux données InserSup sur l'insertion des diplômés cyber des écoles que tu vises — c'est la source officielle la plus fraîche.
>
> Qu'est-ce qui pèse le plus dans ta balance aujourd'hui : la sécurité d'un parcours public, le côté direct d'une école post-bac, ou l'envie de te garder une porte de sortie en cours de route ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **87/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre '23 000 formations Parcoursup' non sourcé dans le contexte de la réponse. Reformulé la mention ENSEIRB-MATMECA pour clarifier que la voie post-bac directe n'est pas garantie (cycle préparatoire Bordeaux INP type La Prépa des INP). Atténué la formulation 'sélectivité dossier modérée' EPITA non sourcée.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #12 — `A1` iter 11 (catégorie `lyceen_post_bac`, axe 1, seed_idx 5)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 79.6s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Bon en code mais CS classique me lasse, y'a quoi d'autre comme voies ?

**Question (refined par Phase 4)** :
> Bon en code mais le CS classique me lasse, y'a quoi d'autre comme voies ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu sais que t'es à l'aise avec le code, mais le format CS classique (fac théorique ou prépa MPSI) te lasse d'avance — tu cherches du technique avec un autre angle, plus concret ou hybride. C'est un signal sain à écouter, pas mal de profils comme le tien s'épanouissent ailleurs.
>
> Voici trois pistes à explorer, sans hiérarchie :
>
> • **BUT informatique (ou réseaux/télécoms)** — cursus en 3 ans accessible via Parcoursup, plus orienté projet et stages que la fac classique. Format pratique avec une bonne insertion documentée, et passerelle possible vers une école d'ingé en alternance après le BUT (selon dossier). Sélectivité modérée et variable selon l'IUT.
>
> • **École d'ingénieur post-bac à spé hybride** — beaucoup d'écoles d'ingé sont accessibles directement après le bac (cursus intégré 2+3 ans), ça représente une part importante de l'offre. Certaines proposent des spés croisées qui pourraient te parler : bio-informatique, finance quantitative, jeu vidéo, robotique. Sélectivité et frais très variables (publique vs privée), à comparer école par école sur Parcoursup.
>
> • **Bachelor spécialisé ou parcours alternatifs** — côté bachelors (data, gaming, cybersécu, IA appliquée), c'est souple et appliqué, mais frais souvent élevés et qualité hétérogène — à creuser cas par cas (insertion réelle, reconnaissance du diplôme, accréditations). Le Cnam peut aussi être une option si tu envisages une formule en alternance ou parallèle études, plutôt qu'un cursus initial classique.
>
> Une question pour t'aider à trier : qu'est-ce qui te branche vraiment quand tu codes aujourd'hui — le défi algo pur, le côté création (jeu, visuel), ou plutôt appliquer le code à un autre domaine qui te touche (santé, finance, environnement, robotique) ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la formulation 'environ une centaine d'écoles d'ingé... c'est moitié de l'offre' (chiffre imprécis non sourcé). Remplacé par formulation qualitative. Précisé que les passerelles BUT→école d'ingé dépendent du dossier. Ajouté une nuance sur le Cnam (plutôt formation continue/alternance, moins adapté direct post-bac sauf cas spécifiques).

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #13 — `A1` iter 12 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 66.5s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as des bases scientifiques solides mais tu cherches des parcours plus appliqués que la prépa, avec du concret et de l'hybridation. C'est une demande très partagée — l'offre post-bac s'est largement diversifiée ces dernières années.
>
> Trois pistes à explorer selon ce qui te parle :
>
> - **Écoles d'ingénieurs post-bac (parcours intégrés 2+3 ans)** : beaucoup d'écoles d'ingénieurs sont accessibles directement après le bac via concours communs (Geipi Polytech, Avenir, Puissance Alpha, Advance) sans passer par la prépa. Le rythme est plus progressif qu'en MPSI, avec projets et stages dès le début. Sélectivité variable selon l'école.
>
> - **BUT (Bachelor Universitaire de Technologie)** : très orienté pratique, avec stages et projets tutorés sur 3 ans. Des filières comme génie mécanique, informatique, mesures physiques ou réseaux te garderaient dans le scientifique appliqué. Le BUT permet ensuite soit l'insertion directe, soit la poursuite en école d'ingénieur ou master. Frais réduits (formation publique).
>
> - **Formations hybrides spécialisées** : bio-informatique, robotique, IA appliquée, jeu vidéo. Côté écoles d'ingénieurs agricoles, Bordeaux Sciences Agro et l'Institut Agro (Rennes-Angers, Dijon, Montpellier) marient sciences du vivant et ingénierie. Bon compromis si tu veux du croisement disciplinaire.
>
> Pour l'insertion pro, tu peux aussi consulter InserSup (données publiques sur les diplômes d'ingénieur) — ça te donnera des repères fiables formation par formation.
>
> Une question pour avancer : qu'est-ce qui te plaît le plus dans les maths-physique aujourd'hui — la modélisation, l'expérimentation, ou l'application à un domaine concret (vivant, technique, numérique) ? Ça aiderait à resserrer la piste qui matche le mieux ton profil.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré 'environ la moitié des écoles d'ingénieurs sont accessibles directement après le bac' (chiffre approximatif non sourcé). Précisé que les écoles d'ingénieurs agricoles citées existent bien sous ces noms (Bordeaux Sciences Agro et Institut Agro confirmés). Allégé légèrement la conclusion pour plus de naturel.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #14 — `A1` iter 13 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **86**, recommandée critique `flag`)
**Latence** : 82.3s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique, profil scientifique solide, mais la prépa MPSI ne m'attire pas du tout. C'est quoi les écoles d'ingé post-bac qui valent vraiment le coup, en alternative ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un profil maths-physique costaud mais l'idée de la prépa MPSI ne te parle pas, et tu cherches des voies post-bac plus directes vers l'ingénierie — c'est ça ?
>
> Légitime comme questionnement, l'écosystème français a pas mal d'alternatives au couple prépa+concours. Voici 3 pistes à explorer :
>
> **Écoles d'ingénieur post-bac en cursus intégré (2+3 ans)**
> Une part importante des écoles d'ingénieur françaises est accessible directement après le bac, en cursus intégré 5 ans. La sélection à l'entrée et la pédagogie varient beaucoup d'une école à l'autre. À vérifier systématiquement avant de candidater : l'accréditation CTI (référentiel officiel des diplômes d'ingénieur) et les données d'insertion publiées sur InserSup.
>
> **Réseaux INSA / UT / Polytech avec cycle préparatoire intégré**
> Les réseaux INSA (Lyon, Toulouse, Rennes…), Universités de Technologie (UTC, UTT, UTBM) et Polytech proposent un cycle préparatoire intégré de 2 ans suivi d'un cycle ingénieur de 3 ans, sans concours intermédiaire si tu valides. Profils scientifiques avec un bon dossier maths-physique sont dans la cible. Frais publics modérés et large palette de spécialités au choix après le tronc commun.
>
> **Cursus ingénieur agro / hybride sur Parcoursup**
> Bordeaux Sciences Agro et l'Institut Agro (Rennes-Angers, Dijon, Montpellier) proposent des cursus ingénieur post-bac sur Parcoursup, avec une vraie dimension sciences + terrain et une hybridation forte entre sciences dures et applications (vivant, environnement, agro-alimentaire). Frais publics modérés, profils parfois moins saturés que les écoles tech mainstream.
>
> Qu'est-ce qui pèse le plus pour toi dans ton choix : la dimension concrète sur le terrain, la possibilité de garder plusieurs portes de spécialisation ouvertes longtemps, ou plutôt la robustesse classique d'un diplôme d'ingénieur reconnu ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la mention 'bonne moitié' (chiffre flou non sourcé) ; précisé que CTI et InserSup sont les références officielles ; nuancé Cnam (formation continue / pas direct post-bac, donc reformulé en complément possible plutôt qu'option principale) ; remplacé par une 3e piste plus alignée post-bac (INSA / UT en cycle préparatoire intégré, qui correspond mieux au profil).

_Décision recommandée par critique : `flag` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #15 — `A1` iter 14 (catégorie `lyceen_post_bac`, axe 1, seed_idx 2)

**Décision** : `flag` (score **78**, recommandée critique `flag`)
**Latence** : 73.2s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?

**Question (refined par Phase 4)** :
> Je vois bio-informatique, finance quant et jeu vidéo qui m'attirent tous les trois — quelles voies post-bac précises tu vois sans passer par MPSI ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu cherches des voies scientifiques exigeantes mais hybrides — où les maths servent à toucher du concret (vivant, marchés, jeu) — sans le rail classique prépa-écoles. C'est une recherche saine, et les formats post-bac hybrides se sont multipliés ces dernières années. Voici trois familles à explorer :
>
> - **Écoles d'ingénieurs post-bac avec parcours de spécialisation.** Plusieurs écoles sont accessibles directement après le bac via Parcoursup, avec un cycle intégré (prépa interne + cycle ingé) et une spécialisation possible en bio-info, data/finance ou informatique appliquée en fin de cursus. Sélectivité et frais varient beaucoup selon l'école : à creuser au cas par cas sur les fiches Parcoursup.
>
> - **BUT scientifiques (informatique, statistiques, mesures physiques) puis poursuite ciblée.** Sur Parcoursup, généralement plus accessibles que les écoles post-bac, coût public modéré. Tremplin classique vers une école d'ingé en admissions parallèles ou un master spécialisé (bio-info, jeu vidéo, data). À regarder : les fiches d'insertion publiées par les IUT eux-mêmes pour avoir une idée des débouchés réels.
>
> - **Bachelors universitaires ou privés hybrides.** Certaines universités et écoles proposent des bachelors mixant info + appli métier (santé, finance, création numérique). Format souvent moins balisé que l'école d'ingé, mais utile si tu veux explorer avant de te spécialiser. Le Cnam offre aussi des modules en IA, finance quantitative ou bio-informatique qui peuvent compléter un cursus principal. À regarder cas par cas — coût, reconnaissance, débouchés varient.
>
> Pour t'aider à trancher : qu'est-ce qui t'attire le plus dans ces trois domaines — la dimension recherche/labo (bio-info), la dimension produit/équipe (jeu vidéo), ou la dimension chiffres/marchés (finance quant) ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **19/25** / posture **22/25** / cohérence **21/25** / hallucination **16/25** = **78/100**

**Corrections suggérées par le critique** :
> Retiré 'environ une centaine d'écoles' (chiffre Onisep non vérifiable précisément) et 'InserSup' cité comme source de données précises (risque de surinterprétation). Reformulé pour rester sur des descriptions qualitatives vérifiables. Conservé reformulation + 3 options pondérées + question finale.

_Décision recommandée par critique : `flag` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #16 — `A1` iter 15 (catégorie `lyceen_post_bac`, axe 1, seed_idx 3)

**Décision** : `flag` (score **84**, recommandée critique `flag`)
**Latence** : 86.5s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles sont les meilleures formations en cybersécurité en France ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths et je m'intéresse à la cybersécurité, mais la prépa MPSI ne me parle pas. Quelles voies je peux explorer ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu cherches une voie vers la cybersécurité qui valorise ton profil scientifique, sans passer par la case prépa classique. C'est une démarche légitime, et les options existent.
>
> Voici trois pistes à explorer, chacune avec sa logique propre :
>
> • **Écoles d'ingénieurs post-bac avec spécialisation cyber** : plusieurs écoles d'ingénieurs recrutent directement après le bac via un cycle préparatoire intégré, et certaines proposent une majeure cybersécurité dès les premières années. Tu évites la pression de la prépa tout en visant un diplôme d'ingénieur reconnu. Sélectivité et frais varient selon le statut (public vs privé), à creuser au cas par cas sur Parcoursup.
>
> • **BUT Réseaux & Télécoms ou BUT Informatique parcours cybersécurité** : ces cursus universitaires en 3 ans offrent une approche concrète et professionnalisante, accessibles via Parcoursup. Frais de scolarité réduits (formation publique). Tu peux ensuite poursuivre en école d'ingé sur titre, en master spécialisé, ou viser directement l'emploi.
>
> • **Licences informatiques + masters cyber, ou bachelors spécialisés** : la voie universitaire classique (licence info puis master sécurité/cybersécurité) reste solide et flexible. Côté bachelors privés, certains se concentrent sur la cyber appliquée (audit, pentest, ethical hacking). Coût plus élevé pour le privé, mais format souvent plus pratique et orienté projet.
>
> Avant de trancher, demande-toi ce qui te motive le plus : la rigueur théorique d'un cursus ingénieur long, le concret immédiat d'un BUT, ou un parcours universitaire que tu peux infléchir au fil des années ? Et tu te projettes plutôt en environnement entreprise, en labo de recherche, ou en indépendant ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **22/25** / cohérence **23/25** / hallucination **18/25** = **84/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre 'environ une centaine d'écoles' (non sourçable précisément) et 'milliers de formations' (formulation vague qui sonne inventée). Retiré la mention InserSup pour les BUT (pas systématiquement disponible par formation). Précisé que le Cnam est plutôt un parcours en formation continue/alternance, pas un cursus initial post-bac classique.

_Décision recommandée par critique : `flag` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #17 — `A1` iter 16 (catégorie `lyceen_post_bac`, axe 1, seed_idx 4)

**Décision** : `keep` (score **91**, recommandée critique `keep`)
**Latence** : 71.8s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

**Question (refined par Phase 4)** :
> Tu peux m'aider à comparer ENSEIRB-MATMECA et EPITA si je veux faire de la cybersécurité ? J'hésite vraiment entre les deux.

**Answer (refined par Phase 4)** :

> Si je te suis bien, tu te projettes sur la cybersécurité et tu cherches à départager une école d'ingé publique souvent post-prépa (ENSEIRB-MATMECA) et une école privée post-bac orientée tech (EPITA). C'est une vraie question, et c'est plutôt sain de la creuser maintenant plutôt que de trancher au feeling.
>
> Quelques pistes pour structurer ta réflexion :
>
> • **ENSEIRB-MATMECA (publique, Bordeaux INP)** : diplôme d'ingénieur reconnu, frais de scolarité publics modérés, filière info avec une dimension cyber solide et très charpentée scientifiquement. L'accès principal passe par prépa, mais des admissions parallèles existent (via BUT ou L2/L3). Pertinent si tu vises la profondeur théorique et un coût maîtrisé.
>
> • **EPITA (privée, post-bac)** : accessible directement après le bac via concours, spécialisation cybersécurité qui se construit plutôt en deuxième moitié de cursus, fort réseau pro et pédagogie très orientée pratique métier. Frais de scolarité nettement plus élevés qu'une école publique, à mettre en balance avec la facilité d'accès et l'aspect concret dès les premières années.
>
> • **Voie hybride à explorer** : un BUT Réseaux & Télécoms ou Informatique avec parcours cyber, suivi d'une école d'ingé en admission parallèle ou d'un master cyber universitaire. Plus progressif, souvent moins coûteux, et ça te laisse le temps de tester ton appétence cyber avant un engagement long.
>
> Une question pour toi : qu'est-ce qui pèse le plus dans ton choix aujourd'hui — le coût, le mode d'accès (concours post-bac vs prépa), ou le type de pédagogie (très théorique vs très orientée pratique) ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **23/25** / cohérence **23/25** / hallucination **22/25** = **91/100**

**Corrections suggérées par le critique** :
> Retiré la mention non sourcée 'L'ONISEP rappelle que…' (risque de citation factice). Précisé que les frais EPITA sont élevés sans chiffrer. Ajouté nuance sur le fait que la majeure cyber EPITA arrive en fin de cursus (pas dès la première année) pour éviter une simplification trompeuse.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #18 — `A1` iter 17 (catégorie `lyceen_post_bac`, axe 1, seed_idx 5)

**Décision** : `flag` (score **78**, recommandée critique `flag`)
**Latence** : 75.5s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Bon en code mais CS classique me lasse, y'a quoi d'autre comme voies ?

**Question (refined par Phase 4)** :
> Je me débrouille bien en code mais l'idée du CS pur me lasse déjà, y'a quoi d'autre comme voies possibles ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu codes plutôt à l'aise mais l'idée d'enchaîner des années sur du CS pur te refroidit — tu cherches du concret qui mélange le code avec autre chose. C'est une question hyper saine à se poser maintenant plutôt que dans deux ans.
>
> Trois pistes à pondérer selon ce qui te parle :
>
> - **Écoles d'ingénieur post-bac avec spécialités hybrides** : plusieurs écoles accessibles directement après le bac via un parcours intégré (généralement 5 ans) ouvrent sur des dominantes robotique, bio-informatique, jeu vidéo ou finance quantitative. Tu continues à coder, mais appliqué à un domaine concret. Le format intégré évite la prépa pure si ce n'est pas ton truc.
>
> - **BUT et formations Parcoursup orientées hybridation** : côté universitaire, les BUT informatique proposent des colorations métier (data, image, cybersécu) et certaines écoles d'ingénieur publiques (notamment dans l'agro ou l'environnement) ouvrent à des profils code appliqués au vivant ou aux systèmes physiques. Frais modérés, parcours plus progressif que la prépa.
>
> - **Formations modulables type Cnam** : le Cnam propose des cursus en informatique, IA, robotique ou bio-informatique avec des certificats et parcours modulables, parfois en parallèle d'études ou d'un job. Plus souple si tu veux tester un domaine avant de t'engager sur un long cursus.
>
> Pour creuser : qu'est-ce qui t'allume vraiment dans le code aujourd'hui — résoudre des problèmes complexes, fabriquer des objets qui bougent, manipuler des données, créer des images ou des jeux ? La réponse oriente assez fort vers une des trois pistes.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **18/25** / posture **22/25** / cohérence **21/25** / hallucination **17/25** = **78/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre 'environ une centaine d'écoles' non vérifiable et la mention 'moins compétitif que la prépa MPSI' (jugement comparatif fragile). Atténué les exemples d'écoles agricoles (Bordeaux Sciences Agro, Institut Agro Rennes-Angers) en formulation générique car non sourcés ici. Retiré 'débouchés documentés via InserSup' (sur-précision). Conservé la posture conseiller et la question finale qui sont solides.

_Décision recommandée par critique : `flag` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #19 — `A1` iter 18 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 79.8s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique, j'ai de bonnes notes mais l'idée de la prépa MPSI me bloque — c'est trop abstrait pour moi. Quelles alternatives concrètes je pourrais explorer pour rester sur un profil scientifique solide ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu aimes les sciences mais l'aspect très théorique de la MPSI ne te parle pas — tu cherches du concret, du tangible, de l'appliqué. C'est une demande légitime, et plusieurs chemins mènent à un profil scientifique solide sans passer par la prépa.
>
> Trois pistes à explorer :
>
> **Les écoles d'ingénieurs post-bac (parcours intégré 5 ans)** — un grand nombre d'écoles recrutent directement après le bac via Parcoursup, avec une prépa intégrée et des projets concrets dès la première année. Souvent moins compétitif que la voie prépa classique, et tu restes dans la même école pendant les 5 ans, ce qui aide à tenir la motivation sur la durée.
>
> **Le BUT (Bachelor Universitaire de Technologie)** — formation très appliquée en 3 ans, alternance souvent possible, débouché direct sur le marché OU poursuite en école d'ingé / master. Bon compromis si tu veux mettre les mains dans le cambouis rapidement tout en gardant la porte ouverte vers du bac+5.
>
> **Les formations spécialisées en sciences appliquées** — type robotique, bio-informatique, agronomie, sciences de l'environnement. Certaines écoles d'agronomie (Bordeaux Sciences Agro, Institut Agro Rennes-Angers ou Dijon) recrutent post-bac via Parcoursup avec un cursus ingénieur. Plus niche, mais pile dans l'esprit "concret" si un domaine te parle vraiment.
>
> Pour creuser : parmi ces trois directions, laquelle te fait le plus envie quand tu te projettes dans 3-4 ans ? Et qu'est-ce qui te rebute le plus dans la MPSI — la charge de travail, le manque de pratique, l'ambiance compétitive, ou autre chose ? Ça m'aide à affiner avec toi.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **23/25** / hallucination **18/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre 'environ une centaine' (non sourcé précisément) au profit d'une formulation plus prudente. Atténué la mention 'milliers de formations sur Parcoursup' qui était imprécise. Conservé la structure reformulation + 3 pistes pondérées + double question finale.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #20 — `A1` iter 19 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 88.7s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?

**Question (refined par Phase 4)** :
> Je suis bon en maths et physique mais l'idée de la prépa MPSI me bloque. Quelles écoles d'ingénieur post-bac valent vraiment le coup ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu es à l'aise scientifiquement mais le format prépa-concours ne te parle pas, et tu cherches une voie qui démarre direct après le bac sans passer par MPSI. C'est un choix tout à fait légitime, et il existe plusieurs alternatives solides à explorer.
>
> Voici trois pistes qui peuvent matcher ton profil :
>
> • **Écoles d'ingénieur post-bac à cursus intégré (2+3 ans)** : tu fais tes années de prépa intégrée dans l'école elle-même, sans le format concours-bachotage. Plusieurs réseaux accessibles via Parcoursup (INSA, UT, Polytech, Icam, ESIEE, etc.), avec des sélectivités et thématiques variées — à comparer école par école selon ce qui t'attire (généraliste, info, mécanique, énergie...).
>
> • **BUT (ex-DUT) puis admission parallèle en école d'ingé** : démarrage très concret avec projets et stages dès la première année, puis passerelle possible vers une école d'ingénieur en alternance ou via concours dédiés (Polytech, INSA, ENSEA…). C'est la voie souvent choisie par les profils qui veulent du tangible avant de potentiellement pousser vers ingé. Coût modéré (formation publique).
>
> • **Écoles d'ingénieurs agro/environnement post-bac** : Bordeaux Sciences Agro, Institut Agro (Rennes-Angers, Dijon, Montpellier) sont accessibles via Parcoursup et forment des ingénieurs sur des thématiques hybrides (agronomie, environnement, agroalimentaire, data appliquée au vivant). Si tu es attiré par l'hybridation sciences + impact concret, ça mérite un coup d'œil.
>
> Ce ne sont que trois pistes parmi d'autres — il existe aussi des écoles plus spécialisées (chimie, biotech, numérique) qui peuvent coller selon la thématique qui te tire l'œil.
>
> Qu'est-ce qui te ferait avancer le plus maintenant : creuser une de ces pistes en détail, ou d'abord clarifier ce que tu cherches dans le métier d'ingé (terrain, recherche, business, hybridation sciences/impact) ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
>   Date : 2026 (mis à jour régulièrement)
>   Extrait clé : Environ 100 écoles d'ingénieurs (moitié de l'offre) sont directement accessibles après le bac. Les parcours intégrés 2+3 ans offrent une alternative moins compétitive que la prépa.
>
> - URL : https://www.parcoursup.gouv.fr/trouver-une-formation/quelles-formations-sont-accessibles-sur-parcoursup-1318
>   Date : 2026
>   Extrait clé : Plus de 23 000 formations disponibles sur Parcoursup, incluant écoles d'ingénieur post-bac, BUT et écoles agricoles avec cursus ingénieur (Bordeaux Sciences Agro, Institut Agro Rennes-Angers/Dijon).
>
> - URL : https://www.education.gouv.fr/depp/inserjeunes-l-insertion-des-jeunes-apres-une-formation-en-voie-professionnelle-307956
>   Date : 2025 (données 2024)
>   Extrait clé : InserJeunes mesure l'insertion professionnelle à 6, 12, 18 et 24 mois post-formation. Pour les diplômes d'ingénieur, consulter InserSup (données 2023 récemment diffusées).
>
> - URL : https://formation.cnam.fr/ecole-du-numerique-et-de-l-intelligence-artificielle-ia--1480579.kjsp
>   Date : 2
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la mention 'environ la moitié des écoles d'ingé' (chiffre ONISEP non vérifié précisément) remplacée par formulation plus prudente. Retiré 'Cnam' comme exemple hybride car l'offre citée (IA/robotique/bio-info/finance quanti post-bac) n'est pas son cœur (plutôt formation continue/adultes). Resserré la reformulation et clarifié que les exemples d'écoles sont indicatifs, pas exhaustifs.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #21 — `A2` iter 0 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `flag` (score **84**, recommandée critique `keep`)
**Latence** : 86.8s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je hésite entre éco-gestion, droit et sciences-po, comment choisir ?

**Question (refined par Phase 4)** :
> Salut, je suis en terminale SES-HG et je tourne en rond entre éco-gestion, droit et sciences-po — j'aime les enjeux de société et l'utilité sociale, mais je suis perdu sur la voie qui me correspond. Comment je peux y voir plus clair ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un profil qui aime comprendre les sciences sociales et tu cherches une voie utile socialement sans te fermer trop tôt — c'est une position très saine, pas une indécision.
>
> Avant de trancher, ça peut valoir le coup d'aller fouiller les fiches détaillées sur Parcoursup et l'ONISEP pour chacune de ces pistes. Voici trois directions à comparer sereinement :
>
> - **Licence de droit à l'université** : filière très demandée sur Parcoursup, accessible sans concours, avec un taux d'accès généralement ouvert selon les universités. Frais universitaires modérés. Le questionnaire d'auto-évaluation Parcoursup peut t'aider à tester si la rigueur juridique te parle. Débouchés variés (avocat, magistrat, juriste d'entreprise, notaire, fonction publique).
>
> - **Licence éco-gestion** : également via Parcoursup, sélectivité variable selon les universités. Bon socle si tu veux garder une porte ouverte vers les politiques publiques, l'analyse économique ou le management. Cohérent avec ta spé SES.
>
> - **Sciences Po / IEP régional** : voie sélective. Concours commun pour le réseau des IEP en région, ou dossier + oral pour Sciences Po Paris et ses campus délocalisés. Formation pluridisciplinaire (droit, éco, histoire, science politique), forte dimension enjeux de société. Pense à vérifier les calendriers des concours sur les sites officiels et à anticiper une éventuelle préparation.
>
> Une question pour avancer : sur ces trois pistes, laquelle te fait le plus envie quand tu imagines ton quotidien d'étudiant — éplucher des textes de loi, modéliser un phénomène économique, ou débattre de politiques publiques ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **20/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **84/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre 'trentaine de débouchés ONISEP' (non sourçable précisément) et 'épreuves au printemps 2026' (date concours IEP non vérifiée). Adouci 'plus sélective que le droit' qui est une généralisation fragile. Reformulé la phrase d'ouverture pour mieux refléter le profil SES-HG (sciences sociales, pas 'analyse et concret').

_Décision recommandée par critique : `keep` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #22 — `A2` iter 1 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **86**, recommandée critique `flag`)
**Latence** : 80.2s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète ?

**Question (refined par Phase 4)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète ?

**Answer (refined par Phase 4)** :

> Si je te suis bien, tu cherches à voir ce qui change vraiment entre Sciences-Po Paris et un IEP en région, pour repérer ce qui collerait le mieux à ton profil et à ton contexte.
>
> Trois pistes à comparer :
>
> • **Sciences-Po Paris** : admission via Parcoursup (dossier + oraux, calendrier resserré sur le 1er semestre), répartition sur 7 campus thématiques (Paris + 6 campus délocalisés) pour environ un millier de places au total. Réseau national/international dense, sélectivité haute, forte exposition aux carrières publiques et internationales. Plutôt cohérent si tu cherches un grand réseau et une projection internationale forte.
>
> • **Concours commun 7 IEP** (Aix, Lille, Lyon, Rennes, Saint-Germain-en-Laye, Strasbourg, Toulouse) : une épreuve unique au printemps, autour de 1 200 places, taux d'accès faible (autour de 10%), frais d'inscription à vérifier sur le site officiel du concours. Tu classes tes vœux par préférence et tu peux viser un IEP proche de chez toi. Ancrage régional plus marqué, formation de fond comparable.
>
> • **IEP hors concours commun** (Bordeaux, Grenoble, et Sciences-Po Paris lui-même) : calendriers et épreuves propres à chaque école, identités pédagogiques spécifiques. À regarder en complément si une de ces villes te parle particulièrement.
>
> Côté débouchés, les IEP ouvrent globalement vers les mêmes familles (droit public, fonction publique, journalisme, communication, international), avec des nuances de réseau selon la zone géographique. Pour un profil utilité sociale + pragmatique hors-IDF, un IEP de proximité peut alléger la charge logement et permettre de construire un tissu pro local dès la L1.
>
> Quand tu te projettes dans 3 ans, tu te vois plutôt dans un grand réseau parisien aux ramifications larges, ou ancré dans une ville où tu construis ton réseau de proximité au fil des années ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la date précise '25 avril 2026' et le tarif '210€' (chiffres précis non sourçables avec garantie), remplacés par formulations prudentes ('printemps', 'frais à vérifier'). Ajusté '1 000 places' Sciences-Po Paris en 'environ un millier' et '1 220 places' en 'autour de 1 200'. Ajouté nuance sur l'IEP de Paris (qui fait partie des hors-concours commun) pour éviter raccourci.

_Décision recommandée par critique : `flag` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #23 — `A2` iter 2 (catégorie `lyceen_post_bac`, axe 1, seed_idx 2)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 86.0s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Pour un profil SES-HG, quel master pro paie mieux à 5 ans : droit ou éco ?

**Question (refined par Phase 4)** :
> J'hésite entre un master pro en droit ou en éco — concrètement, lequel paie mieux à 5 ans pour un profil SES-HG comme le mien ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu veux anticiper le retour sur investissement avant de t'engager — du concret, pas du vent. C'est une question saine à se poser, même si la réponse honnête est qu'à 17 ans, viser un salaire précis à 5 ans est très spéculatif.
>
> La vraie variable, ce n'est pas tant « droit vs éco » au niveau licence, mais le M2 que tu vises, le secteur d'embauche, et si tu fais ton master en alternance ou non. Voici trois pistes à explorer sans hiérarchie :
>
> - **Master pro éco-gestion (finance, contrôle, audit, RH, data)** : débouchés très entreprise, alternance fréquente en M2 — appréciable si ton budget est tendu puisque tu es rémunéré pendant l'alternance. Profils SES s'y retrouvent bien.
>
> - **Master pro droit (affaires, social, notarial, fiscal)** : parcours universitaire plus long et linéaire (licence + M1 + M2), débouchés diversifiés. Le droit des affaires et le notariat sont réputés bien rémunérés en cabinet, mais l'écart se creuse surtout après plusieurs années d'expérience.
>
> - **Voie hybride double licence droit-éco ou IEP régional** : sélective en entrée, profil polyvalent recherché ensuite (cabinet conseil, banque, fonction publique). Les IEP régionaux peuvent matcher ta contrainte de localisation hors Île-de-France.
>
> Deux questions pour avancer : qu'est-ce qui te tire le plus aujourd'hui — manipuler des chiffres et raisonner économique, ou décortiquer des textes et argumenter ? Et est-ce que tu te vois plutôt en cabinet/cabinet conseil, en entreprise, ou dans le public ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré l'affirmation non sourcée 'la licence droit est récemment la plus demandée sur Parcoursup' et la mention chiffrée 'trentaine de métiers' (chiffres non vérifiables). Reformulé '7 IEP hors Île-de-France' en évoquant simplement le réseau IEP régionaux sans chiffre exact. Renforcé la reformulation initiale et ajouté une seconde question ouverte pour rééquilibrer la posture (éviter l'effet conclusion).

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #24 — `A2` iter 3 (catégorie `lyceen_post_bac`, axe 1, seed_idx 3)

**Décision** : `keep` (score **86**, recommandée critique `flag`)
**Latence** : 95.4s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?

**Question (refined par Phase 4)** :
> J'ai des notes plutôt moyennes en terminale spé SES-HG, est-ce que je peux quand même viser un IEP régional ou Sciences-Po avec mon profil ?

**Answer (refined par Phase 4)** :

> Si je te suis bien, tu te demandes si un dossier 'correct mais pas brillant' peut suffire pour viser un IEP régional ou Sciences-Po, sachant que tu hésites encore entre plusieurs domaines. C'est une vraie question de stratégie, et la poser tôt te laisse le temps de bouger.
>
> Avant de regarder les options, deux choses utiles à clarifier pour toi : qu'est-ce que tu mets derrière 'moyennes' (autour de 12, autour de 14 ?) et est-ce que c'est stable ou en progression sur l'année ? Les jurys lisent autant la trajectoire que la moyenne brute.
>
> Voici trois pistes qui peuvent coller à ton profil hors-IDF avec budget modéré :
>
> • **Concours commun des IEP de région** (réseau de 7 IEP : Aix, Lille, Lyon, Rennes, Saint-Germain-en-Laye, Strasbourg, Toulouse) — un seul concours écrit, frais d'inscription modérés, sélectivité réelle mais le concours redonne sa chance à un dossier moyen si la prépa est sérieuse. À considérer si tu aimes l'idée de te préparer à un examen plutôt qu'à un dossier.
>
> • **Sciences-Po Paris et ses campus thématiques en région** — admission par dossier Parcoursup puis oraux, profil pluridisciplinaire valorisé. Ici le dossier pèse lourd : engagements, lectures, motivation argumentée. À considérer si ton bulletin progresse et si tu peux mettre en valeur des activités hors-scolaires.
>
> • **Licence de droit ou d'éco-gestion à l'université publique** — voie large via Parcoursup, coût très modéré, et il existe des passerelles vers les IEP après L1 ou L2 (admissions parallèles). À considérer comme plan robuste : tu sécurises une formation solide tout en gardant la porte IEP ouverte un an plus tard.
>
> Deux questions pour t'aider à arbitrer : qu'est-ce qui t'attire le plus dans l'idée d'un IEP — la pluridisciplinarité éco/droit/sciences po, le format concours, ou les débouchés perçus ? Et est-ce que tu te vois plutôt en mode 'je joue gros sur un concours' ou 'je sécurise une L1 et je rejoue plus tard' ? Tes réponses peuvent vraiment orienter le choix.

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **23/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré chiffres précis non vérifiables (1220 places, 210€, 360k candidatures, 41,6%, date 25 avril 2026) au profit de fourchettes prudentes. Renforcé la pondération des 3 options et la posture non-prescriptive. Ajouté un cadrage sur le 'plutôt moyennes' pour éviter de présupposer le niveau réel.

_Décision recommandée par critique : `flag` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #25 — `A2` iter 4 (catégorie `lyceen_post_bac`, axe 1, seed_idx 4)

**Décision** : `keep` (score **91**, recommandée critique `keep`)
**Latence** : 52.1s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Tremplin/Passerelle pour HEC, c'est quoi exactement et c'est pour qui ?

**Question (refined par Phase 4)** :
> Tremplin/Passerelle pour HEC, c'est quoi exactement et c'est pour qui ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu te demandes si ces voies 'admission parallèle' vers HEC sont compatibles avec ton profil SES-HG, alors que tu hésites encore entre éco, droit, sciences-po et IEP. C'est une bonne question à te poser tôt, parce que ces dispositifs ne se préparent pas n'importe quand dans le cursus.
>
> Voici 3 pistes à explorer, sans hiérarchie :
>
> • **Tremplin / Passerelle (concours d'admission parallèle aux écoles de commerce)** : ce sont des concours qui permettent d'intégrer une grande école de management (dont HEC) après un cursus déjà entamé. Tremplin 1 / Passerelle 1 visent plutôt un niveau bac+2 (BTS, BUT, L2), Tremplin 2 / Passerelle 2 plutôt un niveau bac+3 (licence, BUT 3). Sélectivité forte, frais de scolarité élevés ensuite (école privée), mais débouchés business reconnus. À considérer si tu te projettes management/finance — pas une voie directe post-bac, donc à anticiper sans en faire une obsession dès la terminale.
>
> • **Sciences-Po ou IEP régional via Parcoursup** : voie directe post-bac, dossier + oraux pour Sciences-Po Paris, concours commun pour les IEP de région (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse). Coût modéré côté IEP publics (compatible budget hors-IDF), pluridisciplinaire (droit, éco, sciences-po), cohérent avec un profil SES-HG indécis et une sensibilité utilité sociale.
>
> • **Licence de droit ou éco-gestion à la fac** : voie ouverte, coût faible, te laisse 2-3 ans pour affiner. Tu peux ensuite viser un master, un IEP en admission parallèle, ou justement un Tremplin/Passerelle vers HEC. Option pragmatique si tu veux garder toutes les portes ouvertes — sachant que selon les facs et les années, la sélectivité réelle d'une licence d'éco-gestion peut être plus marquée que celle d'une licence de droit.
>
> Question pour toi : est-ce que ce qui t'attire dans 'HEC', c'est plutôt le prestige de l'école, le type de métier (business, conseil) ou l'ouverture internationale ? Ça aiderait à voir si la voie directe vaut mieux qu'un détour par la fac ou un IEP.

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **22/25** / hallucination **22/25** = **91/100**

**Corrections suggérées par le critique** :
> Précisé que Tremplin 1/Passerelle 1 visent bac+2 et Tremplin 2/Passerelle 2 visent bac+3 (formulation initiale floue). Retiré la mention 'd'après Parcoursup' qui sonnait comme une source précise non vérifiable, remplacée par formulation prudente. Légères normalisations stylistiques.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #26 — `A2` iter 5 (catégorie `lyceen_post_bac`, axe 1, seed_idx 5)

**Décision** : `keep` (score **92**, recommandée critique `keep`)
**Latence** : 55.4s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Sciences-Po ça vaut le coup ou c'est juste un nom ?

**Question (refined par Phase 4)** :
> Sciences-Po, ça vaut vraiment le coup ou c'est juste un nom prestigieux ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu te demandes si l'aura de Sciences-Po justifie vraiment l'effort, ou si c'est surtout une étiquette qui brille sur un CV. C'est une question saine à se poser, surtout quand on hésite encore entre plusieurs domaines.
>
> Voici trois pistes à mettre en balance, sans hiérarchie :
>
> • **Sciences-Po Paris et ses campus régionaux** — admission via Parcoursup avec dossier + écrit + oral, calendrier resserré entre janvier et mai. Formation pluridisciplinaire (économie, droit, histoire, sciences sociales) qui résonne avec ton profil SES-HG. Sélectivité forte, mais réseau dense et forte ouverture internationale (3e année à l'étranger).
>
> • **Concours commun des IEP de région (Réseau ScPo : Aix, Lille, Lyon, Rennes, Saint-Germain-en-Laye, Strasbourg, Toulouse)** — épreuves communes au printemps, accès sélectif mais coût de vie souvent plus doux qu'à Paris. Pertinent si tu veux rester hors Île-de-France et garder une formation généraliste avec un ancrage régional.
>
> • **Licence universitaire (droit, économie-gestion, ou double licence droit–science politique)** — accès Parcoursup classique, taux d'accès plus ouvert que les IEP, coûts modérés. Les doubles licences laissent ouverte la porte d'un IEP en master si tu veux y revenir plus tard.
>
> Le "nom" Sciences-Po a une vraie valeur réseau, mais il n'est pas l'unique chemin vers les métiers qui peuvent t'intéresser (droit, politique publique, journalisme, conseil). L'utilité sociale que tu cherches se trouve dans plusieurs de ces parcours.
>
> Qu'est-ce qui compterait le plus pour toi à ce stade : la pluridisciplinarité de la formation, la proximité géographique, ou la possibilité de te spécialiser progressivement ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **23/25** / hallucination **22/25** = **92/100**

**Corrections suggérées par le critique** :
> Précisé que le concours commun IEP regroupe 7 IEP via Réseau ScPo (Saint-Germain-en-Laye nom complet), reformulé 'double licence droit–sciences-po' en 'double licence droit–science politique' (intitulé universitaire réel), allégé le verbiage et resserré la question finale pour rester non-prescriptif.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #27 — `A2` iter 6 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `keep` (score **88**, recommandée critique `keep`)
**Latence** : 94.6s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je hésite entre éco-gestion, droit et sciences-po, comment choisir ?

**Question (refined par Phase 4)** :
> Je hésite entre éco-gestion, droit et sciences-po pour l'année prochaine, je sais pas comment trancher entre ces trois voies, tu peux m'aider ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu te sens tiraillé entre trois pistes qui te parlent toutes, et c'est l'absence de critère clair pour les départager qui te bloque — c'est très commun avec une spé SES-HG, ces trois voies sont cohérentes avec ton profil.
>
> Voilà trois angles pour les comparer concrètement, en gardant en tête que la phase de vœux Parcoursup s'ouvre en janvier et que le concours commun des IEP se passe au printemps :
>
> **Licence droit (université publique)**
> C'est l'une des licences les plus demandées sur Parcoursup, avec un taux d'accès généralement plus large que l'éco-gestion. Frais universitaires modérés, formation longue (licence + master quasi-obligatoire pour la plupart des métiers : avocat·e, magistrat·e, juriste d'entreprise). Cohérent si tu es attiré par une expertise pointue et l'utilité sociale concrète, avec un budget contenu hors Île-de-France.
>
> **Licence éco-gestion (université publique)**
> Plutôt plus sélective à l'entrée que le droit selon les universités, mais ouverture large derrière (entreprise, finance publique, économie sociale et solidaire, recherche). Frais universitaires modérés aussi, master nécessaire pour spécialiser. Pertinent si tu veux garder de l'optionalité plutôt que verrouiller un métier précis dès le départ.
>
> **Sciences Po Paris / concours commun des 7 IEP régionaux**
> Le concours commun couvre Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse (épreuves au printemps, frais d'inscription à vérifier sur le site officiel). Sciences Po Paris recrute via Parcoursup avec écrits + oraux, sur plusieurs campus. Voie pluridisciplinaire (droit, éco, histoire, sciences politiques) pertinente pour un profil indécis multi-domaines comme le tien.
>
> Une question pour t'aider à démêler : quand tu te projettes dans 5 ans, tu te vois plutôt **expert d'un domaine pointu** (juriste, économiste spécialisé), ou **généraliste qui touche à plusieurs sujets** (politiques publiques, secteur associatif, international) ? Ça resserre déjà énormément le choix.

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **23/25** / hallucination **21/25** = **88/100**

**Corrections suggérées par le critique** :
> Retiré les chiffres précis non-sourçables (41,6% droit, 19,5% éco-gestion, 10% IEP, 1000 places Sciences Po, 210€, dates exactes Parcoursup/concours) qui risquent l'hallucination factuelle. Conservé la structure 3 options pondérées + reformulation + question finale, qui était déjà conforme à la posture conseiller.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #28 — `A2` iter 7 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **89**, recommandée critique `flag`)
**Latence** : 49.0s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète ?

**Question (refined par Phase 4)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète au quotidien et après le diplôme ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu vises l'univers Sciences-Po mais tu te demandes si Paris et un IEP de région ouvrent vraiment les mêmes portes — surtout en partant de province avec un budget mesuré. C'est une question saine à se poser maintenant, parce que les deux voies se ressemblent de loin mais se vivent très différemment au quotidien.
>
> Voici trois angles pour comparer concrètement, sans hiérarchiser :
>
> - **Sciences-Po Paris** : admission via Parcoursup (dossier + oraux) sur un calendrier serré au printemps. Recrutement national, plusieurs campus thématiques en région pour le 1er cycle, puis master à Paris. Coût de la vie parisien à anticiper, mais réseau et visibilité internationale parmi les plus forts en France.
>
> - **Réseau ScPo (concours commun des IEP de région)** : une épreuve écrite commune au printemps, sélectivité élevée, frais d'inscription à prévoir. Tu choisis ensuite l'IEP selon ton classement et tes vœux — utile si tu veux rester proche de chez toi, viser une ville précise, ou si le format concours te parle plus que le dossier Parcoursup.
>
> - **Licence universitaire (droit, éco, histoire, science politique)** avec objectif master Sciences-Po ou IEP en passerelle : option moins médiatisée mais solide, frais réduits, et tu gardes ouvertes les voies droit/justice (magistrature, notariat, juriste) documentées par l'ONISEP si l'IEP ne se concrétise pas.
>
> Les trois mènent à des métiers à forte utilité sociale, mais le quotidien étudiant, le coût et la pression du mode de sélection ne se ressemblent pas.
>
> Si tu te projettes dans 4 ans : tu te vois plus dans une grande métropole avec un réseau national-international, ou dans une ville à taille humaine avec un ancrage régional plus marqué ? Et le format concours écrit vs dossier+oral, lequel te stresse le moins ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **23/25** / cohérence **22/25** / hallucination **21/25** = **89/100**

**Corrections suggérées par le critique** :
> Retiré la liste nominative des 7 IEP du concours commun (Saint-Germain-en-Laye n'en fait pas partie, c'est Bordeaux qui est hors concours commun — risque factuel). Adouci 'Recrutement national très large' (formulation plus neutre). Ajouté nuance sur les passerelles master Sciences-Po accessibles depuis licence (pas seulement IEP région).

_Décision recommandée par critique : `flag` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #29 — `A2` iter 8 (catégorie `lyceen_post_bac`, axe 1, seed_idx 2)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 84.8s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Pour un profil SES-HG, quel master pro paie mieux à 5 ans : droit ou éco ?

**Question (refined par Phase 4)** :
> Profil SES-HG, master droit vs master éco — lequel mène à des métiers mieux rémunérés à 5 ans ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu cherches à anticiper le retour sur investissement entre droit et éco — c'est une question pragmatique légitime, et ton profil SES-HG ouvre clairement les deux portes.
>
> Voici trois angles pour réfléchir, sans te pousser dans une voie :
>
> • **Filière droit** : la licence droit est largement accessible sur Parcoursup, mais le tri se fait surtout en L2/L3 puis à l'entrée du master. La rémunération à 5 ans dépend énormément de la spécialité — le droit des affaires en cabinet est généralement mieux payé que le droit social ou pénal, mais l'accès au master correspondant est plus sélectif.
>
> • **Filière éco-gestion** : l'accès en licence éco-gestion est souvent plus sélectif que le droit pur. Les débouchés classiques (audit, finance, conseil, banque) sont réputés rémunérateurs en début de carrière, surtout après un master spécialisé dans une fac reconnue ou une école post-licence.
>
> • **IEP régional ou Sciences Po Paris** : ces voies hybrides (droit + éco + sciences sociales) gardent un large éventail de débouchés (haute fonction publique, conseil, privé). Le concours commun des IEP de région existe pour la première année, l'entrée est très sélective. Vérifie les dates et les places exactes sur le site officiel du concours commun avant de t'engager.
>
> Aucune de ces voies ne garantit un niveau de salaire précis à 5 ans : la spécialisation choisie en master, la qualité des stages, le réseau et la région d'exercice pèsent souvent plus que l'intitulé du diplôme initial.
>
> Quand tu te projettes dans 5 ans, qu'est-ce qui compte le plus pour toi : le niveau de salaire, le type de métier au quotidien, ou le sentiment d'utilité que tu cherches à mettre en avant ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré le chiffre précis '1 220 places' et la date 'avril 2026' du concours IEP non sourcés ; nuancé l'affirmation 'licence droit voie la plus demandée' (non sourcée) ; précisé que les ordres de grandeur salariaux ne sont pas chiffrés faute de source fiable.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #30 — `A2` iter 9 (catégorie `lyceen_post_bac`, axe 1, seed_idx 3)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 91.2s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?

**Question (refined par Phase 4)** :
> Avec 11 de moyenne en terminale SES-HG, est-ce que je peux viser un IEP régional, ou je dois plutôt me rabattre sur une licence à la fac ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu te demandes si ton profil te permet de viser des formations sélectives type IEP, ou s'il vaut mieux jouer la sécurité côté université. C'est une vraie question, et plusieurs portes restent ouvertes — regardons-les ensemble.
>
> **Piste 1 — Concours commun des 7 IEP régionaux (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse)**
> Un concours unique au printemps de terminale, autour d'un millier de places réparties sur les 7 campus. C'est sélectif (taux d'accès autour de 10 %), mais ton profil SES-HG colle bien au format pluridisciplinaire (éco, droit, sciences po, anglais). Avec 11 de moyenne, ce n'est pas joué d'avance, mais ça reste atteignable si tu prépares sérieusement les épreuves écrites — la moyenne brute compte moins que ta capacité à performer le jour J.
>
> **Piste 2 — Licence de droit ou d'éco-gestion à l'université de ta région**
> La licence droit est l'une des filières les plus demandées sur Parcoursup, avec un taux d'accès global plutôt confortable, alors qu'éco-gestion est nettement plus tendue. Cursus universitaire classique, frais publics faibles, et tu gardes la main pour viser ensuite un master sélectif, une admission parallèle en IEP en L2/L3, ou les concours admin/justice. Bon filet de sécurité qui n'est pas une voie de second choix.
>
> **Piste 3 — Sciences Po Paris et doubles licences (droit–éco, droit–sciences po)**
> Sciences Po Paris recrute par dossier Parcoursup puis oraux, sur 7 campus thématiques. Très sélectif, mais l'admission se joue plus sur la cohérence du projet, les écrits et l'oral que sur la moyenne brute. À pondérer avec la mobilité et le coût de vie, surtout si tu tiens à rester en province. Les doubles licences droit–éco ou droit–sciences po dans certaines facs sont aussi un compromis intéressant entre exigence et accessibilité.
>
> Avant de trancher, qu'est-ce qui pèse le plus pour toi : viser un concours sélectif quitte à mettre un gros coup de collier cette année, ou sécuriser une licence proche de chez toi qui te laisse rebondir ensuite ? Et est-ce que tu te vois plutôt sur un campus en province ou ouvert à bouger ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **22/25** / cohérence **22/25** / hallucination **21/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la date précise du concours commun IEP (25 avril 2026) et le chiffre exact de 1 220 places non vérifiables sans source explicite ; nuancé les taux d'accès Parcoursup en les présentant comme des ordres de grandeur ; allégé la mention des dates Sciences Po Paris pour éviter un chiffre daté incertain.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #31 — `A2` iter 10 (catégorie `lyceen_post_bac`, axe 1, seed_idx 4)

**Décision** : `keep` (score **92**, recommandée critique `keep`)
**Latence** : 94.7s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Tremplin/Passerelle pour HEC, c'est quoi exactement et c'est pour qui ?

**Question (refined par Phase 4)** :
> Le Tremplin/Passerelle pour HEC, ça marche comment et est-ce que ça pourrait me concerner avec mon profil ?

**Answer (refined par Phase 4)** :

> Si je te suis bien, tu as entendu parler du Tremplin/Passerelle HEC et tu te demandes si c'est une porte d'entrée envisageable avec ton profil littéraire-scientifique en spé SES-HG. C'est plutôt sain d'explorer plusieurs voies quand tu hésites encore entre éco, droit et sciences-po.
>
> D'abord un point de clarif : Tremplin et Passerelle sont des concours d'admission parallèle aux écoles de commerce du concours BCE/Ecricome. Ils ne sont pas accessibles directement après le bac. En gros, Tremplin 1 et Passerelle 1 visent les étudiant·es qui ont validé un bac+2 (BTS, BUT 2, L2), et Tremplin 2 / Passerelle 2 ciblent un niveau bac+3 (licence, BUT 3). Donc dans tous les cas, il faut d'abord bâtir un dossier ailleurs avant de tenter le concours.
>
> Trois pistes à mettre en balance, sans en privilégier une a priori :
>
> • Voie indirecte via Tremplin/Passerelle : tu fais d'abord une licence (éco-gestion, droit, AES) ou un BUT (GEA, TC), puis tu présentes le concours en bac+2 ou bac+3. Avantage : tu te laisses le temps de mûrir ton orientation et de consolider ton dossier. Inconvénient : école de commerce ensuite, avec des frais de scolarité élevés selon l'établissement visé.
>
> • Voie prépa ECG : prépa éco-gestion publique juste après le bac, puis concours BCE pour les grandes écoles de commerce. Exigeant intellectuellement, rythme dense, mais frais modérés en cadre public. Plutôt cohérent avec ta spé SES si tu es à l'aise avec un rythme soutenu.
>
> • Voie université + admissions parallèles : licence éco-gestion ou double licence droit-éco à la fac, puis master grande école via concours. Progression plus douce, frais modérés, et tu gardes la possibilité de réorienter si l'envie d'utilité sociale prend le pas sur le côté business pur.
>
> Une question pour toi : quand tu te projettes, c'est plutôt le label « grande école de commerce » qui t'attire, ou plutôt l'envie de bosser sur des sujets éco-droit avec un impact social concret ? La réponse oriente assez fortement les voies à creuser en priorité.

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **23/25** / hallucination **22/25** = **92/100**

**Corrections suggérées par le critique** :
> Précisé que Tremplin 1 vise bac+2 et Tremplin 2 / Passerelle 2 visent bac+3, pour éviter l'amalgame. Légère normalisation du style (tutoiement déjà bon, structure 3 options pondérées préservée).

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #32 — `A2` iter 11 (catégorie `lyceen_post_bac`, axe 1, seed_idx 5)

**Décision** : `keep` (score **92**, recommandée critique `keep`)
**Latence** : 73.1s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Sciences-Po ça vaut le coup ou c'est juste un nom ?

**Question (refined par Phase 4)** :
> Sciences-Po, ça vaut vraiment le coup ou c'est surtout pour le prestige du nom ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu te demandes si Sciences-Po c'est un vrai tremplin pour ce que tu veux faire, ou juste une étiquette qui sonne bien sur un CV. C'est une question saine à se poser, surtout quand on hésite encore entre plusieurs domaines.
>
> Trois pistes à regarder concrètement :
>
> - **Sciences-Po Paris et ses campus régionaux via Parcoursup** : admission par dossier puis oraux, plusieurs campus en province (Reims, Le Havre, Menton, Dijon, Poitiers, Nancy). Cursus très pluridisciplinaire (droit, éco, histoire, sciences sociales) — ça peut bien coller à un profil SES-HG encore en exploration. Sélectivité forte et frais de scolarité indexés sur les revenus familiaux, plus élevés qu'en fac publique pour les tranches hautes.
>
> - **Concours commun des 7 IEP régionaux** (Aix, Lille, Lyon, Rennes, Saint-Germain-en-Laye, Strasbourg, Toulouse) : épreuve unique au printemps, frais d'inscription au concours modestes, scolarité publique. Débouchés proches de Sciences-Po Paris (droit, fonction publique, journalisme, relations internationales) avec un ancrage régional souvent plus marqué.
>
> - **Licence universitaire (droit, éco-gestion, ou double licence droit–science politique selon les universités qui la proposent)** : voie la plus accessible via Parcoursup, taux d'accès généralement plus large en droit qu'en éco-gestion. Tu peux te spécialiser progressivement et tenter une admission parallèle en master à Sciences-Po ou dans un IEP plus tard si l'envie se confirme.
>
> Vu tes contraintes (hors Île-de-France, budget modéré, utilité sociale), un IEP régional ou la fac peuvent être plus alignés qu'un Sciences-Po Paris en première intention — mais ça dépend vraiment de ce que tu vises derrière.
>
> Qu'est-ce qui t'attire le plus quand tu penses à Sciences-Po : le contenu pluridisciplinaire, l'environnement étudiant, les débouchés précis, ou l'image du diplôme ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **23/25** / hallucination **22/25** = **92/100**

**Corrections suggérées par le critique** :
> Précisé que la double licence droit-sciences politiques dépend des universités (pas garantie partout), retiré la date précise du concours commun IEP 'fin avril 2026' (calendrier qui bouge chaque année), et reformulé légèrement pour fluidifier le passage sur les contraintes.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #33 — `A2` iter 12 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `keep` (score **91**, recommandée critique `keep`)
**Latence** : 62.7s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je hésite entre éco-gestion, droit et sciences-po, comment choisir ?

**Question (refined par Phase 4)** :
> Salut, je suis vraiment perdu : entre éco-gestion, droit et Sciences Po / IEP, je n'arrive pas à trancher. Comment je peux y voir plus clair ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu hésites entre trois pistes qui te parlent toutes, et la peur de mal choisir te bloque un peu. C'est une hésitation très saine — ces trois voies accueillent volontiers des profils littéraires-scientifiques comme le tien, mais elles ne mènent pas au même quotidien.
>
> Voici trois pistes à mettre en regard de tes critères (région hors Île-de-France, budget modéré, utilité sociale) :
>
> • **Licence de droit à l'université** — une des filières les plus demandées sur Parcoursup. Coût universitaire classique, débouchés diversifiés (avocat·e, magistrat·e, notaire, juriste d'entreprise, métiers de la fonction publique). Bonne porte pour qui aime l'argumentation, le raisonnement structuré et le service public. La sélectivité varie selon les universités, donc à regarder fac par fac.
>
> • **Licence éco-gestion** — polyvalente, plus quantitative, même cadre universitaire en termes de coût. Débouchés vers l'entreprise, la banque, l'administration économique, ou poursuite en master (finance, marketing, économie publique). Cohérente avec ta spé SES si tu apprécies la dimension chiffrée.
>
> • **Sciences Po / Concours commun IEP** — voie sélective : concours commun aux 7 IEP de région (Lille, Lyon, Rennes, Strasbourg, Aix, Toulouse, Saint-Germain-en-Laye) en fin d'année de terminale, et procédure dossier + oraux pour Sciences Po Paris et ses campus délocalisés. Frais d'inscription au concours à anticiper, mais scolarité publique donc abordable. Cursus pluridisciplinaire (droit, éco, histoire, sciences politiques) qui peut bien convenir à un profil indécis qui aime relier les disciplines.
>
> Une question pour avancer : quand tu te projettes dans cinq ans, tu te verrais plutôt **plaider/conseiller sur des règles** (droit), **analyser des chiffres pour décider** (éco-gestion), ou **comprendre des systèmes complexes pour agir dessus** (IEP) ? Ta réponse spontanée dit souvent plus que dix tableaux comparatifs. Et si tu hésites encore, qu'est-ce qui te freine le plus aujourd'hui — la peur de te fermer des portes, ou de ne pas savoir si tu vas aimer le quotidien ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **22/25** / hallucination **22/25** = **91/100**

**Corrections suggérées par le critique** :
> Retiré la mention 'une trentaine' de débouchés ONISEP (chiffre précis non vérifiable), nuancé la comparaison de sélectivité droit vs éco-gestion (variable selon universités, pas un fait national stable), et précisé que la liste des campus IEP concerne le concours commun (Sciences Po Paris a ses propres campus distincts).

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #34 — `A2` iter 13 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **92**, recommandée critique `keep`)
**Latence** : 48.8s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète ?

**Question (refined par Phase 4)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu hésites entre Sciences Po Paris et un IEP de région, et tu cherches à voir ce qui change vraiment au quotidien — au-delà du prestige sur le papier. C'est une question saine à se poser, surtout avec ton profil SES-HG.
>
> Voici 3 pistes pour démêler ça :
>
> • **Sciences Po Paris** — Admission via Parcoursup avec dossier puis oral, selon un calendrier strict au printemps. À noter : Sciences Po Paris a 7 campus (Paris, Reims, Le Havre, Menton, Nancy, Poitiers, Dijon), chacun avec une spécialité régionale ou thématique — donc tu n'es pas forcément à Paris en première année. Réseau d'anciens dense, ouverture internationale forte, mais coût de vie à anticiper selon le campus.
>
> • **Concours commun des IEP** — Une épreuve écrite mutualisée au printemps pour candidater d'un coup à plusieurs IEP (Aix, Lille, Lyon, Rennes, Strasbourg, Toulouse). Frais d'inscription modérés, sélectivité réelle. Avantage : tu peux viser un ancrage régional plus marqué, avec un coût de vie souvent plus contenu qu'à Paris.
>
> • **Licence universitaire (droit, éco, histoire) en backup** — Si l'IEP ne passe pas, la fac reste une porte d'entrée solide vers les mêmes métiers (droit, administration, journalisme, recherche). Accès plus ouvert, et tu peux retenter un IEP en admission parallèle après L1 ou L2.
>
> Quand tu te projettes dans 3 ans, qu'est-ce qui compte le plus pour toi : le réseau et l'ouverture internationale, un ancrage régional choisi, ou la souplesse d'une voie universitaire qui te laisse le temps d'affiner ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **23/25** / hallucination **22/25** = **92/100**

**Corrections suggérées par le critique** :
> Retiré 'Saint-Germain' (Saint-Germain-en-Laye n'est pas dans le concours commun des 7 IEP — ce sont Aix, Lille, Lyon, Rennes, Strasbourg, Toulouse + Saint-Germain-en-Laye depuis 2021 mais Sciences Po Saint-Germain a quitté le concours commun en 2024). Précisé que Sciences Po Paris a aussi un campus à Reims/Le Havre/Menton/Nancy/Poitiers/Dijon (pas tout à Paris). Adouci la formulation 'province' qui peut sonner cliché.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #35 — `A2` iter 14 (catégorie `lyceen_post_bac`, axe 1, seed_idx 2)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 128.9s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Pour un profil SES-HG, quel master pro paie mieux à 5 ans : droit ou éco ?

**Question (refined par Phase 4)** :
> Pour un profil SES-HG comme le mien, lequel paie mieux à 5 ans : un master pro de droit ou un master pro d'éco/finance ?

**Answer (refined par Phase 4)** :

> Si je te suis bien, tu cherches à comparer le retour salarial entre droit et éco à 5 ans — c'est une question légitime, surtout quand tu vises l'autonomie financière sans filet familial parisien.
>
> Honnêtement, l'écart *à l'intérieur* d'un même master (selon le métier visé, la ville, la spécialisation, le réseau) est souvent plus grand que l'écart moyen droit vs éco. Pour t'aider à y voir plus clair, voici trois pistes à explorer en parallèle :
>
> - **Master pro droit (affaires, fiscalité, droit bancaire)** — voie universitaire, frais publics modérés (cohérent avec un budget contraint). Les débouchés sont très hétérogènes : un fiscaliste en cabinet d'affaires ne se rémunère pas du tout comme un juriste en collectivité ou en association. La licence de droit est une des plus demandées sur Parcoursup, avec une sélection qui se fait surtout sur dossier.
>
> - **Master pro éco/finance/gestion** — soit université publique (frais modérés), soit école de commerce (frais privés bien plus élevés, parfois compensés par alternance). Les débouchés banque/audit/conseil sont souvent décrits comme mieux rémunérés en sortie, mais l'entrée en M1 sélectif filtre pas mal. La licence éco-gestion à l'université est généralement perçue comme plus exigeante en maths que ce que beaucoup imaginent depuis la spé SES.
>
> - **IEP (Sciences Po régional) + master spécialisé** — concours commun des 7 IEP fin avril, sélectivité forte. Profil hybride éco-droit-sciences-po qui ouvre vers conseil, fonction publique, médias, parfois finance. Des doubles diplômes droit–IEP existent dans certaines villes. Ça peut matcher ton goût pour l'utilité sociale combiné à un côté pragmatique.
>
> Plutôt que de courir après un salaire moyen à 5 ans (très volatil selon le poste, le cabinet, la ville — les chiffres APEC ou INSEE par filière donnent des fourchettes mais l'écart individuel reste énorme), une question peut-être plus utile : quel type de quotidien t'attire vraiment — décortiquer des dossiers juridiques, modéliser des chiffres économiques, ou travailler sur des politiques publiques ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré l'affirmation non-sourcée 'licence droit la plus demandée Parcoursup' et 'taux d'accès ~10% IEP' (chiffres précis non sourcés). Reformulé pour rester qualitatif sur la sélectivité. Ajouté une légère reformulation initiale plus chaleureuse et précisé que les ordres de grandeur salariaux dépendent de sources type APEC/INSEE plutôt que d'avancer des tendances sans cadre.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #36 — `A2` iter 15 (catégorie `lyceen_post_bac`, axe 1, seed_idx 3)

**Décision** : `keep` (score **92**, recommandée critique `keep`)
**Latence** : 86.0s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?

**Question (refined par Phase 4)** :
> J'ai 12 de moyenne en terminale SES-HG, j'hésite entre licence droit, éco-gestion et tenter un IEP en région — est-ce que j'ai mes chances quelque part ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un dossier correct sans être en tête de classe, et tu cherches à voir où ce niveau peut t'ouvrir des portes entre trois pistes qui te parlent. C'est une question saine à se poser — ton profil SES-HG est cohérent avec ces trois directions.
>
> Voici trois pistes à comparer :
>
> • Licence de droit à l'université
> Une des filières les plus demandées sur Parcoursup, généralement avec un taux d'accès plus large que l'éco-gestion. Frais modérés (public). Pas de concours d'entrée, mais exigence forte sur la méthode et l'écrit dès le L1. Le questionnaire d'auto-évaluation Parcoursup peut t'aider à voir si la matière te convient vraiment avant de candidater.
>
> • Licence éco-gestion à l'université
> Sélectivité variable selon les universités, parfois plus tendue que le droit dans certaines facs. Frais modérés également (public). Cohérente avec ta spé SES si tu te vois travailler sur l'analyse économique, la gestion ou la finance. Bon tremplin vers un master spécialisé ensuite.
>
> • Concours commun des 7 IEP en région (Aix, Lille, Lyon, Rennes, Saint-Germain-en-Laye, Strasbourg, Toulouse)
> Une épreuve unique au printemps, accessible depuis n'importe quelle académie. Très sélectif mais préparable en autonomie ou via des prépas. Cursus pluridisciplinaire (droit, éco, sciences po, histoire) — potentiellement pertinent vu ton hésitation entre les trois domaines. Frais d'inscription au concours à anticiper, scolarité ensuite raisonnable (public).
>
> Avant de trancher, qu'est-ce qui pèse le plus dans ta réflexion : garder un cursus large pour ne pas te spécialiser trop vite, te concentrer sur une matière qui te parle déjà, ou éviter la pression d'un concours en plus de Parcoursup ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **23/25** / posture **24/25** / cohérence **23/25** / hallucination **22/25** = **92/100**

**Corrections suggérées par le critique** :
> Précisé que le concours commun IEP regroupe 7 IEP avec date variable selon années (avril–mai), retiré la mention 'fin avril 2026' trop précise non sourcée, ajusté la formulation 'plus sélective' pour éco-gestion qui n'est pas systématiquement vrai (variable selon université), reformulé la question finale pour être plus ouverte.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #37 — `A2` iter 16 (catégorie `lyceen_post_bac`, axe 1, seed_idx 4)

**Décision** : `keep` (score **88**, recommandée critique `keep`)
**Latence** : 99.7s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Tremplin/Passerelle pour HEC, c'est quoi exactement et c'est pour qui ?

**Question (refined par Phase 4)** :
> Tremplin/Passerelle pour HEC, c'est quoi exactement et c'est pour qui ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu te demandes ce que recouvrent ces noms de concours et si c'est une voie envisageable pour toi sans passer par la prépa classique.
>
> Tremplin et Passerelle sont deux concours d'admission parallèle aux écoles de commerce : tu intègres l'école après un premier cycle d'études supérieures (BTS, BUT, L2 ou L3) plutôt qu'en post-bac ou après prépa. Ça permet de garder de la flexibilité avant de te spécialiser.
>
> Trois pistes à mettre sur la table :
>
> • **Admission parallèle après BUT/BTS/licence (concours Tremplin ou Passerelle)** : tu fais d'abord un cursus public accessible près de chez toi, puis tu tentes l'écrit du concours en bac+2 ou bac+3. Frais de scolarité élevés une fois dans l'école de commerce (privée), mais tu sécurises d'abord un diplôme intermédiaire utile en cas de bascule.
>
> • **CPGE économique post-bac (filière ECG)** : voie classique vers les grandes écoles de commerce, prépa publique sans frais directs, concours post-prépa ensuite. Exigeant intellectuellement, sélectif sur dossier à l'entrée, rythme intense.
>
> • **Licence éco-gestion à la fac proche de chez toi** : voie publique avec accès Parcoursup généralement plus ouvert. Tu peux bifurquer ensuite vers une admission parallèle, un master spécialisé, ou même rebasculer vers droit/sciences-po si ton intérêt évolue — pratique vu ton hésitation actuelle.
>
> Vu que tu balances entre éco, droit, sciences-po et IEP : qu'est-ce qui t'attire le plus aujourd'hui — la logique chiffres/stratégie d'entreprise du commerce, ou plutôt l'analyse politique et juridique des autres voies ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **23/25** / cohérence **22/25** / hallucination **21/25** = **88/100**

**Corrections suggérées par le critique** :
> Précisé que Tremplin/Passerelle sont les noms officiels des concours d'admission parallèle (Tremplin = ESCP, Passerelle = banque commune type EM Lyon/EDHEC). Retiré 'concours BCE' associé à ECG (BCE existe mais c'est plus large que prépa) pour rester sur 'concours post-prépa'. Adouci 'insertion pro généralement documentée' qui sonnait flou.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #38 — `A2` iter 17 (catégorie `lyceen_post_bac`, axe 1, seed_idx 5)

**Décision** : `keep` (score **91**, recommandée critique `keep`)
**Latence** : 70.6s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Sciences-Po ça vaut le coup ou c'est juste un nom ?

**Question (refined par Phase 4)** :
> Sciences-Po, ça vaut vraiment le coup ou c'est juste pour le prestige du nom ?

**Answer (refined par Phase 4)** :

> Si je te suis bien, tu te demandes si la marque 'Sciences-Po' justifie l'effort, ou si c'est surtout un effet de réputation qui gonfle l'attractivité. C'est une question saine, surtout quand tu hésites entre plusieurs voies sérieuses et que tu cherches l'utilité concrète derrière le nom.
>
> Trois pistes à comparer sur des critères objectifs :
>
> • **Sciences-Po Paris** — formation pluridisciplinaire (éco, droit, sciences sociales, humanités), répartie sur plusieurs campus dont certains hors Paris. Admission via dossier Parcoursup + oraux, sélectif mais public, frais modulés selon les revenus familiaux. Débouchés larges : politiques publiques, droit, médias, international. Cohérent avec un profil SES-HG curieux et multi-domaines.
>
> • **Concours commun des IEP régionaux** (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) — épreuve écrite commune au printemps, profil et débouchés proches de Sciences-Po Paris avec un ancrage régional plus marqué. Coût de vie souvent plus doux hors Île-de-France, ce qui peut compter selon ton cadre budget. Effort de préparation conséquent mais cadré.
>
> • **Licence droit ou éco-gestion en fac publique** — voie plus accessible à l'admission, peu coûteuse, qui te laisse la possibilité de viser un IEP en passerelle master plus tard, ou de bifurquer vers concours, magistrature, juriste d'entreprise. Voie pragmatique si tu préfères ouvrir d'abord, trancher ensuite, en gardant un coût modéré.
>
> Chacune demande un effort différent : marathon de prépa concours pour les IEP, dossier travaillé long pour Sciences-Po, autonomie et rigueur perso pour la fac.
>
> Quand tu te projettes dans 3 ans, qu'est-ce qui compte le plus pour toi : viser haut tout de suite quitte à prendre le risque, ou construire pas à pas avec plusieurs portes ouvertes ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **24/25** / cohérence **23/25** / hallucination **22/25** = **91/100**

**Corrections suggérées par le critique** :
> Retiré la date précise '25 avril 2026' (chiffre non sourcé, risque obsolescence) et 'environ 1 220 places' / 'taux 10%' (chiffres précis non sourcés) au profit de formulations qualitatives. Conservé la structure reformulation + 3 options pondérées + question ouverte finale.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #39 — `A2` iter 18 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 94.3s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je hésite entre éco-gestion, droit et sciences-po, comment choisir ?

**Question (refined par Phase 4)** :
> Je suis en terminale, j'hésite entre éco-gestion, droit et un IEP en région — j'ai du mal à trancher, comment je m'y prends ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un profil solide en SES-HG, tu cherches une voie utile socialement, et tu veux comparer sereinement avant de t'engager. C'est sain de prendre le temps avant de cocher des vœux.
>
> Avant de te donner des pistes, deux questions qui peuvent t'aider à clarifier : qu'est-ce qui te plaît le plus dans tes spés actuelles — l'analyse chiffrée des SES, le raisonnement historique, ou la dimension argumentation/débat ? Et est-ce que tu te projettes plutôt en cursus généraliste pluridisciplinaire ou dans une discipline plus cadrée ?
>
> En attendant, voici trois pistes équilibrées, sans en privilégier une :
>
> • **Licence éco-gestion** : université publique, frais modérés, débouchés larges (entreprise, banque, secteur public, associatif). Bonne porte si tu veux garder de l'optionalité tout en restant proche de chez toi.
>
> • **Licence droit** : formation très demandée chaque année sur Parcoursup, avec une diversité de métiers documentée par l'ONISEP (avocat·e, magistrat·e, juriste d'entreprise, notaire, etc.). Frais modérés en fac publique, mais beaucoup de lecture et de rigueur écrite attendues.
>
> • **IEP de région ou Sciences-Po** : les IEP du réseau commun (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) partagent un concours commun au printemps ; Sciences-Po passe par Parcoursup avec écrits puis oraux. Profils pluridisciplinaires (droit, éco, histoire, sciences po), très orientés secteur public et utilité sociale, mais préparation exigeante — vérifie les dates exactes sur les sites officiels.
>
> À garder en tête côté calendrier : la fenêtre Parcoursup s'étend habituellement de janvier à mars pour les vœux, avec premières réponses début juin — confirme les dates 2026 sur parcoursup.fr.
>
> Pour t'aider à trancher : si tu devais renoncer à une matière demain — droit pur, économie chiffrée, ou sciences politiques transversales — laquelle te manquerait le moins ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **22/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la date précise du concours commun IEP (25 avril 2026) et les dates Parcoursup chiffrées non vérifiables sans source — remplacées par formulations prudentes ('au printemps', 'fenêtre Parcoursup habituelle de janvier à mars'). Retiré 'la formation la plus demandée sur Parcoursup en 2025' (chiffre non sourcé). Conservé la structure reformulation + 3 options pondérées + question finale ouverte.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #40 — `A2` iter 19 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 49.2s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète ?

**Question (refined par Phase 4)** :
> Sciences-Po Paris ou IEP région, quelle différence concrète ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu cherches à voir ce qui distingue vraiment ces deux voies au-delà du prestige affiché — pas juste l'étiquette. C'est une démarche saine, et tu as le temps de creuser tranquillement.
>
> Voici trois angles pour t'aider à comparer concrètement :
>
> • **Le format d'admission n'est pas le même.** Sciences Po Paris recrute via Parcoursup avec un dossier, des écrits déposés en ligne et un oral, sans concours écrit commun. Le Réseau ScPo (Aix, Lille, Lyon, Rennes, Saint-Germain-en-Laye, Strasbourg, Toulouse) organise un concours commun écrit unique en avril ; à noter que d'autres IEP comme Grenoble ou Bordeaux ont leurs propres modalités. Le type d'épreuve qui te met le plus à l'aise (dossier + oral vs écrit massif sur un jour) peut déjà orienter ton choix.
>
> • **Le maillage territorial change ton quotidien.** Sciences Po Paris répartit son cycle bachelor sur 7 campus, dont plusieurs en région (Dijon, Le Havre, Menton, Nancy, Poitiers, Reims) avant un retour possible à Paris en master. Un IEP régional, lui, t'ancre dans une ville étudiante précise pendant les cinq ans — souvent plus abordable côté logement, avec un réseau alumni local marqué.
>
> • **L'offre pédagogique se ressemble plus qu'on ne le pense en bachelor.** Les deux proposent un tronc commun pluridisciplinaire (droit, éco, science politique, histoire, sociologie) qui colle bien à un profil SES-HG. Les vraies différences se jouent en master : spécialisations, doubles diplômes, partenariats internationaux — ça vaut la peine de regarder les maquettes côte à côte plutôt que de raisonner par réputation globale.
>
> Qu'est-ce qui pèse le plus pour toi aujourd'hui : le cadre de vie étudiante, le type d'épreuve où tu te sens le plus en valeur, ou les débouchés master que chaque école ouvre ?

**Sources research (Phase 1 WebSearch, extraits)** :

> URL : https://www.education.gouv.fr/parcoursup-2026-les-candidats-peuvent-consulter-l-offre-de-formation-2026-452019
> Date : Décembre 2025
> Extrait clé : Parcoursup 2026 offre ~25 000 programmes (licences éco/droit/sciences-po), inscriptions 19 janv–12 mars 2026, décisions admission dès 2 juin 2026.
>
> URL : https://concoursiep.com/le-concours-commun-des-iep/
> Date : 2025-2026
> Extrait clé : Concours commun 7 IEP (Aix, Lille, Lyon, Rennes, Saint-Germain, Strasbourg, Toulouse) samedi 25 avril 2026, ~1 220 places, taux d'accès ~10%, frais inscription 210€.
>
> URL : https://www.cidj.com/s-orienter/avec-parcoursup/integrer-sciences-po-concours-dossier-oral-mode-d-emploi-2026
> Date : 2026
> Extrait clé : Sciences-Po 2026 : 1 000 places sur 7 campus, admissions par dossier Parcoursup (19 jan–12 mars) + oraux (mai–31 mai), calendrier strict.
>
> URL : https://www.onisep.fr/metier/decouvrir-le-monde-professionnel/droit-et-justice
> Date : 2025
> Extrait clé : 30 métiers droit/justice documentés (avocate, magistrate, notaire, commissaire police, juriste d'entreprise), formations université (licence+master) ou IEP, plus de la moitié avec témoignages professionnels.
>
> URL : https://www.cidj.com/s-orienter/avec-
>
> [...]

**Critique scores Phase 3** : factuelle **20/25** / posture **24/25** / cohérence **23/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Corrigé la liste du concours commun (Réseau ScPo = Aix, Lille, Lyon, Rennes, Saint-Germain-en-Laye, Strasbourg, Toulouse — 7 IEP, mais Grenoble et Bordeaux ont leur propre concours et ne sont pas dans le commun). Précisé que Sciences Po Paris a 7 campus délocalisés dont 6 en région (Dijon, Le Havre, Menton, Nancy, Poitiers, Reims) + Paris. Retiré l'imprécision sur les frais d'inscription comme spécificité du concours commun. Adouci 'très sélective' qui était un jugement non chiffré.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #41 — `A3` iter 0 (catégorie `lyceen_post_bac`, axe 1, seed_idx 0)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 106.8s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> J'aime les lettres mais tout le monde dit que ça mène à rien, c'est vrai ?

**Question (refined par Phase 4)** :
> J'adore les lettres mais autour de moi on me répète que ça ne mène à rien, est-ce que c'est vrai ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu portes une vraie passion pour l'écriture et la littérature, mais les remarques autour de toi te font douter. C'est normal d'hésiter quand on entend ce discours en boucle, et c'est plutôt sain de venir vérifier par toi-même. Regardons ensemble ce que disent les sources officielles, parce que la réalité est bien plus nuancée que le « ça mène à rien ».
>
> • **Licence Lettres classique (université publique)** : frais très accessibles, compatible avec un budget contraint et une bourse possible selon ta situation familiale. D'après l'ONISEP, elle ouvre vers l'enseignement, la communication, le journalisme, l'édition, la culture. L'insertion se construit surtout après un master, c'est donc un parcours qui demande de se projeter sur le temps long.
>
> • **Licences professionnelles ou parcours « Métiers du livre / Information-Communication »** : même cadre universitaire public, mais avec une coloration métiers concrets dès la licence (rédaction web, communication éditoriale, documentation, médiation culturelle). Plus directement professionnalisante si tu veux voir des débouchés sans attendre Bac+5.
>
> • **Lettres + double compétence (langues, droit, info-com, sciences politiques via bi-licence ou mineure)** : tu gardes ta passion comme socle et tu ajoutes une corde qui élargit l'éventail. Les profils littéraires polyvalents restent recherchés en communication, édition, presse, RH, mais les chiffres précis dépendent de l'établissement et de la spécialité, à vérifier sur les fiches ONISEP du diplôme visé.
>
> Avant de trancher, qu'est-ce qui te parlerait le plus : explorer en profondeur ce que tu aimes en gardant plusieurs portes ouvertes, ou avoir le plus tôt possible un métier identifié au bout du parcours ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-licences-de-lettres-et-de-langues/la-licence-lettres
>   Date : 2026
>   Extrait clé : Débouchés en administration, enseignement, communication, journalisme, édition, culture. Insertion généralement après master (Bac + 5). Concours professeurs possible après L3.
>
> - URL : https://u-paris.fr/lac/licence-lettres-edition-et-metiers-de-l-ecrit/
>   Date : 2025-2026
>   Extrait clé : Licence LEME (Lettres, Édition, Métiers de l'Écrit) ouvre vers bibliothécaire, documentaliste, rédacteur web, journaliste, attaché de presse, chargé de communication.
>
> - URL : https://data.enseignementsup-recherche.gouv.fr/pages/insertion_professionnelle/
>   Date : Février 2026 (données 2024)
>   Extrait clé : Taux emploi 12 mois Lettres-Langues-Arts : 66,6% (60,9% salariés + 5,7% non-salariés). Données officielles InserSup.
>
> - URL : https://www.cned.fr/l-actualite-de-la-formation/blog-lycee/terminales-2025-2026-preparez-votre-orientation-post-bac
>   Date : 2025-2026
>   Extrait clé : Études lettres débouchent enseignement, communication, social, RH, médiation culturelle. Master requis pour insertion opérationnelle.
>
> - URL : https://candidat.
>
> [...]

**Critique scores Phase 3** : factuelle **22/25** / posture **22/25** / cohérence **23/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Remplacé 'Licence LEME' (acronyme non standardisé risquant l'hallucination) par formulation générique 'licences pro Métiers du livre / Information-Communication'. Retiré 'InserSup' et 'France Travail' nommés comme sources de chiffres précis (aucun chiffre cité, donc référence inutile et risquée). Adouci ton avec un tutoiement plus chaleureux conforme persona 17 ans.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #42 — `A3` iter 1 (catégorie `lyceen_post_bac`, axe 1, seed_idx 1)

**Décision** : `keep` (score **86**, recommandée critique `flag`)
**Latence** : 74.9s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quels métiers vraiment accessibles avec une licence de lettres modernes ?

**Question (refined par Phase 4)** :
> Avec une licence de lettres modernes, quels métiers sont vraiment atteignables sans finir au chômage ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu adores les lettres mais tu sens cette pression autour de toi qui te dit "ça ne mène à rien" — et c'est lourd à porter quand tu fais déjà ce choix avec ta spé. Cette peur est très partagée, et il existe vraiment des parcours qui débouchent, surtout une fois le master posé.
>
> Voici trois pistes que tu peux explorer sans te fermer de portes :
>
> • **Licence Lettres modernes → master MEEF (enseignement)** : voie universitaire publique, frais contenus, compatible bourse. Mène aux concours de l'enseignement (CAPES de lettres, agrégation) qui se passent généralement en M1/M2. Bien implantée partout en France, pas seulement en Île-de-France.
>
> • **Licence Lettres avec parcours métiers de l'écrit ou édition** (intitulés variables selon les universités) : ouvre vers l'édition, la rédaction web, le secteur de la presse, les métiers des bibliothèques et de la documentation. Cursus universitaire donc coût bas, et la communication/édition reste un secteur où l'écrit de qualité a sa place.
>
> • **Licence Lettres + master en communication, journalisme ou médiation culturelle** : tu gardes ta passion littéraire et tu ajoutes une corde plus concrète côté débouchés. Selon les fiches ONISEP, ces parcours mènent vers la com', les RH, le social, la médiation culturelle ou le journalisme — avec un master qui solidifie l'insertion.
>
> Une chose à garder en tête : en lettres, c'est souvent le bac+5 qui change vraiment la donne côté emploi. La licence seule ouvre des portes, le master les stabilise.
>
> Question pour avancer : entre *transmettre* (enseigner), *créer et écrire* (édition, presse, web) et *accompagner* (médiation, culture, social), laquelle de ces trois sensibilités te parle le plus aujourd'hui ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-licences-de-lettres-et-de-langues/la-licence-lettres
>   Date : 2026
>   Extrait clé : Débouchés en administration, enseignement, communication, journalisme, édition, culture. Insertion généralement après master (Bac + 5). Concours professeurs possible après L3.
>
> - URL : https://u-paris.fr/lac/licence-lettres-edition-et-metiers-de-l-ecrit/
>   Date : 2025-2026
>   Extrait clé : Licence LEME (Lettres, Édition, Métiers de l'Écrit) ouvre vers bibliothécaire, documentaliste, rédacteur web, journaliste, attaché de presse, chargé de communication.
>
> - URL : https://data.enseignementsup-recherche.gouv.fr/pages/insertion_professionnelle/
>   Date : Février 2026 (données 2024)
>   Extrait clé : Taux emploi 12 mois Lettres-Langues-Arts : 66,6% (60,9% salariés + 5,7% non-salariés). Données officielles InserSup.
>
> - URL : https://www.cned.fr/l-actualite-de-la-formation/blog-lycee/terminales-2025-2026-preparez-votre-orientation-post-bac
>   Date : 2025-2026
>   Extrait clé : Études lettres débouchent enseignement, communication, social, RH, médiation culturelle. Master requis pour insertion opérationnelle.
>
> - URL : https://candidat.
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la mention 'LEME' (sigle non standard non vérifiable) et l'affirmation 'CAPES accessible dès la L3' (imprécise — l'inscription est possible en M1 sous conditions, pas la titularisation). Retiré 'France Travail repère les secteurs en tension' (formulation trop affirmative sans source précise). Adouci les attributions de sources pour rester prudent.

_Décision recommandée par critique : `flag` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #43 — `A3` iter 2 (catégorie `lyceen_post_bac`, axe 1, seed_idx 2)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 87.6s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Master édition / journalisme / communication : lequel a le meilleur taux d'embauche ?

**Question (refined par Phase 4)** :
> Entre les masters édition, journalisme et communication, sur lequel j'ai le plus de chances de trouver un emploi rapidement après le bac+5 ?

**Answer (refined par Phase 4)** :

> Je comprends ce que tu cherches : tu adores les lettres, et en même temps tu veux choisir un master qui t'ouvrira concrètement des portes après le bac+5. C'est une question vraiment saine à se poser dès la terminale, et plutôt rare — beaucoup attendent la fin de la licence pour y penser.
>
> Voici comment se positionnent les trois pistes, en restant honnête sur ce qu'on peut dire et ne pas dire :
>
> • **Master communication** : c'est le secteur avec le plus large éventail de débouchés (chargé de com, attaché de presse, communication interne ou externe, com digitale). L'insertion est plutôt accessible mais la concurrence à l'entrée est forte, et beaucoup de postes démarrent en alternance ou stage long.
>
> • **Master édition / métiers du livre** : voie privilégiée si tu veux rester proche du livre, du texte, de la chaîne éditoriale (assistant d'édition, correcteur, rédacteur web, métiers documentaires). Le cœur de marché est plus restreint que la com, mais l'adéquation avec une passion littéraire est forte.
>
> • **Master journalisme** : débouchés réels (presse écrite, web, audiovisuel), mais accès souvent via écoles reconnues sélectives, et la précarité en début de carrière est fréquente (piges, CDD courts) avant de se stabiliser.
>
> Au-delà des grandes tendances sectorielles, ce qui fait vraiment la différence sur ces trois masters, c'est la qualité des stages, les expériences éditoriales menées pendant ta licence (revue étudiante, blog, fanzine, podcast, newsletter) et le portfolio que tu te constitues. Les trois mènent à l'emploi quand le projet est construit en amont.
>
> Une question pour t'aider à trancher : quand tu te projettes dans ton quotidien pro dans cinq ans, tu te vois plus écrire pour **informer** (journalisme), pour **porter une idée, une marque ou un message** (communication), ou pour **accompagner et faire exister les œuvres des autres** (édition) ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-licences-de-lettres-et-de-langues/la-licence-lettres
>   Date : 2026
>   Extrait clé : Débouchés en administration, enseignement, communication, journalisme, édition, culture. Insertion généralement après master (Bac + 5). Concours professeurs possible après L3.
>
> - URL : https://u-paris.fr/lac/licence-lettres-edition-et-metiers-de-l-ecrit/
>   Date : 2025-2026
>   Extrait clé : Licence LEME (Lettres, Édition, Métiers de l'Écrit) ouvre vers bibliothécaire, documentaliste, rédacteur web, journaliste, attaché de presse, chargé de communication.
>
> - URL : https://data.enseignementsup-recherche.gouv.fr/pages/insertion_professionnelle/
>   Date : Février 2026 (données 2024)
>   Extrait clé : Taux emploi 12 mois Lettres-Langues-Arts : 66,6% (60,9% salariés + 5,7% non-salariés). Données officielles InserSup.
>
> - URL : https://www.cned.fr/l-actualite-de-la-formation/blog-lycee/terminales-2025-2026-preparez-votre-orientation-post-bac
>   Date : 2025-2026
>   Extrait clé : Études lettres débouchent enseignement, communication, social, RH, médiation culturelle. Master requis pour insertion opérationnelle.
>
> - URL : https://candidat.
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **22/25** / cohérence **23/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la mention 'France Travail' présentée comme source pour com et édition (claim non vérifiable précisément, risque hallucination). Reformulé en termes plus prudents ('plutôt accessible', 'marché plus restreint'). Adouci légèrement le ton vers tutoiement_doux avec un peu plus de chaleur en ouverture.

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #44 — `A3` iter 3 (catégorie `lyceen_post_bac`, axe 1, seed_idx 3)

**Décision** : `keep` (score **86**, recommandée critique `keep`)
**Latence** : 50.5s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Tout le monde dit que les lettres ça mène à rien, j'commence à m'inquiéter pour de vrai

**Question (refined par Phase 4)** :
> Tout le monde dit que les lettres ça mène à rien, j'commence à m'inquiéter pour de vrai

**Answer (refined par Phase 4)** :

> Si je t'entends bien, tu aimes écrire et la littérature, mais la pression autour de toi te fait douter de la suite — c'est une inquiétude vraiment légitime, et tu n'es pas seul·e à la ressentir.
>
> Déjà, une vérité utile à poser : les lettres ne mènent pas « à rien ». Les filières littéraires ouvrent vers l'enseignement, la communication, l'édition, le journalisme, la médiation culturelle, les ressources humaines, le travail social. La nuance honnête : l'insertion solide se joue souvent après un master (Bac+5), pas dès la fin de licence — c'est important de le savoir pour anticiper.
>
> Voici 3 pistes à explorer, sans hiérarchie :
>
> • **Licence Lettres classique en fac publique près de chez toi** — coût très accessible (compatible bourse selon ta situation), large socle littéraire, te laisse le temps de préciser ton projet en L2/L3. Débouchés via master : enseignement (CAPES/agrégation préparés après le master), recherche, culture.
>
> • **Licences pro orientées Édition / Métiers du livre / Métiers de l'écrit** — plus pro dès la licence, ouvrent vers bibliothèque, documentation, rédaction web, communication éditoriale. Plusieurs universités en proposent : à regarder sur Parcoursup avec le filtre « édition » ou « métiers du livre » dans ta région.
>
> • **Lettres + double cursus ou mineure (info-com, langues, droit, sciences sociales)** — tu gardes ta passion mais tu élargis les débouchés. Plusieurs facs proposent ces doubles parcours, y compris hors Île-de-France à coût public.
>
> Un outil pour creuser concrètement : **MétierScope** (France Travail) te laisse explorer les métiers par compétences (rédiger, analyser, conseiller, transmettre) — utile pour mettre des visages concrets sur « les lettres » au lieu d'un mot abstrait.
>
> Dis-moi : qu'est-ce qui te fait vibrer le plus dans l'écriture — créer tes propres textes, transmettre, analyser des œuvres, ou raconter le monde des autres ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-licences-de-lettres-et-de-langues/la-licence-lettres
>   Date : 2026
>   Extrait clé : Débouchés en administration, enseignement, communication, journalisme, édition, culture. Insertion généralement après master (Bac + 5). Concours professeurs possible après L3.
>
> - URL : https://u-paris.fr/lac/licence-lettres-edition-et-metiers-de-l-ecrit/
>   Date : 2025-2026
>   Extrait clé : Licence LEME (Lettres, Édition, Métiers de l'Écrit) ouvre vers bibliothécaire, documentaliste, rédacteur web, journaliste, attaché de presse, chargé de communication.
>
> - URL : https://data.enseignementsup-recherche.gouv.fr/pages/insertion_professionnelle/
>   Date : Février 2026 (données 2024)
>   Extrait clé : Taux emploi 12 mois Lettres-Langues-Arts : 66,6% (60,9% salariés + 5,7% non-salariés). Données officielles InserSup.
>
> - URL : https://www.cned.fr/l-actualite-de-la-formation/blog-lycee/terminales-2025-2026-preparez-votre-orientation-post-bac
>   Date : 2025-2026
>   Extrait clé : Études lettres débouchent enseignement, communication, social, RH, médiation culturelle. Master requis pour insertion opérationnelle.
>
> - URL : https://candidat.
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections suggérées par le critique** :
> Retiré la mention spécifique 'LEME, Université Paris Cité' (slug formation non vérifié) au profit d'une formulation générique 'licences pro Édition / Métiers du livre'. Atténué l'affirmation 'Selon l'Onisep et le CNED' (attribution non sourçable précisément) en formulation plus prudente. Ajouté une nuance sur le concours d'enseignement (CAPES/agrégation après master, pas L3).

_Décision recommandée par critique : `keep` — décision finale : `keep` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Q&A #45 — `A3` iter 4 (catégorie `lyceen_post_bac`, axe 1, seed_idx 4)

**Décision** : `flag` (score **84**, recommandée critique `flag`)
**Latence** : 74.4s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Lettres modernes vs LLCER, c'est quoi la différence concrète ?

**Question (refined par Phase 4)** :
> Lettres modernes vs LLCER, c'est quoi la différence concrète ?

**Answer (refined par Phase 4)** :

> Si j'entends bien ta question, tu hésites entre deux licences proches dans l'univers des lettres, et tu te demandes laquelle ouvre le plus de portes concrètes — c'est une interrogation hyper saine à se poser en terminale.
>
> Avant de te projeter, dis-moi : qu'est-ce qui t'attire le plus aujourd'hui — la langue française et son histoire littéraire, ou plutôt l'idée d'explorer une langue étrangère en profondeur (anglais, espagnol, italien, etc.) ? Ça change pas mal la donne.
>
> Voici trois pistes à mettre en balance :
>
> • **Lettres modernes** : cœur littérature française, linguistique, stylistique, écriture. Les débouchés documentés par l'ONISEP couvrent l'enseignement (concours dès la L3 envisageables), l'édition, la communication, le journalisme, les métiers de la culture. Frais réduits en fac publique, bourse possible selon ton dossier social. À retenir : l'insertion solide se construit souvent via un master ciblé.
>
> • **LLCER** (Langues, Littératures, Civilisations Étrangères et Régionales) : tu gardes une dimension littéraire forte, mais centrée sur une langue étrangère (à choisir au moment de la candidature). Ouvre vers la traduction, la médiation culturelle, l'enseignement de langue, la communication multilingue. Même logique de coût qu'en fac publique. Atout : la double compétence langue + littérature est appréciée à l'international.
>
> • **Licences orientées métiers de l'écrit** (type lettres appliquées, édition, communication écrite — il en existe plusieurs en France, à repérer dans ta région via Parcoursup) : plus appliqué dès la L1. Vise des métiers comme rédacteur web, assistant d'édition, documentaliste, chargé de communication. Pertinent si tu préfères entrer dans la vie active rapidement plutôt que t'engager dans un parcours master long.
>
> À méditer : quand tu te projettes dans cinq ans, qu'est-ce qui te ferait le plus vibrer — transmettre et enseigner, écrire/éditer pour un public, ou faire vivre une langue étrangère au quotidien ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-licences-de-lettres-et-de-langues/la-licence-lettres
>   Date : 2026
>   Extrait clé : Débouchés en administration, enseignement, communication, journalisme, édition, culture. Insertion généralement après master (Bac + 5). Concours professeurs possible après L3.
>
> - URL : https://u-paris.fr/lac/licence-lettres-edition-et-metiers-de-l-ecrit/
>   Date : 2025-2026
>   Extrait clé : Licence LEME (Lettres, Édition, Métiers de l'Écrit) ouvre vers bibliothécaire, documentaliste, rédacteur web, journaliste, attaché de presse, chargé de communication.
>
> - URL : https://data.enseignementsup-recherche.gouv.fr/pages/insertion_professionnelle/
>   Date : Février 2026 (données 2024)
>   Extrait clé : Taux emploi 12 mois Lettres-Langues-Arts : 66,6% (60,9% salariés + 5,7% non-salariés). Données officielles InserSup.
>
> - URL : https://www.cned.fr/l-actualite-de-la-formation/blog-lycee/terminales-2025-2026-preparez-votre-orientation-post-bac
>   Date : 2025-2026
>   Extrait clé : Études lettres débouchent enseignement, communication, social, RH, médiation culturelle. Master requis pour insertion opérationnelle.
>
> - URL : https://candidat.
>
> [...]

**Critique scores Phase 3** : factuelle **21/25** / posture **22/25** / cohérence **22/25** / hallucination **19/25** = **84/100**

**Corrections suggérées par le critique** :
> Retiré la mention spécifique 'LEME — Université Paris Cité' (slug formation précis non vérifiable côté sources officielles dans le draft) au profit d'une formulation générique 'licences pro/appliquées métiers de l'écrit'. Adouci le 'bourse probable vu ton profil' qui présume du dossier social. Reformulé la reformulation initiale pour éviter de poser une émotion ('tu paniques') que l'élève n'a pas explicitement formulée.

_Décision recommandée par critique : `flag` — décision finale : `flag` (boundaries : score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`)_

---

## Synthèse review humaine

### Distribution par catégorie + décision

| Catégorie | keep | flag | total |
|---|---|---|---|
| `lyceen_post_bac` | 36 | 9 | 45 |

### Distribution par prompt_id

| prompt_id | n Q&A keep+flag | seeds disponibles |
|---|---|---|
| `A1` | 20 | 6 |
| `A2` | 20 | 6 |
| `A3` | 5 | 5 |

### Score moyen par axe critique (45 Q&A)

| Axe | Moyenne /25 | Min | Max | Médiane |
|---|---|---|---|---|
| `hallucination` | **19.7** | 15 | 22 | 20.0 |
| `factuelle` | **21.5** | 18 | 23 | 22.0 |
| `coherence` | **22.3** | 21 | 24 | 22.0 |
| `posture` | **23.0** | 21 | 24 | 23.0 |

_Axe le plus faible : `hallucination` — focus prioritaire pour la review humaine._

### Couverture catégorielle nuit 1

Le pipeline a brûlé le quota avant d'attaquer les catégories suivantes.
La nuit 1 ne couvre que **1 catégorie sur 7** prévues au YAML 51 prompts :

- ✅ `lyceen_post_bac` : couvert (45/600 jobs prévus = 7.5%)
- ❌ `etudiant_reorientation` : non-couvert (à relancer nuit 2 post-fix)
- ❌ `actif_jeune` : non-couvert (à relancer nuit 2 post-fix)
- ❌ `master_debouches` : non-couvert (à relancer nuit 2 post-fix)
- ❌ `famille_social` : non-couvert (à relancer nuit 2 post-fix)
- ❌ `meta_question` : non-couvert (à relancer nuit 2 post-fix)
- ❌ `profil_non_cadre` : non-couvert (à relancer nuit 2 post-fix)

### Cas limites instructifs (les 9 flags)

Les Q&A flaggées (score 70-84) sont les plus instructives pour calibrer le prompt v3.2 / la pipeline 4 phases. Triées par score croissant :

| # | prompt_id | iter | score | axe le plus bas | sample |
|---|---|---|---|---|---|
| 1 | `A1` | 2 | **78** | `hallucination` (16/25) | Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ? |
| 2 | `A1` | 8 | **78** | `hallucination` (15/25) | Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ? |
| 3 | `A1` | 14 | **78** | `hallucination` (16/25) | Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ? |
| 4 | `A1` | 17 | **78** | `hallucination` (17/25) | Bon en code mais CS classique me lasse, y'a quoi d'autre comme voies ? |
| 5 | `A1` | 0 | **84** | `hallucination` (18/25) | Je suis en terminale spé maths-physique mais je sature des maths abstraites, alt… |
| 6 | `A1` | 3 | **84** | `hallucination` (19/25) | Quelles sont les meilleures formations en cybersécurité en France ? |
| 7 | `A1` | 15 | **84** | `hallucination` (18/25) | Quelles sont les meilleures formations en cybersécurité en France ? |
| 8 | `A2` | 0 | **84** | `hallucination` (19/25) | Je hésite entre éco-gestion, droit et sciences-po, comment choisir ? |
| 9 | `A3` | 4 | **84** | `hallucination` (19/25) | Lettres modernes vs LLCER, c'est quoi la différence concrète ? |

### Recommandations sample humain

1. **Focus axe `hallucination`** (score moyen le plus bas) — vérifier chaque chiffre cité, chaque URL référencée, chaque nom propre formation/école.
2. **Comparer keep score 85 vs 89** — y a-t-il une vraie différence qualitative entre la borne basse keep et le haut du panier ?
3. **Comparer flag 70 vs 84** — la frontière 84/85 est-elle bien calibrée ? Faut-il décaler boundary keep à 87 ou 90 ?
4. **Couvrir au moins 1 cas par seed_idx unique** dans A1, A2, A3 — vérifier que le pipeline ne fait pas de bias seed (toujours mêmes patterns de réponse selon le seed).
5. **Cross-check les 9 flags en priorité** — décider si keep (remontée frontière) / drop (mauvaise qualité réelle) / re-run (possibilité bug isolé non-stop-condition).

---

*Doc généré par `scripts/extract_nuit1_samples_md.py` sous l'ordre `2026-04-29-0656-claudette-orientia-validation-extract-nuit1`. Format v3 référence : `docs/sprint9-data-dryrun-samples-2026-04-28.md` (commit `6cc9492`).*