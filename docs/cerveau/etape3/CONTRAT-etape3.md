# Contrat de l'étape 3 : le v2 minimal du cerveau

Version v0, 25/09/2026, Claudette. Ordre `2026-09-25-1907-claudette-orientai-etape3-v2-minimal` (go de Matteo le
25/09 à 19h06, Telegram 10778). Écrit AVANT toute ligne de code du v2 (section 14.1 du contrat du cerveau). À relire
par Jarvis ; les choix de la section 10 sont à trancher par Matteo. Aucun appel payant avant la validation.

Contrat parent : `docs/cerveau/CONTRAT-cerveau.md` v1.2 (sha256 `07dee32b0949...`), sections 2, 3, 6, 10 et 13
(étape 3). Ce document les précise ; en cas de contradiction, le parent gagne, sauf décision datée de Matteo citée ici.

## 0. En bref

- `src/v2/` : les 4 étages du parent (filtre de sécurité repris, cerveau GLM 5.3 + outils, vérificateur de chiffres,
  réponse), une boucle écrite par nous (pas de framework), Pydantic pour décrire et valider chaque outil et le profil.
- 3 outils nouveaux (`trouver_formation`, `comparer`, `mettre_a_jour_profil`) et `lire_fiche` réduit à l'essentiel
  par défaut, détail à la demande.
- **L'essentiel est mesuré, pas choisi au jugé** (section 4) : 10 notions couvrent 292 des 304 chiffres attendus du
  banc vertical que la base rend (96,1 %), et ramènent une fiche Parcoursup de 43 à 10 valeurs en médiane.
- La prod n'est pas touchée : pas de route d'API à cette étape (choix C5), la v2 se joue par le lanceur de l'étape 1.
- Gate de l'étape 3 = gate F (30 questions) ; les bancs sont joués et montrés contre la référence figée, leurs
  planchers (section 8 du parent) sont le gate de l'étape 4 (section 9).
- Budget Mistral : plafond 15 USD, arrêt automatique, un essai à blanc puis le gate F avant les bancs pour mesurer le
  coût par tour au lieu de le supposer. Le juge (abonnement) ne tourne que sur le go de Matteo.

## 1. Périmètre

Dans l'étape 3 : `src/v2/{pipeline,outils,profil,verificateur,prompt}.py`, la version `v2` du lanceur, le banc gate F
branché au lanceur, les mesures du gate F, l'export des traces pour l'explorateur, les tests.

Hors de l'étape 3 : le prompt travaillé (étape 4), la règle de clarification sur plusieurs messages au-delà de ce que
le prompt v0 en dit (étape 5), `chercher_connaissance` (étape 6), toute mise en prod, Langfuse, DSPy.

Ne bouge pas : `src/rag/scope_classifier.py`, `src/base_c/outils.py` (enveloppés, jamais modifiés), la base C (empreinte
`bfb26cdddfc6`), les bancs (sha `f467374be3d7`, `5b268bf34d91`), le gate F (`5c78dc6e9001`), le juge `judge_v2`, la
référence figée `results/multiversion/2026-09-25_reference/`.

## 2. Le pipeline (`src/v2/pipeline.py`)

Un message de l'élève, dans l'ordre :

1. **Filtre** : `ScopeClassifier(client, model="mistral-small-2603").classify(message, history)`, sans modification du
   module (l'identifiant exact est passé en paramètre, `src/rag/models.py` porte déjà `mistral-small-2603`). Tout label
   autre que `in_scope` rend la réponse toute écrite du classifieur et arrête là (détresse : 3114, 119, 3919).
2. **Cerveau** : appel `chat.complete` sur `zai-glm-5-3`, `server_url="https://api.eu.mistral.ai"`, avec le prompt v0
   (section 7), le profil courant en JSON, l'historique de la conversation (messages de l'élève et réponses affichées,
   pas les résultats d'outils des tours précédents) et le catalogue d'outils (schémas Pydantic, section 3),
   `tool_choice="auto"`. Tant que le modèle demande des outils : on les exécute dans l'ordre, on rend chaque résultat
   (ou son erreur) comme message `tool`, on rappelle le modèle.
   - **Plafond : 6 appels d'outils par message de l'élève**, appels parallèles comptés un par un. Au-delà, les appels
     demandés ne sont pas exécutés : leur message `tool` dit « plafond de 6 recherches atteint : réponds avec ce que tu
     as et dis-le », puis un dernier appel avec `tool_choice="none"`. Le plafond atteint est tracé.
   - **Étapes affichées** (choix Q2 du parent) : chaque appel d'outil émet un événement `etape` dont la phrase est
     construite par le code à partir du nom et des paramètres (« je cherche les BUT informatique près de Lens »),
     jamais par le modèle.
   - Une erreur d'outil (`FiltreInvalide`, validation Pydantic) n'arrête rien : elle revient au modèle comme résultat,
     avec les valeurs proches (section 3), et compte dans les 6.
   - Une panne d'API (après les nouvelles tentatives du client) rend un message d'excuse fixe, sans chiffre, tracé
     comme panne ; le lanceur la compte (il le fait déjà pour la prod).
3. **Vérificateur** (section 6) sur le brouillon ; au plus une réécriture, qui peut appeler des outils dans ce qui
   reste des 6.
4. **Réponse** : émise une fois vérifiée (événement `reponse`), suivie des sources des chiffres affichés.

Trace par message (format « État des lieux », section 7 du parent), écrite par le pipeline et reprise telle quelle par
le lanceur : décision du filtre ; chaque appel d'outil (nom, paramètres, identifiants rendus, `nb_resultats`,
`tronque`, erreur éventuelle, durée) ; profil avant et après ; brouillon 1, vérification 1, brouillon 2 et
vérification 2 le cas échéant (chiffres adossés avec fiche et source, chiffres non adossés, phrases retirées) ;
réponse ; latence par étage ; jetons et coût par modèle (enveloppe `ClientCompte` de l'étape 1).

## 3. Les outils (`src/v2/outils.py`)

Chaque outil = un modèle Pydantic (`extra="forbid"`) dont le schéma JSON est la description envoyée au modèle, et qui
valide ce que le modèle renvoie. Une valeur hors liste lève une erreur qui **nomme les valeurs admises les plus
proches** (`difflib.get_close_matches`, comme `src/base_c/outils.py` le fait déjà dans `_verifier_liste`). Les résultats
de recherche gardent la forme de `_rechercher` : `filtres_appliques`, `nb_resultats`, `tronque`, `limite`,
`ecartees_non_disponible`, `resultats`, `sources`. Ce que le modèle voit : le format C retenu au banc E (PR #186),
cartes courtes dans les résultats de recherche et fiche en texte par `lire_fiche` (`src/eval/format_d.py`, `carte_c`,
`carte_b`) ; ce que le vérificateur consulte : les valeurs structurées derrière ces textes.

Outils repris (enveloppes, paramètres et bornes inchangés, voir la section 3 du parent) : `chercher_formations`,
`chercher_masters`, `trouver_commune`, `lister_valeurs`. `lire_fiche` gagne un paramètre (section 4).

Outils nouveaux, signatures :

```python
TypeFormation = Literal["pass", "las", "licence", "but", "bts", "cpge", "cupge", "ifsi",
                        "diplome_sante", "ecole_ingenieur", "titre_pro"]   # liste de chercher_formations

class TrouverFormation(BaseModel):          # « le BUT info de Lens », « MP2I à Clemenceau », « l'IUT Lyon 1 »
    texte: str = Field(min_length=2, max_length=200)
    commune: str | None = Field(None, max_length=80)     # résolue par trouver_commune ; homonymes -> erreur qui les liste
    types: list[TypeFormation] | None = Field(None, max_length=11)
# rend : {"requete_normalisee": str, "nb_candidats": int, "tronque": bool,
#         "candidats": [{"id", "intitule", "etablissement", "commune", "type", "termes_trouves", "score"}]}  (au plus 10)

class Comparer(BaseModel):
    ids: list[str] = Field(min_length=2, max_length=5)   # uniques ; un id inconnu -> erreur qui le nomme
    champs: list[str] | None = Field(None, max_length=15)  # notions de la table `champ` ; défaut = l'essentiel (section 4)
# rend : {"formations": [{"id", "intitule", "etablissement", "commune", "type"}],
#         "champs": [notion], "valeurs": {id: {cle: {valeur, unite, statut, raison, portee, source_id, millesime}}}}
# mêmes notions et mêmes sessions pour toutes les formations ; une notion sans objet pour un espace (master contre
# post-bac) est rendue « sans objet », jamais omise.

class MettreAJourProfil(BaseModel):          # champs de la section 4 du parent ; None = inchangé
    statut: Literal["lyceen", "etudiant", "parent", "reorientation"] | None = None
    niveau_actuel: Literal["premiere", "terminale", "bac_obtenu", "bac+1", "bac+2", "bac+3", "bac+4", "bac+5"] | None = None
    voie_bac: Literal["generale", "sti2d", "st2s", "stmg", "stl", "std2a", "stav", "sthr", "s2tmd",
                      "professionnelle"] | None = None
    specialite_bac_pro: str | None = Field(None, max_length=80)      # « CIEL », « ASSP »...
    specialites: list[str] | None = Field(None, max_length=4)        # liste fermée des spécialités de terminale
    moyenne: float | None = Field(None, ge=0, le=20)
    moyenne_detail: str | None = Field(None, max_length=80)          # « 16 en maths »
    commune: str | None = Field(None, max_length=80)                 # résolue en code INSEE par trouver_commune
    mobilite_km: int | None = Field(None, ge=0, le=300)
    pret_a_partir: bool | None = None
    budget: Literal["serre", "moyen", "indifferent"] | None = None
    alternance: Literal["souhaitee", "indifferente", "exclue"] | None = None
    interets: list[str] | None = Field(None, max_length=10)          # chaque entrée <= 60 caractères
    a_eviter: list[str] | None = Field(None, max_length=10)          # exclusion, jamais inclusion
# rend : le profil complet. `formations_citees` n'est pas un paramètre : le pipeline y ajoute chaque id rendu par
# trouver_formation, lire_fiche ou comparer.
```

`trouver_formation`, règle écrite avant le code : texte et champs de la base passés en minuscules sans accents ni
ponctuation ; lettres et chiffres collés séparés (« lyon1 » lu « lyon 1 ») ; sigles dépliés par une table versionnée
(`src/v2/sigles.json`, chaque entrée avec sa source : IUT, INSA, UCA, UPS, UGA...) ; un sigle ambigu (UCA = Clermont
Auvergne ou Côte d'Azur) garde toutes ses lectures ; mots vides retirés ; score = part des termes de la requête trouvés
dans intitulé + établissement + commune + filière ; filtre `commune` et `types` appliqués avant le score ; au plus 10
candidats, ex æquo départagés par l'id. Zéro candidat : réponse vide avec les établissements et communes les plus
proches du texte, jamais une formation « au plus près ». Pas d'appel de modèle dans l'outil.

Profil (`src/v2/profil.py`) : même modèle Pydantic, gardé côté serveur le temps de la conversation, réinjecté au modèle
à chaque message. Pas de nom, pas d'e-mail, pas de lycée nominatif : `extra="forbid"` refuse tout champ hors liste.

## 4. L'essentiel de la fiche (`lire_fiche(id, detail=False)`)

**Mesure** (règle 13) : `python -m src.eval.essentiel_fiche`, zéro appel d'API, sortie commitée
`results/cerveau_etape3/essentiel_fiche.json`, relevée le 25/09/2026 sur la base de main (sha256 du fichier
`3c76e30a27ea...`, empreinte canonique `bfb26cdddfc6`).

Méthode : chaque chiffre attendu du banc vertical dont la fiche est dans la base C (`results/banc_e/exposition.json`)
est rattaché à la notion de la base qui le porte (table `CORRESPONDANCE` du script, écrite à la main), puis on lit la
fiche par `lire_fiche` (filtre « montré au modèle » de #189 compris).

| | nombre |
|---|---|
| chiffres attendus du banc vertical | 341 |
| hors base C | 18 |
| rendables (fiche dans la base) | 323 |
| rendus avec la même valeur (`egal`) | 269 |
| rendus avec une autre valeur (`ecart` : open data du banc contre page publique de #189, ex. places 117 contre 109) | 35 |
| dans la base mais masqués au modèle par #189 (`masque` : 8 candidats MonMaster phase principale, open data) | 8 |
| absents de la base (`absent` : 10 insertion de masters non collectée, 1 « classés » non affiché par la page) | 11 |
| banc lot 0 : chiffres attendus | **0** (le banc n'en porte aucun ; il ne peut pas servir à cette mesure) |

Contrôle de la table : 278 attendus ont au moins un champ de valeur égale dans leur fiche ; 269 le sont sur la notion
de la table (96,8 %). Les 9 autres sont des égalités fortuites sur une autre notion (ex. 19 % de bacs techno attendu,
20 % rendu, et 19 % de mentions AB). Témoin de hasard : confrontés à la fiche d'un autre attendu (graine 7), 32 des 323
attendus trouvent une valeur égale ; une égalité de valeur seule ne vaut donc pas rattachement, d'où la table.

Part cumulée par notion (sur les 304 attendus rendus, `egal` + `ecart`) :

| notion | attendus | part cumulée |
|---|---|---|
| taux_acces (dont 3 aux sessions 2023-2024) | 128 | 42,1 % |
| places | 125 | 83,2 % |
| repartition_admis_bac_techno | 11 | 86,8 % |
| repartition_admis_bac_pro | 10 | 90,1 % |
| candidats_ont_postule | 10 | 93,4 % |
| capacite_accueil (masters) | 8 | 96,1 % |
| part_neobacheliers | 4 | 97,4 % |
| candidats_ont_pu_recevoir_une_proposition | 3 | 98,4 % |
| part_mention_tb, part_mention_sans_mention | 2 + 2 | 99,7 % |
| voeux_phase_principale (2023) | 1 | 100 % |

**Seuil proposé : 95 % des attendus rendus**, atteint à la 6e notion. **Essentiel proposé (choix C1)** :

- les 6 notions du seuil, toutes sessions montrées : `taux_acces`, `places`, `capacite_accueil`,
  `repartition_admis_bac_techno`, `repartition_admis_bac_pro`, `candidats_ont_postule` ;
- `repartition_admis_bac_general`, pour que la répartition des admis par bac soit entière (sinon le modèle voit deux
  parts sur trois) ;
- pour les fiches santé, 3 notions de portée nationale, gardées pour le gate F et non pour le banc (F-HSAN-02 : « donner
  le chiffre NATIONAL en le disant national ») : `passage_mmopk_1_ou_2_ans_national` (47,5 %),
  `passage_pass_las_ensemble_national`, `sante.reforme_2027` ;
- toujours : l'identité de la formation (intitulé, établissement, type, statut, apprentissage, sélectivité, lien
  officiel, dernière session), ses lieux, la raison de tout « non disponible » sur une notion de l'essentiel, et la
  liste des notions non rendues (pour que le modèle sache qu'il peut demander `detail=True`).

Effet mesuré (même commande, les 3 945 fiches) : Parcoursup 43 valeurs en médiane aujourd'hui (max 77) contre 10 (max
13) ; MonMaster 18 contre 3 ; apprentissage 11 contre 1. Couverture : 292 des 304 attendus rendus (96,1 %), 292 des
323 rendables (90,4 %). Ce qui sort de l'essentiel et reste dans `detail=True` : part de néobacheliers, mentions,
propositions, boursiers, femmes, même académie, coût, insertion, capacités santé par université.

Le chiffre de 43 compte les entrées de `valeurs` rendues par `lire_fiche`, textes compris (coût en détails,
alternance, présence de la fiche en cours) ; les « 41 chiffres » de #189 comptent autrement (chiffres vus, script
`src/eval/concordance.py`). Les deux sont des médianes sur Parcoursup.

Ce que la mesure n'établit pas : l'insertion et le coût n'ont aucun attendu rendu dans le banc (insertion des masters
non collectée, coût jamais demandé en chiffre) ; leur place dans l'essentiel est une question de produit, pas de banc
(choix C2). L'apprentissage n'a aucun attendu : l'essentiel n'y garde que `places`.

## 5. « Rien de 2026 » contre la base actuelle

Décision de Matteo du 25/09 à 18h55 (Telegram 10773, relayée par Jarvis) : le modèle ne voit que la session 2025 ou
d'avant. Relevé sur la base de main (`lire_fiche` sur les 3 945 fiches, 25/09), quatre familles d'entrées la
contredisent aujourd'hui (les chiffres de page « session 2025, page relevée le 2026-09-25 » sont de 2025 : seule la
date du relevé est en 2026) :

| entrée | où | pourquoi elle existe |
|---|---|---|
| `capacite_accueil@2026` | 398 masters (disponible), montrée au modèle | #189 : la page MonMaster affiche la capacité de la campagne en cours ; `capacite_accueil@2025` n'est disponible que pour 82 masters, alors que l'open data 2025 (`capacite_campagne_2025`) existe pour les 480, masqué |
| `capacites_mmopk_*`, `sante.capacites_universite` | 183 fiches santé (panel de 10 universités), montrées | capacités d'accueil en 2e année de santé, « rentrée 2026 », pages des universités |
| `fiche_publique_annee_en_cours@2026` | les 3 945 fiches, montrée | présence de la formation sur la plateforme en cours (relevé du 25/09) ; pas un chiffre |
| `cout.*` (droits d'inscription, CVEC) | post-bac, montré | tarif de l'année universitaire 2026-2027 ; pas de l'open data Parcoursup |

`sante.reforme_2027` (texte de la réforme des études de santé, relevé le 23/09/2026) n'est pas une statistique de
2026 : il reste montré sauf avis contraire (C3).

Le v2 ne touche pas la base : il filtre dans `src/v2/outils.py`, et la règle est testée. Arbitrage : choix C3.

## 6. Le vérificateur (`src/v2/verificateur.py`)

- **Portée** (parent, section 6) : pourcentages, euros, places, extraits par la logique de
  `src/eval/battery/numbers.py` (unités `pct`, `eur`, `places`, tolérances du module). Durées, niveaux, dates : non
  contrôlés.
- **Adossé** : la valeur égale, à la tolérance, une valeur de même unité rendue par un outil pendant la conversation
  (tous les tours, tous les outils). Chaque chiffre adossé garde la liste de ses porteurs (id de fiche, clé, source) ;
  plusieurs porteurs = ambiguïté tracée, pas une erreur.
- **Chiffre de l'élève** (choix C4) : une valeur écrite par l'élève dans la conversation (« j'ai vu 6 % ») est acceptée
  si la réponse la reprend, tracée « dit par l'élève », jamais affichée avec une source.
- **Non adossé** : une réécriture, avec le message « ces chiffres ne sont dans aucun résultat d'outil : [liste].
  Retire-les, ou appelle l'outil qui les donne. » Le modèle peut appeler des outils dans ce qui reste des 6. Si le
  second brouillon garde un chiffre non adossé, **la phrase qui le porte est retirée** (découpe déterministe en
  phrases, ligne de tableau = une phrase) et l'incident est tracé (chiffre, phrase, tour). Si tout est retiré, la
  réponse devient un message fixe sans chiffre qui renvoie à la fiche officielle.
- Le vérificateur ne juge pas le sens (un chiffre juste attribué à la mauvaise formation passe) : c'est le rôle de
  `comparer`, du prompt et du juge. Il ne contrôle pas non plus les formations citées : le gate F le mesure (section 9).

## 7. Le prompt de conseiller v0

Texte joint : `docs/cerveau/etape3/prompt_conseiller_v0.txt` (versionné, `src/v2/prompt.py` le lit tel quel). Simple
par construction : les règles d'usage des outils de la section 3 du parent, la règle de clarification (section 5 du
parent), le traitement hors domaine (Q4), la lecture du taux d'accès, les chiffres nationaux, « rien de 2026 ». Pas
d'exemple de réponse, pas de gabarit de forme : c'est l'étape 4.

## 8. Code et tests (phase B)

- `src/v2/` : `pipeline.py`, `outils.py`, `profil.py`, `verificateur.py`, `prompt.py`, `sigles.json`.
- `src/eval/multiversion/versions/v2.py` : la version jouée par le lanceur, même interface que `prod.py`
  (`nom`, `fils`, `empreinte()`, `chauffer()`, réponse + trace). Empreinte = sha du prompt, du paquet `src/v2`, de la
  base et identifiants de modèles.
- Lanceur : banc `gatef` ajouté (`docs/cerveau/gate_f/requetes_gate_f.json`, sha fixé `5c78dc6e9001`, ses `tours`
  lus comme les `turns` des bancs) ; `zai-glm-5-3` ajouté à `PRICES` (section 9) ; rien d'autre ne change.
- `src/eval/multiversion/gate_f.py` : mesures déterministes du gate F (section 9).
- Tests : chaque outil avec ses bornes (valeur limite acceptée, valeur au-delà refusée avec valeurs proches) ;
  `trouver_formation` sur les 8 questions de la famille nom (formations attendues dans les 10 candidats) ; profil
  (`extra="forbid"`, fusion) ; plafond de 6 (un faux modèle qui demande 8 appels : 6 exécutés, 2 refusés, réponse
  finale sans outil) ; et **un test de sabotage par garantie** (règle 9, levier par variable
  `ORIENTIA_SABOTAGE_V2`) : un vérificateur qui laisse passer un chiffre inventé doit rougir ; un « essentiel par
  défaut » qui rend toute la fiche doit rougir ; un filtre « rien de 2026 » désactivé doit rougir ; une phrase non
  adossée gardée après réécriture doit rougir.
- Aucun test ne charge le `.env` ; les tests qui appellent un modèle utilisent un faux client.

## 9. Règle de décision, écrite avant le run (section 14.2 du parent)

**Bancs et instruments** : mêmes bancs, même lanceur, même juge que la référence figée. Vertical (57 conversations, 79
tours) ; lot 0 (60 conversations, 67 tours) ; gate F (30 questions, 32 tours). Juge `judge_v2` (Opus 5.5 effort low,
stdin, fiches de la page publique, consigne de nommage) sur le vertical ; mesures déterministes de l'étape 1
(critère 1, chiffres adossés, refus, latence, coût).

**Gate de l'étape 3 = gate F** (sections 8 et 9 du parent), tous requis :
1. fiches attendues rendues par les outils de la conversation ≥ 90 %, sur les familles recherche, nom, multi-tour
   (au tour 2) et honnêteté (déterministe : ids attendus contre ids rendus par les outils) ;
2. 0 formation citée hors des résultats d'outils : détecteur déterministe (intitulés et établissements de la base C
   écrits dans la réponse, contre les ids rendus dans la conversation), relu par le juge sur la règle écrite de chaque
   question ; le détecteur est livré avec son contrôle positif (une réponse qui cite une formation non rendue doit
   être comptée) ;
3. clarification : 5 sur 5 avec une orientation d'abord et au plus 2 questions (compte des phrases interrogatives,
   déterministe, plus verdict du juge) ;
4. chiffres affichés adossés : 100 % (vérificateur ; garantie structurelle, mesurée aussi a posteriori par le lanceur).

**Bancs, montrés contre la référence** (planchers de la section 8 du parent, requis à l'étape 4, rapportés ici) :
erreur de fait < 10 % et refus < 10 % (juge, vertical, avec intervalle de confiance ; aussi sur l'échantillon figé de
34 tours pour le côte à côte avec ChatGPT + recherche) ; critère 1 ≥ 85 % ; adossés 100 % ; latence p90 < 15 s.
Référence (juge corrigé, 25/09) : prod 31,6 % d'erreur de fait (25/79), 2,26 ; ChatGPT + recherche 0 % sur 34,
4,67. Le lot 0 est joué (mesures déterministes) ; le juger est le choix C6.

**Latence** : risque connu, non mesuré. GLM 5.3 au format C : 11,6 s médiane par tour au banc E ; une boucle à
plusieurs appels séquentiels peut dépasser 15 s au p90. Rapporté, pas corrigé à cette étape.

**Budget et coûts** (prix lus le 25/09/2026 à 17h18 UTC sur `https://docs.mistral.ai/models/zai-glm-5-3` et
`https://docs.mistral.ai/models/mistral-small-4-0-26-03`, texte de la page relevé par curl) : GLM 5.3 1,4 USD par
million de jetons en entrée (0,14 en cache), 4,4 en sortie ; Small 4 0,15 / 0,6. Le cache n'est pas compté (coût
surestimé, jamais sous-estimé).

Estimation, **supposée** : 0,03 à 0,08 USD par tour (0,0274 mesuré au banc E, format C, 91 % des tours avec au moins un appel
à `lire_fiche` ; la boucle en fera davantage, avec un contexte qui grandit), soit 5 à 15 USD pour les 178 tours. Pour la remplacer par
une mesure :

| palier | quoi | plafond Mistral | condition pour passer au suivant |
|---|---|---|---|
| 0 | essai à blanc : 3 conversations du gate F (une recherche, un nom, une clarification) | 0,50 USD | traces complètes, 0 panne, garanties vertes ; coût par tour relevé |
| 1 | gate F complet (32 tours) | 4 USD | projection des bancs = coût par tour mesuré x 146 tours ; si la projection + le dépensé dépasse 15 USD, arrêt et retour à Matteo |
| 2 | vertical + lot 0 (146 tours) | 15 USD cumulés | arrêt automatique du lanceur au plafond (réservation des conversations en vol, étape 1) |

Arrêts automatiques en plus du plafond : plus de 20 % de pannes sur les 10 premières conversations d'un palier ;
une garantie rouge (adossés < 100 %) à n'importe quel palier.

Ce qui est payant : les appels Mistral des paliers 0 à 2 (plafonds ci-dessus), dans l'enveloppe validée avec ce
contrat. Ce qui demande le go de Matteo au moment de le lancer : le juge (quota de l'abonnement), sur le vertical
(79 verdicts) et le gate F (32), soit 111 verdicts, comme les 113 du rejugement de la référence. Rien d'OpenAI.

Tout amendement de cette section se date avant la lecture des résultats qu'il concerne.

## 10. Choix soumis à Matteo

| # | Question | Options | Reco |
|---|---|---|---|
| C1 | Essentiel de `lire_fiche` | a) les 10 notions de la section 4 (seuil 95 % des attendus rendus) ; b) seuil 90 % : 4 notions (taux d'accès, places, répartition techno et pro), sans `candidats_ont_postule`, sans capacité des masters, sans les notions santé nationales ; c) garder tout (43 valeurs en médiane) | **a** : b retire les masters et casse F-HSAN-02, c est ce que Matteo a demandé de changer (10770-10771) |
| C2 | Coût et insertion dans l'essentiel | a) non, en `detail=True` ; b) oui (2 à 3 valeurs de coût + 1 ligne d'insertion) | **b pour l'insertion, a pour le coût** : l'insertion répond à « et après ? » (1 ligne en médiane), aucune mesure ne la demande mais la question revient dans les conversations ; le coût est de 2026-2027 (voir C3) |
| C3 | « Rien de 2026 » face à la base (section 5) | a) filtrer les 4 familles de la section 5 dans ce que voit le modèle, et montrer `capacite_campagne_2025` (open data 2025) à la place de la capacité 2026 des masters (elle remplace alors `capacite_accueil` dans l'essentiel) ; b) garder la capacité 2026 de la page MonMaster (règle #189 « la page publique ») et les capacités santé 2026, filtrer le reste | **a** : décision la plus récente (18h55) ; la règle #189 reste vraie pour 2025. Conséquence de a : plus aucun chiffre de coût visible, même en détail |
| C4 | Chiffre cité par l'élève | a) accepté s'il vient d'un message de l'élève, tracé « dit par l'élève », sans source ; b) traité comme non adossé | **a** : F-HSAN-02 et F-NINF-21 demandent de commenter le chiffre de l'élève |
| C5 | Route d'API `/v2/answer/stream` à cette étape | a) aucune route : v2 jouée par le lanceur seulement ; b) route présente, désactivée par défaut | **a** : zéro surface ajoutée à la prod tant que le v2 ne la bat pas ; la route vient avec la mise en prod |
| C6 | Juger le lot 0 | a) non : mesures déterministes seulement (la référence ne l'a pas jugé en judge_v2) ; b) oui : 67 verdicts de plus sur le quota | **a** : pas de point de comparaison jugé côté prod |

## 11. Ce que ce contrat n'établit pas

- Le coût par tour et la latence du v2 : supposés, mesurés au palier 0.
- Que GLM 5.3 appelle bien les outils nouveaux sans exemple : le banc E le montre pour `lire_fiche` seulement (91 % des
  tours avec appel), pas pour une boucle à 7 outils.
- Que la table `CORRESPONDANCE` couvre les bancs futurs : elle est écrite pour les 20 champs du banc vertical.
- Que le détecteur de formations citées (gate F, critère 2) voit tout : son contrôle positif est livré avec lui, ses
  angles morts (formation citée par un sigle ou un surnom) seront publiés avec le premier run.
