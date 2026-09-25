# Contrat du cerveau : le pipeline v2 d'OrientAI

Version v1.1, 24/09/2026, Jarvis (v1.1 : décisions de l'après-midi, feuille de route, méthode, où vit le plan). **Validé par Matteo le 24/09 à 17h12 (Telegram 10703) : les 7 choix de la section 11 suivent la recommandation.** Écrit AVANT tout code (Telegram 10693 : « go commence l'étape 2 »). Modèle retenu entre-temps au banc E : GLM 5.3 avec la carte courte + l'outil `lire_fiche` (PR #186, 7b6c4f9). Périmètre : Informatique, Santé, Maths (démo investisseurs). Rien de ce contrat ne touche la prod actuelle.

## 0. En bref (ce que Matteo valide)

- **Un pipeline v2 construit à côté du v1**, pas une réparation. Le v1 (17 étages, onglet « État des lieux ») reste en prod tant que le v2 ne le bat pas au banc.
- **4 étages seulement** : filtre de sécurité (repris tel quel du v1), cerveau (le modèle + des outils sur la base C), vérificateur de chiffres, réponse.
- **Le modèle ne cherche plus « au jugé »** : il appelle des outils à filtres fermés sur la base C (3 945 formations, 172 981 chiffres sourcés). Il n'écrit jamais de SQL.
- **Aucun chiffre n'est affiché sans avoir été vérifié** contre ce que les outils ont rendu dans la conversation.
- **Le profil de l'élève** (voie de bac, spécialités, moyenne, ville, contraintes) est retenu le temps de la conversation, et une seule règle dit quand poser une question.
- **30 questions-tests** (gate F), écrites avant le code, avec les fiches que les outils doivent rendre. Elles viennent des données officielles déjà vérifiées (gate C et banc vertical).
- **7 choix** en section 11, **tranchés le 24/09 : la recommandation partout**.

## 1. Pourquoi ce découpage (mesures)

| Constat | Mesure | Trace |
|---|---|---|
| La recherche actuelle rate la bonne fiche | bonne fiche dans les 10 premières : 61,6 % (au service) | `results/jarvis_analyse_2026-09-05/REPRISE.md` l.104, recall@10 serving 0,616 (86 questions, borne basse) |
| Le classement est décidé par des bonus fixes, pas par la question | écart de score 3,2 % entre rang 1 et rang 100 ; 0 des 5 premières fiches par sens ne survit au tri, en médiane | RAPPORT 05/09 §4.2 |
| Le modèle ne voit que 5 fiches sur 10 à 12 | `V4_MAX_SOURCES = 5` | `src/rag/generator.py:36` |
| Le prompt strict détruit la réponse | 90 mots en médiane, 33 % de refus, note 1,99/5 | banc lot 0 du 23/09, onglet État des lieux |
| Avec les BONNES fiches, le modèle cite 81 % des chiffres attendus | étape D, exposition gelée (borne haute) | RAPPORT D |
| Des requêtes structurées rendent exactement les bonnes fiches | gate C : 20/20, 69/69 chiffres | PR #183 |
| Un agent à outils retrouve ce que le RAG rate | LAS Psycho Bordeaux, Licence Info Toulouse III, BTS MCO/NDRC | spike du 05/09, RAPPORT §5 |

Conclusion : le trou est entre la question et les fiches. On le ferme en laissant le modèle **demander** les fiches par critères, au lieu de les **deviner** par ressemblance de texte.

## 2. Les 4 étages du v2

```
message de l'élève
  -> 1. filtre de sécurité et de sujet   (repris du v1, inchangé)
  -> 2. cerveau : boucle modèle + outils (au plus 6 appels)
  -> 3. vérificateur de chiffres         (déterministe)
  -> 4. réponse affichée
```

1. **Filtre de sécurité et de sujet** : `ScopeClassifier` du v1 (`src/rag/scope_classifier.py`), sans modification. Détresse : réponse toute écrite avec 3114, 119, 3919. Hors sujet : refus poli. Il reste le premier étage, avant tout appel au modèle principal.
2. **Cerveau** : le modèle choisi au banc E (Medium 3.5, GLM 5.2, GLM 5.3 ou Small 4) reçoit le prompt de conseiller, le profil courant et le catalogue d'outils (section 3). Il appelle les outils dont il a besoin, puis rédige. Au plus **6 appels d'outils** par message de l'élève. Au-delà, il répond avec ce qu'il a et le dit.
3. **Vérificateur de chiffres** : chaque pourcentage, montant en euros et nombre de places du brouillon doit se retrouver dans ce que les outils ont rendu pendant la conversation (même logique que `src/eval/battery/numbers.py`, unités `pct`, `eur`, `places`). Section 6.
4. **Réponse** : affichée une fois vérifiée. Pendant les appels d'outils, l'écran montre les étapes (« je cherche les BUT informatique près de Lens… »). Choix Q2.

Ce qui **disparaît** du v1 : routeur LLM, mode récit, intention par règles, SELECT approximatif, recherche par sens et par mots-clés, fusion RRF, bonus fixes (« reranker »), MMR, garde géographique, exemple golden_qa, fact cards, prompt strict v4, validation par règles, nouvelle tentative, policy. Aucun n'est supprimé du dépôt : ils restent au v1.

## 3. Les outils (catalogue fermé)

Chaque outil a des paramètres typés et bornés. Une valeur hors liste renvoie une erreur qui **nomme les valeurs admises les plus proches**, pour que le modèle se corrige lui-même. Chaque résultat renvoie les **filtres effectivement appliqués**, le **nombre total** de résultats, s'il est **tronqué**, et combien de formations ont été **écartées faute de valeur** (« non disponible » n'est jamais un zéro).

| Outil | Existe ? | Ce qu'il fait | Paramètres principaux |
|---|---|---|---|
| `chercher_formations` | oui, `src/base_c/outils.py:276` | formations post-bac (Parcoursup, apprentissage) qui passent tous les filtres | `types` (pass, las, licence, but, bts, cpge, cupge, ifsi, diplome_sante, ecole_ingenieur, titre_pro), `filieres`, `intitule_contient`, `apprentissage`, `statut`, `communes` / `departements` / `regions`, `pres_de` {commune, rayon_km ≤ 300}, `taux_acces_min` (≥) / `taux_acces_max` (<), `places_min`, `part_bac_techno_min`, `part_bac_pro_min`, `session` (2023 à 2025), `tri`, `limite` ≤ 50 |
| `chercher_masters` | oui, `outils.py:301` | masters MonMaster 2025 (informatique et maths) | `mention_contient`, `secteurs`, `regions_academiques`, `departements`, `pres_de`, `alternance`, `capacite_min`, `tri`, `limite` |
| `lire_fiche` | oui, `outils.py:320` | tout ce que la base sait d'une formation : chaque chiffre avec sa source, son année, sa portée (formation, université, national) et la raison d'un « non disponible » ; insertion ; liens d'alternance | `id` |
| `trouver_commune` | oui, `outils.py:57` | résout un nom de commune (homonymes : plusieurs candidats, le modèle choisit ou demande) | `nom`, `departement` |
| `lister_valeurs` | oui, `outils.py:67` | valeurs admises d'un champ (filières, régions…), avec leurs effectifs | `champ`, `types` |
| `trouver_formation` | **à créer** | retrouve une formation **nommée** par l'élève (« le BUT info de Lens », « MP2I à Clemenceau », « l'IUT Lyon 1 ») : recherche par mots-clés normalisés sur intitulé + établissement + commune, sigles dépliés (IUT, UCA, UPS, INSA…), « Lyon1 » lu « Lyon 1 » ; rend au plus 10 candidats avec leur identifiant | `texte`, `commune` (facultatif), `types` (facultatif) |
| `comparer` | **à créer** | 2 à 5 formations côte à côte, mêmes champs, mêmes années, chacun sourcé : évite que le modèle mélange les chiffres de deux fiches | `ids`, `champs` (facultatif) |
| `mettre_a_jour_profil` | **à créer** | enregistre ce que l'élève a dit de lui (section 4) ; rend le profil complet | champs du profil |
| `chercher_connaissance` | **plus tard** (étape 6) | petit corpus de procédures (calendrier Parcoursup, bourses, césure, réforme santé 2027), découpé par section | `question` |

Règles d'usage écrites dans le prompt (et mesurées au gate F) :
- **chercher avant de citer** : aucun chiffre sur une formation sans l'avoir lue par un outil pendant la conversation ;
- **une formation nommée par l'élève** se retrouve d'abord par `trouver_formation`, puis se lit par `lire_fiche` ;
- **une question à critères** (« à moins de 50 km », « au moins 35 % de bacs techno ») se traduit en filtres de `chercher_formations`, jamais en ressemblance de texte ;
- **si le résultat est tronqué** ou si des formations sont écartées faute de valeur, la réponse le dit (« j'en ai trouvé 23, voici les 8 plus accessibles »).

Forme des résultats rendus au modèle : le choix entre le texte de fiche de l'étape A et une carte courte + `lire_fiche` sera fixé par le **banc E** (en cours, résultats le 24/09). Le contrat ne le préjuge pas.

## 4. Le profil de l'élève

Retenu **le temps de la conversation**, côté serveur, réinjecté au modèle à chaque message. Rien n'est gardé après la conversation dans le v2 (la mémoire de trajectoire est un chantier ultérieur, avec comptes et consentement).

| Champ | Exemple | Sert à |
|---|---|---|
| `statut` | lycéen, étudiant, parent, en réorientation | ton, pertinence |
| `niveau_actuel` | terminale, L1, L3, bac obtenu | ce qui est accessible |
| `voie_bac` | générale, STI2D, ST2S, STMG, bac pro CIEL, bac pro ASSP… | filtres `part_bac_techno_min`, `part_bac_pro_min` |
| `specialites` | maths + NSI, SVT + physique-chimie, maths complémentaires | adéquation |
| `moyenne` | 12, « 16 en maths » | réalisme, jamais un verdict |
| `commune` | Lens (code INSEE résolu) | `pres_de` |
| `mobilite` | « pas loin », rayon en km, prêt à partir | `rayon_km` |
| `budget` | « pas un gros budget » | public, apprentissage, coût |
| `alternance` | souhaitée, indifférent | `apprentissage` |
| `interets` | informatique, cybersécurité, santé sans être médecin | domaines, filières |
| `a_eviter` | « pas de prépa », « pas le droit » | exclusion (le v1 le transformait en inclusion) |
| `formations_citees` | identifiants retrouvés | suivi multi-messages |

Pas de nom, pas d'e-mail, pas de lycée nominatif : l'élève est souvent mineur, le profil ne contient que ce qui sert à chercher.

## 5. La règle de clarification

Une seule règle, mesurée par les questions `F-Q*` et `F-M*` du gate F :

1. **Toujours répondre d'abord** : une première orientation utile, même avec un profil vide (les grandes voies, ce qui les distingue).
2. **Puis au plus 2 questions**, les plus discriminantes pour la recherche, dans cet ordre de priorité : le domaine visé, la voie de bac et les spécialités, la ville ou la zone.
3. **Jamais de liste de formations chiffrée** tant que la zone ou le domaine manque : pas de chiffres sans outil, pas d'outil sans critère.
4. Au message suivant, le profil complété déclenche la recherche **sans redemander** ce qui a déjà été dit.

## 6. Le vérificateur de chiffres

- **Portée** : pourcentages, montants en euros, nombres de places (unités de `numbers.py`). Les durées (« 3 ans »), niveaux (« bac+5 ») et dates ne sont pas contrôlés.
- **Adossé** = la valeur figure dans un résultat d'outil de la conversation (lecture, recherche, comparaison). Les chiffres nationaux santé (PASS 47,5 %, LAS 25,7 %) sont dans la base avec leur portée : ils passent, à condition d'être dits nationaux (contrôle par le juge).
- **Non adossé** : une réécriture est demandée au modèle (« ce chiffre n'est dans aucun résultat : retire-le ou appelle l'outil qui le donne »). Si le second brouillon garde un chiffre non adossé, la phrase est retirée et l'incident est tracé. Choix Q6.
- **Trace** : chaque chiffre affiché garde son identifiant de fiche et sa source, pour l'afficher sous la réponse (et dans l'explorateur).

## 7. Traces et instrument (lien avec l'étape 1)

Chaque message produit une trace au format de l'onglet « État des lieux » : filtre (décision), appels d'outils (nom, paramètres, identifiants rendus, nombre de résultats), profil avant et après, brouillon, vérification (chiffres adossés, retirés), réponse, latence, coût. Le lanceur de l'étape 1 joue v1 et v2 sur les mêmes bancs ; l'explorateur les montre côte à côte, question par question.

## 8. Cibles (planchers, puis on optimise)

Mesurées sur le banc vertical (57 conversations) et le banc tous domaines (67 tours), juge à l'aveugle qui voit les fiches :

| Critère | Plancher | Repère |
|---|---|---|
| Réponses avec erreur de fait (juge) | < 10 % | Medium 43 %, GLM 5.2 16,5 % en D (borne haute) |
| Refus | < 10 % | prod 33 % |
| Chiffres attendus cités justes | ≥ 85 % | 81 % en D avec les fiches données à la main |
| Chiffres affichés adossés | 100 % (vérificateur) | prod 58 % (banc lot 0) |
| Note moyenne du juge | la plus haute possible ; repère à battre : GPT-5.5 seul, 4,28 | prod 1,99 |
| Latence p90 | < 15 s | prod 6,2 s (sans outils) ; spike agent 8,5 s médiane (Mistral) |

Gate F (section 9) : couverture des fiches attendues ≥ 90 % sur les familles recherche, nom, multi-tour et honnêteté ; 0 formation citée hors des résultats d'outils ; 100 % des questions de clarification avec orientation d'abord et au plus 2 questions.

## 9. Le gate F : 30 questions-tests (écrites avant le code)

Fichier `gate_f/requetes_gate_f.json` (sha 5c78dc6e9001), produit par `gate_f/build_gate_f.py` (déterministe). 102 fiches attendues, toutes présentes dans la base C. Aucune liste ne vient de la base : elles viennent du gate C (calculé sur les jeux officiels Parcoursup, apprentissage, MonMaster, geo.api) et du banc vertical (267/267 chiffres identiques au jeu officiel).

| Famille | N | Ce qu'on mesure |
|---|---|---|
| recherche | 12 | la question à critères devient les bons filtres : toutes les fiches attendues sont rendues par les outils |
| nom | 8 | les formations nommées par l'élève sont retrouvées par leur identifiant avant d'être chiffrées |
| clarification | 5 | question vague : orientation d'abord, au plus 2 questions, aucun chiffre sans outil |
| multi-tour | 2 | le 2e message complète le profil, la recherche en tient compte |
| honnêteté | 3 | donnée absente (pas de PASS à Poitiers), portée nationale (passage PASS Lille), piège de lecture (taux d'accès ≠ chances) |

Mesures par question : fiches attendues retrouvées ; formations citées hors résultats (doit être 0) ; chiffres adossés ; nombre d'appels et erreurs d'outils ; questions posées ; verdict du juge sur la règle écrite.

## 10. Organisation du code

- Nouveau paquet `src/v2/` : `pipeline.py` (les 4 étages), `outils.py` (enveloppe des outils de `src/base_c/outils.py` + les 3 nouveaux), `profil.py`, `verificateur.py`, `prompt.py`.
- Réutilisé tel quel : `src/rag/scope_classifier.py`, `src/base_c/outils.py`, `src/eval/battery/numbers.py` (logique d'extraction).
- Une route d'API séparée (`/v2/answer/stream`), désactivée en prod par défaut ; le v1 reste la seule route servie.
- Tests : chaque outil avec ses bornes, et un test de sabotage par garantie (un vérificateur qui laisse passer un chiffre inventé doit rougir).

## 11. Choix tranchés par Matteo le 24/09 à 17h12 : la reco partout (Telegram 10703)

| # | Question | Options | Reco |
|---|---|---|---|
| Q1 | v2 à côté ou réparation du v1 ? | a) v2 à côté, v1 en prod jusqu'à ce que le v2 le batte ; b) réparer le v1 étage par étage | **a** : le v1 a des étages morts et des réglages qui s'annulent (onglet État des lieux) |
| Q2 | Afficher la réponse en direct ou après vérification ? | a) après vérification, avec les étapes de recherche affichées pendant l'attente ; b) en direct, vérification a posteriori | **a** : c'est la seule façon de garantir « aucun chiffre non vérifié à l'écran » |
| Q3 | Durée de vie du profil | a) la conversation seulement ; b) persistant (compte) | **a** pour le v2 ; b) = chantier mémoire de trajectoire, avec consentement |
| Q4 | Question hors Info, Santé, Maths | a) réponse générale honnête, sans chiffres, « pas encore couvert en détail » ; b) repli sur l'ancien RAG | **a** (décision du 24/09 : ancien RAG mis de côté) |
| Q5 | Plafond d'appels d'outils par message | 4, 6 ou 8 | **6** (état de l'art relevé le 05/09, RAPPORT §6 : le sur-appel est le 1er mode d'échec des agents, plafonner est unanime ; le spike plafonnait à 8) |
| Q6 | Chiffre non vérifié | a) 1 réécriture, sinon phrase retirée et tracée ; b) chiffre marqué « non vérifié » à l'écran | **a** |
| Q7 | Masters dans la démo | a) oui, 480 masters informatique et maths déjà dans la base ; b) post-bac seulement | **a**, déjà couvert par `chercher_masters` |

## 12. Ce qui est décidé depuis, et ce qui reste ouvert

Décidé le 24/09 :
- **Modèle** : GLM 5.3 (`zai-glm-5-3`, API Mistral, point d'accès Europe `api.eu.mistral.ai`), avec la carte courte + l'outil `lire_fiche` (format C). Banc E : 12,7 % de réponses avec erreur de fait contre 75,9 % pour Medium, juge qui voit les fiches (PR #186, 7b6c4f9, `results/banc_e/RAPPORT.md`). Borne haute : les fiches étaient fournies.
- **Pas de framework d'agents** (Matteo 10708) : la boucle est écrite par nous (environ 150 lignes, estimation), pour garder chaque étape visible. **Pydantic** (déjà dans le dépôt, 2.12.5) décrit chaque outil et le profil une seule fois : description envoyée au modèle, validation de ce qu'il renvoie, traces. **Langfuse** à la mise en prod seulement (shim `src/observability` jamais branché). **DSPy** après un v2 stable.
- **Référence de mesure** (Matteo 10707) : la cible est « ChatGPT seul » (GPT-5.5 sans fiches) ; la prod n'est jouée qu'une fois, comme photo « avant » et contrôle de non-régression. Le 4,28 de GPT-5.5 vient du banc du 05/09 (60 conversations, juge sans fiches) : il doit être rejoué sur nos bancs avec le juge actuel (coût OpenAI à chiffrer avant).

Reste ouvert :
- le texte du prompt de conseiller (étape 4, travaillé avec Matteo) ;
- le corpus de procédures (étape 6) ;
- la mise en prod : après que le v2 bat la prod au banc, avec la réparation du déploiement automatique (dette Railway) ;
- l'hébergement souverain (décision ouverte au QG : aucune offre LLM qualifiée SecNumCloud au 24/09, GLM absent des offres souveraines).

## 13. Feuille de route, dans l'ordre (validée par Matteo le 24/09)

| Étape | Qui | Livrable | Gate avant la suivante |
|---|---|---|---|
| 0 | Claudette | ce contrat et le gate F versionnés dans le dépôt OrientIA (`docs/cerveau/`), REPRISE.md qui pointe dessus | PR docs mergée |
| 1. Instrument | Claudette | un lanceur unique qui joue une version du pipeline (v2, prod, ChatGPT seul) sur le banc vertical (57 conversations) et le banc lot 0 (67 tours) ; traces au format de l'onglet « État des lieux » ; critère 1 (chiffres justes, `numbers.py`, extracteur corrigé pour les tableaux), juge à l'aveugle qui voit les fiches, coût, latence ; premier run : la prod (une fois) et ChatGPT seul | Jarvis vérifie, Matteo voit les runs dans l'explorateur (sélecteur de version) |
| 2. Contrat | Jarvis | ce document et le gate F | **fait, validé le 24/09** |
| 3. v2 minimal | Claudette | `src/v2/` : filtre de sécurité repris, boucle GLM 5.3 + outils base C (dont les 3 à créer : `trouver_formation`, `comparer`, `mettre_a_jour_profil`), vérificateur de chiffres, prompt de conseiller v0 simple | gate F (section 9) + bancs, dans l'explorateur |
| 4. Réponse | Jarvis + Matteo, puis Claudette | prompt de conseiller travaillé, vérificateur réglé | bancs : planchers de la section 8 |
| 5. Conversation | Claudette | profil sur plusieurs messages, règle de clarification (section 5) | familles clarification et multi-tour du gate F |
| 6. Procédures | Jarvis (sources) + Claudette | petit corpus sourcé (calendrier Parcoursup, bourses, réforme santé), `chercher_connaissance` | questions de procédure des bancs |

Ensuite : prod propre (déploiement automatique, point d'accès Europe, Langfuse), vrais utilisateurs (lycéens, conseillers), pack démo.

## 14. Méthode de travail (à respecter à chaque session, sans exception)

Ce qui a fait tenir les étapes A à E, et qui ne doit pas se dégrader :
1. **Contrat avant code** : chaque étape commence par un écrit (contrat, protocole) relu par Jarvis, et par Matteo quand il y a un choix. Les tests (gate) sont écrits AVANT le code, à partir des sources officielles, jamais à partir de notre base.
2. **Règle de décision écrite avant le run** : critère principal, garde-fous, budget, arrêt. Un amendement se date avant la lecture des résultats.
3. **Vérification indépendante par Jarvis** : chaque livraison de Claudette est recomptée avec un code et des copies de sources propres à Jarvis, avec un témoin positif (un sabotage doit faire rougir le contrôle). « 0 écart » se publie avec son périmètre.
4. **Matteo voit chaque étape** dans l'explorateur (avant/après, réponses côte à côte, signalements), puis valide ; merge seulement sur son go, relayé par Jarvis (`merge-approval`).
5. **Règle 13** : toute affirmation qui porte une décision cite sa mesure (fichier, commande, date), sinon elle est marquée « supposé ».
6. **Coûts** : aucun appel payant avant le protocole validé ; prix lus sur la page publiée, jamais supposés sans le dire ; aucun juge relancé sans le go de Matteo (quota de l'abonnement, consigne du 24/09).
7. **Traçabilité** : chaque ordre passe par `/order` (note dans le vault), chaque événement significatif met à jour le QG (orientai-hq, `content/`, puis déploiement), commits étroits, opérations sur `.git` annoncées avant (règle 14).

Pièges d'outillage déjà rencontrés (24/09) :
- juge `claude -p` : passer les lots par l'entrée standard (stdin), jamais par l'outil de lecture (limite de 25 000 tokens par lecture : lectures partielles silencieuses, témoin 8bf2a1383d) ;
- mise à jour de Claude Code pendant un run : binaire nvm en chemin absolu, `DISABLE_AUTOUPDATER=1` ;
- ne jamais sourcer le `.env` d'OrientIA dans le shell du juge (clé Anthropic) ; tests lancés sur un export `git archive` pour éviter `load_dotenv` ;
- `tool_choice` « any » ou « required » ne force pas l'appel d'outil chez Medium sur cette API ; la consigne explicite fonctionne ;
- alias : `zai-glm-5` et `zai-glm-latest` pointent vers GLM 5.3, toujours écrire l'identifiant exact.

## 15. Où vit ce plan

- Source de travail : `~/projets/_orientai-ref/cerveau-2026-09/` (ce fichier, `gate_f/`).
- Copie versionnée : vault Obsidian `01-Projets/Actifs/OrientAI-Cerveau-v2/` (sous git) ; puis dans le dépôt OrientIA à l'étape 0.
- Résumé et décisions : QG https://orientai-hq.vercel.app (chantier « Le cerveau », décisions du 24/09).
- Lecture visuelle : explorateur, onglet « Cerveau : contrat ».
