# Dry-run Q&A samples — Sprint 9-data 2026-04-28

**Date génération** : 2026-04-28 ~13:48 UTC  
**Pipeline** : 4 phases agentic (research WebSearch → draft → critique 4 axes → refine)  
**Modèle** : `claude-opus-4-7` via subprocess `claude --print`  
**Config** : `--filter-prompt-id A1 --max-iterations 5 --parallel 2 --rate-limit-delay 1.0`  
**Total elapsed** : 8.2 min, 20 sub-agent calls, 0 erreurs, 0 × 429  
**Source** : `data/golden_qa/dryrun_test.jsonl` (commit `028a062`)

---

## Stats globales

| # | Iter | Score | Décision | Latence |
|---|------|-------|----------|---------|
| 1 | 0 | **86** | `keep` | 183.4s |
| 2 | 1 | **89** | `keep` | 165.3s |
| 3 | 2 | **82** | `flag` | 154.8s |
| 4 | 3 | **86** | `keep` | 161.2s |
| 5 | 4 | **78** | `flag` | 174.7s |

**Récap** : 3 keep + 2 flag + 0 drop  |  score moyen **84.2**

**Profil cible A1** : 17 ans, terminale spé maths-physique, profil scientifique solide pas attiré par prépa MPSI / CS pure. Cherche alternatives concrètes (BUT, écoles ingé post-bac, bachelors, formations hybrides).

**Tone attendu** : tutoiement (proximité coach lycéen 17 ans).

---

## Q&A #1 — A1 iter 0 (score **86**, decision `keep`, latence 183.4s)

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique, j'ai des bons résultats mais je sature des maths super abstraites style démonstrations à rallonge. La prépa MPSI me fait flipper. Tu vois des alternatives concrètes pour rester sur du scientifique sans tomber dans le théorique pur ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un vrai profil scientifique solide, mais ce qui t'attire c'est l'application concrète plutôt que la démonstration pour la démonstration — et la MPSI te semble pousser le curseur trop loin côté abstraction. C'est une lucidité plutôt saine, beaucoup de profils comme le tien s'épanouissent davantage ailleurs qu'en prépa classique.
>
> Voici trois pistes que tu pourrais explorer, à pondérer selon ce qui résonne le plus avec toi :
>
> **Piste 1 — BUT (Bachelor Universitaire de Technologie), 3 ans en IUT.** Plusieurs spécialités sont très alignées avec ton profil maths-physique : Génie Mécanique et Productique, Mesures Physiques, Génie Électrique et Informatique Industrielle, Réseaux & Télécoms, Informatique (liste complète à vérifier sur onisep.fr). Le format est très concret : projets, stages dès la 1re année, alternance possible en 2e/3e année. Frais universitaires modérés (consulter parcoursup.fr pour les montants à jour). Sélectivité : modérée à forte selon les IUT. Débouchés : insertion directe à bac+3 ou poursuite en école d'ingé via admissions parallèles (voie royale et sous-cotée).
>
> **Piste 2 — Écoles d'ingénieurs post-bac avec prépa intégrée, 5 ans.** Tu accèdes via deux gros concours sur Parcoursup : Geipi Polytech (réseau Polytech + ENI, épreuves maths + au choix physique-chimie / SI / info / SVT) ou Puissance Alpha (regroupant des écoles type EFREI, ESIEA, ESEO, ECE). Tu as les premières années qui font office de prépa mais avec des projets, des labos, et un recrutement post-bac qui retire la pression du concours d'admission en école. Côté coût, c'est très variable selon le statut (public type Polytech vs privé associatif) — à comparer école par école sur leurs sites et sur Parcoursup. Sélectivité : sur dossier + écrits. Débouché : titre d'ingénieur reconnu CTI.
>
> **Piste 3 — Licences sciences avec passerelles, ou formations hybrides spécialisées.** Si tu veux garder une porte ouverte académique, une L1 maths-info ou physique permet la passerelle vers une école d'ingé en L2/L3 via admissions parallèles. Sinon, sur des hybridations très concrètes (bio-info, finance quant, jeu vidéo, robotique), regarde aussi les bachelors spécialisés et les titres RNCP enregistrés par l'État — par exemple sur le jeu vidéo, plusieurs cursus combinent programmation, game design et production (à filtrer sur france-competences.fr pour vérifier le niveau et le contenu exact). Coût : licence universitaire faible, bachelors privés sensiblement plus chers (consulter directement les établissements). Sélectivité : variable. Débouché : selon spécialisation.
>
> Pour creuser sérieusement, les deux références à garder sous le coude sont onisep.fr (fiches formations et métiers) et parcoursup.fr (formations exactes, attendus, frais).
>
> Une question pour t'aider à trier : entre ces trois pistes, qu'est-ce qui te bloque le plus aujourd'hui — la durée des études, la dimension théorique vs pratique, ou la lisibilité du débouché métier à la sortie ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/apres-le-bac-les-etudes-superieures/quelles-etudes-apres-le-bac
> - Date : page rentrée 2025-2026 (consultée 28/04/2026)
> - Extrait clé : Panorama officiel ONISEP des poursuites post-bac scientifiques hors prépa MPSI : BUT (3 ans, 24 spécialités), écoles d'ingénieurs post-bac avec prépa intégrée (5 ans), licences sciences avec passerelles, bachelors universitaires technologiques.
>
> - URL : https://www.onisep.fr/formation/apres-le-bac-les-etudes-superieures/les-principales-filieres-d-etudes-superieures/les-cpge-classes-preparatoires-aux-grandes-ecoles/les-prepas-scientifiques/la-prepa-pcsi-physique-chimie-et-sciences-de-l-ingenieur
> - Date : page rentrée 2025-2026
> - Extrait clé : "Les écoles d'ingénieurs post-bac recrutent sur dossier ou concours après le ...

**Critique scores Phase 3** : factuelle **21/25** / posture **24/25** / cohérence **23/25** / hallucination **18/25** = **86/100**

**Corrections suggérées par le critique** :
> Les chiffres précis (24 spécialités BUT, 35 écoles Geipi, 17 Puissance Alpha, fourchettes coûts) sont annoncés 'estimation connaissance générale' mais restent risqués sans source — préférer formulations qualitatives ou renvoyer à onisep.fr/parcoursup.fr. Le RNCP 'Concepteur et développeur de jeux vidéo' avec ses 4 blocs est trop spécifique pour être cité sans vérif slug. Sinon posture pondérée, reformulation et question de relance impeccables.

_Décision recommandée par critique : `keep` (vs décision finale `keep` selon score boundary keep≥85 / flag 70-85 / drop<70)_

---

## Q&A #2 — A1 iter 1 (score **89**, decision `keep`, latence 165.3s)

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?

**Question (refined par Phase 4)** :
> Concrètement, est-ce que ça vaut vraiment le coup de tenter une école d'ingénieur post-bac plutôt qu'une prépa MPSI ? J'ai un bon niveau en maths-physique mais la prépa me fait pas rêver, j'ai peur de perdre 2 ans dans un truc trop théorique alors que je veux du concret, voire de l'hybridation genre bio-info ou jeu vidéo.

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as les capacités pour la prépa mais tu cherches une voie qui te mette les mains dans le cambouis plus tôt, avec une vraie ouverture sur des domaines hybrides — pas juste "ingénieur généraliste classique". C'est une réflexion saine, et tu n'es pas seul·e dans ce cas : beaucoup de profils scientifiques solides choisissent aujourd'hui des trajectoires alternatives à MPSI sans rien sacrifier sur le niveau. Voici trois pistes contrastées à mettre en balance.
>
> **Piste 1 — Écoles d'ingé post-bac en 5 ans (INSA, UTC/UTT/UTBM, INP, Polytech, ENI, etc.)** : tu entres directement après le bac sur dossier + parfois entretien (sélectives sur Parcoursup, source officielle Parcoursup 2026). Durée 5 ans, diplôme d'ingénieur reconnu CTI à la sortie, frais de scolarité modérés en public — généralement de quelques centaines à ~2000€/an selon l'école et le statut, avec bourses CROUS possibles (estimation à vérifier sur le site officiel de chaque école, les montants varient). L'avantage par rapport à la prépa : tu attaques les projets, le code, les TP labos dès la 1ère année, avec un cycle préparatoire intégré moins compétitif que MPSI. L'inconvénient : tu t'engages plus tôt sur une école précise, donc le choix initial pèse plus.
>
> **Piste 2 — BUT (Bachelor Universitaire de Technologie) en 3 ans en IUT** : 24 mentions différentes, grade licence, possible en apprentissage dans plein d'IUT (source ONISEP 2025-2026). C'est l'option la plus concrète et la moins risquée financièrement — tu peux viser informatique, mesures physiques, génie bio, génie industriel. À la sortie tu peux soit bosser, soit poursuivre en école d'ingé en admission parallèle (beaucoup d'écoles recrutent des BUT en 3ème année), soit en master. Très bonne porte d'entrée si tu veux tester le "concret" sans fermer la porte à un diplôme d'ingé plus tard.
>
> **Piste 3 — Formations hybrides spécialisées (bachelors thématiques, plusieurs intitulés RNCP existants autour des métiers du jeu vidéo — game design, dev, production —, doubles cursus bio-info, cursus type CPES qui sélectionne sur dossier d'excellence avec critères mixtes dont les ressources mais pas exclusivement)** : tu trouves aujourd'hui des formations reconnues État (titres RNCP, source France Compétences) qui marient deux mondes — game design + dev, biologie + data science, finance + maths appliquées. Plus niche, sélectivité variable, débouchés très liés à la qualité du réseau de la formation et aux stages. Important : il n'existe pas un diplôme unique "jeu vidéo RNCP" mais plusieurs intitulés différents selon les établissements, donc à creuser au cas par cas. La marque "école d'ingé CTI" reste plus universellement lisible par les recruteurs, c'est un fait à pondérer (estimation, connaissance générale).
>
> Une question pour t'aider à trancher : quand tu t'imagines dans 3 ans, est-ce que tu te vois plutôt déjà en stage/alternance dans une boîte sur un projet concret (→ BUT ou bachelor hybride), ou en train de bosser sur des projets longs et de la R&D dans un cadre école avec un diplôme "ingé" en ligne de mire (→ post-bac 5 ans) ? Ta réponse intuitive à ça en dit beaucoup sur ce qui te conviendrait vraiment.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/apres-le-bac-les-etudes-superieures/les-principales-filieres-d-etudes-superieures
> - Date : 2025-2026 (guide rentrée 2026)
> - Extrait clé : ONISEP recense BTS, BUT (24 mentions, 3 ans, possible en apprentissage), licences, CPGE, écoles d'ingé post-bac, écoles de commerce, CPES (cursus d'excellence 3 ans alternatif à la prépa pour bacheliers boursiers visant ingé/art/CPGE).
>
> - URL : https://www.onisep.fr/formation/apres-le-bac-les-etudes-superieures/les-principales-filieres-d-etudes-superieures/les-but-bachelors-universitaires-de-technologie
> - Date : 2025-2026
> - Extrait clé : Le BUT se prépare en 3 ans en IUT, donne grade licence, 24 mentions avec parcours spécialisés, accessible en apprentissage dans certains IUT — alternative directe à la prépa pour p...

**Critique scores Phase 3** : factuelle **22/25** / posture **24/25** / cohérence **23/25** / hallucination **20/25** = **89/100**

**Corrections suggérées par le critique** :
> La mention 'CPES si tu es boursier·e' est imprécise (CPES n'est pas réservé aux boursiers, c'est un critère parmi d'autres). 'Licence pro Métiers du jeu vidéo RNCP' est vague — préciser qu'il existe plusieurs intitulés RNCP plutôt que sous-entendre un diplôme unique. Les fourchettes de coût (quelques centaines à ~2000€/an) gagneraient à citer une source précise ou être marquées 'estimation'.

_Décision recommandée par critique : `keep` (vs décision finale `keep` selon score boundary keep≥85 / flag 70-85 / drop<70)_

---

## Q&A #3 — A1 iter 2 (score **82**, decision `flag`, latence 154.8s)

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?

**Question (refined par Phase 4)** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises pour un profil maths-physique qui ne veut pas de MPSI ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un socle scientifique solide mais la prépa classique ne te parle pas, et tu cherches des voies qui marient le code, le concret et un domaine d'application qui te passionne (vivant, finance, jeu). C'est une démarche saine — beaucoup de profils comme le tien se sentent coincés entre 'MPSI ou rien', alors qu'il existe une vraie diversité de portes d'entrée.
>
> Voici trois pistes pondérées, à creuser selon ce qui résonne :
>
> **Piste 1 — Écoles d'ingénieurs post-bac (concours communs Geipi Polytech, Puissance Alpha, Avenir, Advance ; INSA en recrutement direct)**
> - Durée : 5 ans intégrés (2 ans cycle prépa + 3 ans cycle ingé), pas de concours intermédiaire
> - Coût : public (Geipi Polytech, INSA) frais de scolarité réduits type universitaire ; privés (Puissance Alpha, écoles Fésic) typiquement plusieurs milliers d'euros par an — vérifier les montants exacts sur le site de chaque école, ils varient fortement
> - Sélectivité : recrutement via Parcoursup (dossier + épreuves ou entretien selon le concours). À noter : INSA est un réseau distinct, avec son propre recrutement, pas adossé à Geipi Polytech. Calendrier des épreuves à vérifier chaque année sur le site officiel de chaque concours
> - Débouché : ingénieur diplômé bac+5, spécialisations possibles bio-info, informatique, robotique selon l'école. Une part significative des ingénieurs français sont recrutés post-bac, c'est une voie pleinement reconnue
>
> **Piste 2 — Cycles Préparatoires Communs (CPC) ou BUT Informatique / MMI**
> - Durée CPC : 2 ans tronc commun + 3 ans en école partenaire ; BUT : 3 ans avec sortie possible bac+3
> - Coût : public, frais réduits
> - Sélectivité : CPC sélection l'année du bac sur Parcoursup (alternative à CPGE pour profils scientifiques) ; BUT accessible sur dossier Parcoursup
> - Débouché : BUT Info ou BUT MMI = base solide pour développeur, data, jeu vidéo (l'Onisep cite explicitement le BUT MMI comme voie publique alternative aux bachelors jeu vidéo privés). Poursuite possible en école d'ingé ou master
>
> **Piste 3 — Bachelors spécialisés privés (jeu vidéo, finance, bio-info)**
> - Durée : 3 ans (bachelor) ou 4-5 ans (cursus long)
> - Coût : significativement plus élevé que le public, souvent plusieurs milliers d'euros par an — à vérifier école par école et à mettre en regard du budget famille
> - Sélectivité : variable, souvent sur dossier + entretien
> - Débouché : selon l'Onisep, plusieurs dizaines d'écoles proposent un cursus jeu vidéo ; pour finance quant et bio-info, c'est un terrain plus restreint en bachelor pur — souvent plus solide via école d'ingé avec spécialisation en M1/M2. Vérifier reconnaissance RNCP et taux d'insertion publiés avant de s'engager
>
> Avant d'aller plus loin : quand tu projettes un quotidien dans 5 ans, qu'est-ce qui te motive le plus — concevoir un système qui résout un problème (ingé), prototyper et coder vite sur un projet concret (BUT/bachelor), ou rester sur un domaine scientifique précis (bio, finance, jeu) ? Ta réponse va beaucoup réduire le champ.

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/ecoles-d-ingenieurs-et-si-vous-aviez-le-profil
> - Date : 2025-2026
> - Extrait clé : La moitié des écoles d'ingénieurs (environ 100 établissements — Insa, ENI, écoles de la Fésic) sont accessibles directement après le bac ; près d'un tiers des étudiants ingénieurs sont recrutés post-bac, sans passer par une CPGE.
>
> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-cycles-preparatoires-communs-aux-ecoles-d-ingenieurs
> - Date : 2025-2026
> - Extrait clé : Les Cycles Préparatoires Communs (CPC) constituent une troisième voie : sélection l'année du bac, 2 ans de tronc commun, puis intégration d'une école partenaire — alternative à CPGE pour profil...

**Critique scores Phase 3** : factuelle **20/25** / posture **23/25** / cohérence **22/25** / hallucination **17/25** = **82/100**

**Corrections suggérées par le critique** :
> Les dates précises (28 avril 2026 Geipi, 25 avril 2026 Puissance Alpha) et le chiffre '35 écoles publiques / 16 privées' sont à risque d'hallucination — à sourcer ou retirer. La fourchette de coût bachelors privés (7-12k€) est correctement étiquetée 'estimation' mais reste imprécise. INSA n'est pas un réseau Geipi/Polytech, à dissocier.

_Décision recommandée par critique : `flag` (vs décision finale `flag` selon score boundary keep≥85 / flag 70-85 / drop<70)_

---

## Q&A #4 — A1 iter 3 (score **86**, decision `keep`, latence 161.2s)

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Quelles sont les meilleures formations en cybersécurité en France ?

**Question (refined par Phase 4)** :
> Quelles sont les meilleures formations en cybersécurité en France pour un profil scientifique qui ne veut pas faire prépa ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu as un bon niveau scientifique, la cybersécurité t'attire, mais la voie MPSI ne te parle pas — tu cherches des alternatives concrètes qui mènent au même type de débouchés sans passer par deux ans de prépa pure.
>
> C'est une démarche très saine, et bonne nouvelle : la cybersécurité est un des rares domaines où plusieurs voies hybrides mènent à des postes recherchés, donc tu n'es pas coincé entre prépa ou rien.
>
> Voici trois pistes que tu peux mettre en balance :
>
> **Piste 1 — BUT Réseaux & Télécommunications parcours Cybersécurité, ou BUT Informatique parcours sécurité (3 ans, université)**
> - Durée : 3 ans, diplôme bac+3 reconnu, possibilité de poursuivre en école d'ingénieur après B2 ou B3 validée (ONISEP 2026).
> - Coût : frais universitaires standards (~170€/an), donc très accessible côté budget modéré.
> - Sélectivité : modérée à sélective selon les IUT, dossier Parcoursup, pas de concours écrit.
> - Débouché : InserJeunes (données 2025) publie les taux d'emploi à 6/12/18 mois par IUT et par parcours — c'est la source à consulter directement pour comparer concrètement avant de candidater, plutôt que de te fier à une fourchette générale.
> - Pour qui : profil concret, qui veut mettre les mains dans la technique vite, garder l'option d'enchaîner en école ensuite.
>
> **Piste 2 — École d'ingénieur post-bac avec spécialisation cyber (5 ans, prépa intégrée)**
> - Durée : 5 ans en cycle continu, pas de prépa séparée — tu rentres directement après le bac via concours Avenir, Puissance Alpha, ou dossiers INSA/UT (Parcoursup 2026).
> - Coût : variable selon statut public/privé — à vérifier école par école sur leur site officiel et sur la fiche Parcoursup. Les écoles publiques (INSA, UT) sont nettement plus accessibles que les écoles privées sous contrat.
> - Sélectivité : sélective, profil cible « bac général + spé Maths + une autre spé scientifique » (Parcoursup 2026).
> - Débouché : titre d'ingénieur reconnu CTI, spécialisations cyber/cloud/réseaux dans les 2 dernières années, bonne insertion mais à vérifier école par école sur InserSup.
> - Pour qui : tu veux le titre d'ingénieur et tu préfères un cadre structuré sur 5 ans plutôt que des passerelles.
>
> **Piste 3 — Bachelor RNCP « ingénieur cybersécurité » ou écoles spécialisées cyber (3-5 ans, privé majoritairement)**
> - Durée : 3 ans (bachelor) ou 5 ans (cycle complet), avec une structure modulaire (blocs de compétences obligatoires + bloc spécialisation type robotique, cyber, cloud) et un niveau d'anglais exigé. Vérifie le numéro de fiche RNCP exact sur france-competences.fr avant de candidater — le contenu et les blocs varient d'une école à l'autre.
> - Coût : généralement plus élevé que le public, à vérifier école par école directement sur leur site (les écarts sont importants entre établissements).
> - Sélectivité : variable — certaines très ouvertes, d'autres avec tests techniques.
> - Débouché : reconnu via RNCP, mais la valeur du diplôme dépend beaucoup de la réputation de l'école — c'est typiquement le genre de filière où InserJeunes ou les retours d'anciens comptent énormément avant de signer.
> - Pour qui : tu veux une formation très orientée métier, hybride (cyber + cloud, cyber + IA, etc.), et tu acceptes un coût plus élevé en échange d'une approche moins académique.
>
> Un point important : « la meilleure formation » dépend autant du contenu que de ce que tu veux faire après — pentester, analyste SOC, cryptographe, consultant gouvernance, ce sont des métiers très différents qui ne se préparent pas tous au même endroit.
>
> Du coup, pour avancer : qu'est-ce qui t'attire le plus dans la cybersécurité aujourd'hui — le côté technique « casser/défendre des systèmes », le côté plus stratégique « protéger une organisation », ou tu n'as pas encore tranché et tu cherches une formation qui te laisse explorer les deux ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/apres-le-bac-les-etudes-superieures/les-principales-filieres-d-etudes-superieures/les-cpge-classes-preparatoires-aux-grandes-ecoles/les-prepas-scientifiques
> - Date : 2026 (page mise à jour par ONISEP)
> - Extrait clé : Les CPGE scientifiques sont une voie parmi d'autres : les bacheliers généraux peuvent aussi rejoindre une école d'ingénieurs post-bac, un BUT, ou intégrer une école après une 2e ou 3e année de BUT validée.
>
> - URL : https://www.parcoursup.gouv.fr/sites/default/files/database/documents/2026-02/pr-sentation-synth-tique-parcoursup-2026-pdf-1116.pdf
> - Date : Février 2026
> - Extrait clé : Parcoursup 2026 référence l'ensemble des formations post-bac reconnues par l'État : licences, BUT, BTS, écoles d'ingénieurs post-bac (concours Avenir, Puissan...

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **23/25** / hallucination **19/25** = **86/100**

**Corrections suggérées par le critique** :
> Les chiffres marqués 'estimation, connaissance générale' (70-85% insertion, 6000-12000€/an, 7000-10000€/an ESILV/EFREI) restent des fourchettes non sourcées même flaggées — préférer renvoyer vers InserJeunes/sites écoles sans avancer de chiffre. RNCP 40534 à vérifier (numéro précis cité comme source). Bonne reformulation initiale et question de relance finale ouverte.

_Décision recommandée par critique : `keep` (vs décision finale `keep` selon score boundary keep≥85 / flag 70-85 / drop<70)_

---

## Q&A #5 — A1 iter 4 (score **78**, decision `flag`, latence 174.7s)

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
> Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

**Question (refined par Phase 4)** :
> J'hésite entre l'ENSEIRB-MATMECA et l'EPITA pour me spécialiser en cybersécurité, comment je peux trancher si je veux éviter la prépa MPSI ?

**Answer (refined par Phase 4)** :

> Si je te comprends bien, tu vises la cybersécurité comme spécialité, tu écartes la voie prépa MPSI classique, et tu compares deux écoles aux ADN très différents — une école publique historiquement post-prépa et une école privée post-bac. C'est une comparaison qui mérite d'être dépliée parce qu'elles ne jouent pas dans le même championnat d'admission.
>
> Voici trois pistes à explorer, sans hiérarchie :
>
> **Piste 1 — EPITA, voie post-bac directe**
> Tu entres après le bac via le Concours Avenir, 2 ans de prépa intégrée puis 3 ans de cycle ingénieur, soit 5 ans au total. Ce modèle prépa intégrée correspond exactement à ce que décrit l'ONISEP : près d'un tiers des étudiants ingénieurs sont recrutés ainsi, avec passage en contrôle continu, plus doux qu'une CPGE. La majeure SRS (Système, Réseaux, Sécurité) est leur signature en cyber. Coût : école privée, ordre de grandeur autour de 10-12 k€/an à vérifier sur leur site officiel (les frais évoluent chaque année). Sélectivité : exigeante sur maths/physique mais accessible sans MPSI. Débouché cyber : pentest, SOC, conseil sécurité dans le privé.
>
> **Piste 2 — ENSEIRB-MATMECA, voie admission parallèle après BUT**
> L'ENSEIRB recrute majoritairement après CPGE, donc l'accès post-bac direct est très restreint. Si tu veux éviter MPSI, le chemin réaliste passe par un BUT informatique (parcours cybersécurité disponible dans plusieurs IUT) puis admission parallèle en cycle ingé — l'ONISEP confirme que le BUT ouvre explicitement cette porte, éventuellement renforcée par une prépa ATS scientifique. Coût : très bas (frais d'inscription école publique, à confirmer sur le site officiel). Durée : 3 ans BUT + 3 ans école = 6 ans au lieu de 5. Atout : diplôme d'État, marque ENSEIRB, profil hybride théorique/pratique.
>
> **Piste 3 — Une école cyber dédiée post-bac**
> Quelques écoles sont entièrement orientées cybersécurité dès la première année. L'ENSIBS à Vannes propose par exemple une filière cyberdéfense post-bac (école publique d'ingénieurs). D'autres établissements affichent une coloration cyber forte dès l'entrée — il est plus prudent d'aller vérifier directement les fiches Parcoursup et les JPO plutôt que de se fier à une liste mémorisée, parce que les intitulés et les parcours bougent d'une année à l'autre. La phase d'admission Parcoursup ouvre le 2 juin 2026, donc tu as le temps d'aller aux JPO de plusieurs avant de te positionner.
>
> Une question pour t'aider à trancher : qu'est-ce qui pèse le plus pour toi entre éviter complètement la prépa, minimiser le coût annuel, et la durée totale du parcours avant ton premier vrai poste en cyber ?

**Sources research (Phase 1 WebSearch, extraits)** :

> - URL : https://www.onisep.fr/formation/les-principaux-domaines-de-formation/les-ecoles-d-ingenieurs/les-differentes-voies-d-acces-en-ecole-d-ingenieurs
> - Date : 2025-2026 (page ONISEP maintenue)
> - Extrait clé : Près d'un tiers des étudiants ingénieurs sont recrutés directement après le bac via prépa intégrée (5 ans, 2+3), alternative moins stressante que la CPGE avec passage sur contrôle continu.
>
> - URL : https://www.onisep.fr/formation/apres-le-bac-les-etudes-superieures/les-principales-filieres-d-etudes-superieures/les-but-bachelors-universitaires-de-technologie
> - Date : 2025-2026
> - Extrait clé : Le BUT (bac+3, diplôme national) ouvre l'accès aux écoles d'ingénieurs via admissions parallèles ; possibilité de passer par une prépa ATS scientifique pour augmenter ses chances.
>
> - URL : http...

**Critique scores Phase 3** : factuelle **18/25** / posture **23/25** / cohérence **22/25** / hallucination **15/25** = **78/100**

**Corrections suggérées par le critique** :
> ESNA Toulouse n'existe pas (confusion probable avec ENSEEIHT ou ESAIP) — à retirer ou remplacer par une école cyber post-bac vérifiée (ex: Guardia est blocklist, mais ENSIBS Vannes est valide). Le coût EPITA cité ~9-10k€/an est sous-estimé (réel ~10-12k€). Marquer plus clairement les chiffres comme estimatifs ou les retirer.

_Décision recommandée par critique : `flag` (vs décision finale `flag` selon score boundary keep≥85 / flag 70-85 / drop<70)_

---

## Lecture du verdict (synthèse)

- ✅ **Active listening + reformulation systématique** : tous les 5 Q&A ouvrent par "Si je te comprends bien..." ou équivalent
- ✅ **3 pistes pondérées non-prescriptives** : aucun "tu devrais", toujours "Voici trois pistes" / "à pondérer selon ce qui résonne"
- ✅ **Tone tutoiement** respecté sur tous les samples (cohérent profil lycéen 17 ans)
- ✅ **Question finale d'exploration** clôt chaque réponse
- ✅ **Marqueurs `(estimation, connaissance générale)`** présents pour chiffres approximatifs

**Points forts** :
- Posture conseiller : 23.4/25 mean — top
- Cohérence persona : 22.6/25 mean — top

**Points faibles (axe hallucination 17.8/25 mean)** :
- Q&A #5 (score 78, flag) : critique catch *"ESNA Toulouse n'existe pas (confusion probable avec ENSEEIHT ou ESAIP)"* — école inventée par draft
- Q&A #3 (score 82, flag) : critique catch *"dates précises 28 avril 2026 Geipi, 25 avril 2026 Puissance Alpha"* — chiffres non sourcés
- Q&A #4 (score 86, keep) : critique signale *"chiffres 70-85% insertion / 6000-12000€ ESILV-EFREI restent fourchettes non sourcées même flaggées estimation"*

→ **Le filtre score≥85 protège bien le dataset final** : les hallucinations non-marquées partent en `flag` (review humaine mardi 29/04 par Matteo + Ella + Deo Munduku) au lieu de `keep` automatique. Le critique Phase 3 fait son job.

**Calibration potentielle** (à voir post-sample humain mardi) :
- Forcer `(estimation)` plus systématiquement sur tous chiffres dans le prompt Phase 2
- Ajouter règle anti-école-inventée explicite dans Phase 3 (vérifier existence avant mention)
- Note : ces calibrations attendent le signal sample humain, pas d'itération à blanc avant nuit

---

*Dry-run validé GO côté Claudette + Jarvis. Décision GO/NO-GO nuit 22h relayée à Matteo via Jarvis.*
