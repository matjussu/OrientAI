# Etat de l'art septembre 2026 pour la refonte du RAG OrientAI

Scout 08. Recherches effectuees le 05/09/2026. Environ 25 requetes WebSearch/WebFetch.

## Convention de fiabilite utilisee dans ce rapport

Chaque affirmation porte son niveau de preuve :

- **[P]** source primaire fetchee ce jour (doc editeur, page de prix editeur, annonce editeur, page officielle).
- **[S]** source secondaire fetchee (media, blog d'ingenierie identifiable).
- **[A]** agregateur de prix / blog SEO, non recoupe en source primaire. A traiter comme **non verifie** tant qu'on n'a pas ouvert la page de l'editeur. Beaucoup de ces sites sont eux-memes generes et se recopient entre eux : je les cite parce qu'ils donnent un ordre de grandeur, pas parce qu'ils l'etablissent.

Regle appliquee : aucun chiffre marque [A] ne doit servir seul a porter une decision de refonte. Les chiffres [A] sont la pour cadrer un budget, pas pour arbitrer.

---

## 1. Modeles disponibles en septembre 2026 pour la generation en francais

### 1.1 Lineup Mistral (etat au 05/09/2026)

Source primaire : docs.mistral.ai, page "Models overview", fetchee le 05/09/2026.
URL : https://docs.mistral.ai/getting-started/models/models_overview/

Modeles generalistes texte / multimodal listes **[P]** :

| Modele | Version | Positionnement annonce |
|---|---|---|
| Mistral Medium 3.5 | v26.04 | agentique, code, multimodal. Modele phare. |
| Mistral Small 4 | v26.03 | instruct + reasoning + code, hybride |
| Mistral Large 3 | v25.12 | multimodal, usage general |
| Ministral 3 14B / 8B / 3B | v25.12 | vision + texte, tiers edge |
| Z.ai GLM 5.2 | v5.2 | **modele tiers** heberge par Mistral, contexte 1M |

Modeles specialises **[P]** : OCR 4.1 / 4.0 / 3, Voxtral TTS et Voxtral Mini Transcribe 2 et Realtime (audio), Codestral v25.08 (code), **Codestral Embed v25.05 et Mistral Embed v23.12 (embeddings)**, Shieldstral 1.0 et Mistral Moderation 2 v26.03 (moderation), Leanstral 1.5 (preuves formelles).

**Constat structurant pour nous : la page officielle des modeles ne liste que deux modeles d'embedding, dont `mistral-embed` en version v23.12.** C'est-a-dire decembre 2023. Notre `mistral-embed-2312` n'est donc pas "un vieux modele qu'on aurait du mettre a jour" : c'est **le seul embedding texte generaliste que Mistral propose, et il n'a pas ete renouvele depuis presque trois ans** au 05/09/2026 **[P]**. Tous les concurrents cites en section 2 ont sorti au moins une generation depuis. C'est la mesure la plus directement actionnable de ce rapport.

**Magistral et Devstral : absents de la page overview du 05/09/2026 [P].** Un article secondaire affirme que Mistral Medium 3.5 est un modele fusionne qui "remplace Devstral 2 et Magistral" (letsdatascience, non date precisement) **[A]**. A verifier avant de citer : ce qui est etabli, c'est l'absence de la liste, pas la fusion.

Prix Mistral : **la page mistral.ai/pricing fetchee le 05/09/2026 ne rend pas son tableau au fetch [P partiel]**. Elle etablit seulement la structure : facturation par million de tokens, entree et sortie separees, **batch = -50 %**, **cache d'entree = jusqu'a -90 % sur les tokens d'entree repetes**, OCR facture aux 1000 pages, audio a la minute, APIs outils a l'appel. Elle donne un seul chiffre en exemple : "Mistral Large : 0,50 $/M in, 1,50 $/M out".

Chiffres agregateurs, **non verifies en source primaire [A]** (benchlm.ai, cloudzero, aipricing.guru, releves "septembre 2026") :

| Modele | in $/M | out $/M |
|---|---|---|
| Mistral Medium 3.5 | 1,50 | 7,50 |
| Mistral Large 3 | 0,50 | 1,50 |
| Mistral Small 4 | 0,15 | 0,60 |
| Mistral Small 3.2 | 0,08 | 0,20 |
| Mistral Medium 3 (notre modele actuel) | 0,40 | 2,00 |
| Codestral | 0,30 | 0,90 |
| Ministral 3 3B / 8B / 14B | 0,10 / 0,15 / 0,20 | idem |
| Codestral Embed | 0,15 | - |

Fenetre de contexte Mistral Medium 3.5 : **262 144 tokens** selon OpenRouter et Artificial Analysis **[A]**, avec tool use / function calling et entree image supportes **[A]**. Date de sortie annoncee 29/04/2026 **[A]**, coherente avec le tag officiel v26.04 **[P]**.

Sources : https://docs.mistral.ai/getting-started/models/models_overview/ , https://mistral.ai/pricing , https://benchlm.ai/mistral/api-pricing , https://openrouter.ai/mistralai/mistral-medium-3-5 , https://artificialanalysis.ai/models/mistral-medium-3-5

**Nouveaute Mistral la plus pertinente pour nous, et de loin (section 3 pour l'analyse).** Annonce primaire fetchee : https://mistral.ai/news/agentic-search/ , 20/08/2026 **[P]**.

Autres jalons Mistral juin-septembre 2026, via un agregateur de release notes **[A]**, URL https://releasebot.io/updates/mistral :
- 30/08/2026 OCR 4.1 en GA
- 20/08/2026 Agentic Search (confirme en primaire)
- 11/08/2026 **endpoints d'inference regionaux en GA** (Europe ou US au choix) + Priority Tier avec SLA
- 04/08/2026 Shieldstral, classifieur de securite open-weights Apache 2.0, tenant sur un seul GPU 16 Go
- 09/07/2026 Studio : gestion versionnee des prompts et skills, audit log, rollback
- 23/06/2026 OCR 4, 170 langues, auto-hebergeable en un conteneur

### 1.2 Alternatives proprietaires

**Anthropic. Source primaire fetchee le 05/09/2026 [P]**, https://platform.claude.com/docs/en/about-claude/pricing :

| Modele | in $/MTok | out $/MTok | batch in/out | cache hit |
|---|---|---|---|---|
| Claude Haiku 4.5 | 1 | 5 | 0,50 / 2,50 | 0,10 |
| **Claude Sonnet 5** | **2** | **10** | 1 / 5 | 0,20 |
| Claude Sonnet 4.6 | 3 | 15 | 1,50 / 7,50 | 0,30 |
| **Claude Opus 5** | **5** | **25** | 2,50 / 12,50 | 0,50 |
| Claude Fable 5.1 / Mythos 5.1 | 10 | 50 | 5 / 25 | 0,25 |

Trois points fermes et directement exploitables **[P]** :
1. **Le prix 2 $/10 $ de Sonnet 5 est devenu definitif.** La hausse a 3 $/15 $ prevue au 01/09/2026 n'aura pas lieu. La note de la doc le dit explicitement. Les agregateurs qui annoncent Sonnet 5 a 3 $/15 $ en septembre 2026 ont tort.
2. **Fenetre de 1M tokens au tarif standard sur Claude 4.6 et suivants**, caching et batch appliques sur toute la fenetre. Une requete de 900k est facturee au meme tarif unitaire qu'une de 9k.
3. **Data residency** : `inference_geo: "us"` applique un multiplicateur 1,1x sur Claude 4.6+. La Claude API premiere partie est **globale par defaut**. Il n'y a pas, dans cette page, d'option `inference_geo` UE documentee. Pour un argument de souverainete UE cote Anthropic, il faut passer par Bedrock ou Vertex en region UE, avec **+10 % pour un endpoint regional vs global** **[P]**.

Attention piege de coût **[P]** : "Claude 4.7 et suivants utilisent un nouveau tokenizer qui produit environ 30 % de tokens en plus pour le meme texte". Comparer les prix affiches entre Sonnet 4.6 et un modele 4.7+ sans corriger ce facteur fausse le calcul.

**OpenAI.** La page openai.com/api/pricing a rendu **HTTP 403** au fetch le 05/09/2026, donc **aucun chiffre OpenAI n'est etabli ici en primaire**. Agregateurs **[A]** : GPT-5.5 a 5 $/30 $, GPT-5.5 Pro a 30 $/180 $, GPT-5.6 Sol a 5 $/30 $, GPT-5.6 Terra a 2 $/12 $, gpt-5-mini a 0,25 $/2 $, gpt-5-nano a 0,05 $/0,40 $. Source : https://benchlm.ai/openai/api-pricing , https://www.morphllm.com/openai-api-pricing . **A revalider avant tout arbitrage budgetaire.**

Note importante pour notre eval : le juge du 05/09 a compare a "GPT-5.5". Si le prix reel de GPT-5.5 est 5 $/30 $, il coute environ **3x l'entree et 3x la sortie de Sonnet 5**, ce qui change l'arbitrage : le concurrent qui nous bat a 3,9/5 sans contexte n'est pas au meme point de la courbe prix/qualite que celui qui nous bat a 3,5/5.

**Google.** Aucun fetch primaire. Agregateurs **[A]** : Gemini 3.1 Pro a 2 $/12 $ avec surcharge 4 $/18 $ au-dela de 200k, contexte annonce 2M ; Gemini 3.6 Flash et 3.8 Flash a 0,75 $/3,75 $, contexte ~1,05M, avec passage annonce a 1,50 $/7,50 $ au 01/01/2027. Sources : https://benchlm.ai/google/api-pricing , https://openrouter.ai/google/gemini-3.6-flash

### 1.3 Open-weights auto-hebergeables, francais

Ce que je peux etablir en primaire ou quasi-primaire **[P/S]** :

- Scaleway sert deja en production, en region Paris, **`qwen3-embedding-8b` et `bge-multilingual-gemma2` a 0,10 EUR/M tokens d'entree** **[P]**, https://www.scaleway.com/en/pricing/model-as-a-service/ . Ces deux modeles sont precisement les deux candidats embeddings serieux pour le francais (section 2). Le fait qu'ils soient servis en serverless souverain a 0,10 EUR/M est le point le plus actionnable de toute la section.
- Meme page **[P]**, chat : glm-5.2 a 1,80 / 5,50 EUR/M, deepseek-v4-flash-0731 a 0,40 / 0,80 EUR/M (0,08 en cache), llama-3.3-70b a 0,90 EUR/M, mistral-small-3.2-24b a 0,15 / 0,35 EUR/M, qwen3.5-397b-a17b a 0,60 / 3,60 EUR/M. Palier gratuit de 1M tokens, batch -50 %.
- Meme page, **cout d'hebergement dedie [P]** : L4-24G a 0,93 EUR/h (~679 EUR/mois), L40S-48G a 1,72 EUR/h (~1255 EUR/mois), H100-80G a 3,40 EUR/h (~2482 EUR/mois), 8xH100-SXM a 30,06 EUR/h (~21 944 EUR/mois).

Lecture directe pour nous : **un reranker open-weights de 0,5B a 4B tourne confortablement sur un L4 a 679 EUR/mois**, et un embedding 8B sur un L40S. Un modele de generation de classe frontier ne tient pas dans ce budget. Donc, si on veut de la souverainete, elle est economiquement realiste sur **l'embedding et le rerank**, beaucoup moins sur la generation.

Le paysage open-weights de generation en 2026 (DeepSeek V4, Qwen3.x, Kimi K2.6/K3, GLM 5.x, Llama 4, gpt-oss-120b) n'est documente ici que par des blogs comparatifs **[A]** qui se contredisent sur les numeros de version. Deux elements meritent d'etre retenus malgre tout, parce qu'ils sont juridiques et pas de perf :
- **Llama 4 exclut les developpeurs bases dans l'UE du volet multimodal de sa licence** **[A]**. Si vrai, c'est un disqualifiant sec pour un projet qui vend de la souverainete. **A verifier dans le texte de licence avant toute decision.**
- gpt-oss-120b vise explicitement le creneau "un seul GPU 80 Go" **[A]**, donc ~2482 EUR/mois chez Scaleway en H100 dedie **[P pour le prix GPU]**.

Sources : https://wavect.io/blog/open-weight-llm-comparison-2026/ , https://spectrumailab.com/blog/best-open-source-ai-models-ranked-2026

### 1.4 Souverainete UE : ce qui est reellement disponible

- **Mistral : endpoints d'inference regionaux en GA depuis le 11/08/2026**, choix Europe ou US, presentes comme reponse directe aux exigences de residence des donnees et au RGPD **[A/S]**, avec partenaires industriels europeens cites (Amadeus, ASML, Capgemini, Caisse des Depots, CMA CGM). Sources : https://releasebot.io/updates/mistral , https://tech-insider.org/fr/mistral-shieldstral-regional-endpoints-2026/ . **Le fait est corrobore par deux sources independantes mais je ne l'ai pas ouvert sur mistral.ai : a confirmer en primaire avant de le mettre dans un pitch.**
- Nuance a assumer publiquement : **Mistral sert desormais des modeles tiers non europeens sur sa propre plateforme**, Z.ai GLM 5.2 figure dans la liste officielle des modeles **[P]**. La presse francaise a traite le sujet comme une inflexion de la promesse de souverainete **[S]** : https://www.epochtimes.fr/mistral-ai-ouvre-sa-plateforme-aux-modeles-chinois-un-virage-qui-redefinit-sa-promesse-de-souverainete-3331136.html . Un argumentaire "souverainete francaise" fonde uniquement sur "on utilise Mistral" est desormais attaquable. Ce qui reste solide, c'est "inference en region UE, sur infrastructure europeenne, avec residence des donnees contractuelle".
- **Scaleway** : Generative APIs serverless en region Paris, prix publics **[P]**.
- **OVHcloud AI Endpoints** : catalogue de 40+ modeles annonce prioritairement sur la confidentialite des donnees, tarification par tokens, Batch API a tarif reduit **[A]**, https://www.ovhcloud.com/en/public-cloud/ai-endpoints/ . Prix par modele non releves en primaire.
- **Anthropic** : pas d'`inference_geo` UE documente sur la premiere partie ; passer par Bedrock ou Vertex region UE, +10 % vs global **[P]**.

---

## 2. Rerankers et embeddings en 2026

### 2.1 Mistral a-t-il un endpoint rerank ?

**Reponse : non, aucun endpoint `rerank` n'apparait dans la liste officielle des modeles Mistral au 05/09/2026 [P]**, et deux requetes ciblees n'ont remonte aucune annonce Mistral d'un tel endpoint. Ce qui existe sous le nom "Mistral" cote rerank, ce sont des modeles **tiers** construits sur des bases Mistral : `nv-rerankqa-mistral-4b-v3` de NVIDIA (dont la variante `rerank-qa-mistral-4b` est **deprecatee au 24/08/2026** **[A]**), `rank1-mistral-2501-24b`, `first_mistral`, RankZephyr. Aucun n'est un produit Mistral.

Ce que Mistral propose a la place, et qui joue le meme role fonctionnel autrement : **Agentic Search** (section 3).

Sources : https://docs.mistral.ai/getting-started/models/models_overview/ , https://build.nvidia.com/nvidia/rerank-qa-mistral-4b

**Consequence directe : si on veut un reranker, il ne viendra pas de Mistral. Le choix se fait hors ecosysteme Mistral, ce qui a un cout de souverainete a moins de prendre un open-weights auto-heberge.**

### 2.2 Rerankers commerciaux

| Modele | Prix | Multilingue | Source |
|---|---|---|---|
| Cohere Rerank 4 Pro | 0,0025 $/recherche **[A]** | 100+ langues, cross-lingue dans un meme appel, JSON semi-structure **[A]** | https://openrouter.ai/cohere/rerank-4-pro , https://vercel.com/ai-gateway/models/rerank-v4-pro |
| Cohere Rerank 4 Fast | 0,002 $/recherche **[A]** | 100+ langues **[A]** | https://openrouter.ai/cohere/rerank-4-fast |
| Cohere Rerank 3.5 | 0,001 $/recherche **[A]** | | idem |
| Voyage rerank-2.5 | 0,05 $/M tokens, **200M premiers tokens gratuits** **[A]** | multilingue, contexte 32k, instruction-following **[A]** | https://docs.voyageai.com/docs/pricing |

Rerank 4 Pro et Fast sont sortis le 11/12/2025 **[A]**. Voyage rerank-2.5 le 11/08/2025 **[A]**.

Ordre de grandeur a retenir : a 0,0025 $ par recherche, **un rerank Cohere Pro sur 10 000 tours de conversation coute 25 $**. C'est negligeable devant le cout de generation. Le vrai cout d'un reranker n'est pas l'argent, c'est la latence et la dependance.

### 2.3 Rerankers open-weights

Chiffres **[A]** issus de comparatifs (futureagi, particula, localaimaster, mixedbread) :
- **bge-reranker-v2-m3** : donne comme "le bon defaut de production 2026" pour le triplet qualite / latence / licence. Multilingue, gratuit, auto-hebergeable a bas cout.
- **Jina reranker v3** : 81,33 % Hit@1 a 188 ms, contexte 131k, scoring listwise de 64 documents en un appel, seul "top-tier" sous 200 ms.
- **mxbai-rerank-v2 (1,5B)** : 8x plus rapide que bge-reranker-v2-gemma a precision superieure, licence permissive.
- **Qwen3-Reranker** en 0,6B / 4B / 8B, instructions personnalisables par langue et domaine, support 100+ langues, contexte 32k.

Sources : https://futureagi.com/blog/best-rerankers-for-rag-2026/ , https://particula.tech/blog/reranker-models-compared-cohere-voyage-jina-bge-latency-ndcg , https://www.mixedbread.com/blog/mxbai-rerank-v2 , https://qwenlm.github.io/blog/qwen3-embedding/

### 2.4 Embeddings meilleurs que mistral-embed sur le francais

Point de depart factuel : **`mistral-embed` est en version v23.12 [P]**, sans successeur generaliste dans le catalogue officiel.

Candidats, **[A]** sauf mention :
- **bge-multilingual-gemma2** : donne comme etat de l'art sur **FR-MTEB**, avec des resultats particulierement bons en retrieval. C'est le seul modele que les sources associent explicitement au benchmark **francais**. Et il est servi par **Scaleway en region Paris a 0,10 EUR/M [P]**. Combinaison rare : bon en francais, souverain, et pas cher.
- **Qwen3-Embedding-8B** : 70,58 sur MTEB multilingue, no.1 au 05/06/2025, contexte 32k, 100+ langues. Egalement servi par **Scaleway a 0,10 EUR/M [P]**.
- **Cohere embed-v4** : 0,12 $/M texte, 0,47 $/M image, contexte 128k, 1024 dims avec sortie configurable de 256 a 1536, formats int8/binary. 100+ langues.
- **Voyage-3.5 / voyage-4 famille** : 200M premiers tokens gratuits sur voyage-4-large, voyage-4, voyage-4-lite, voyage-context-4.
- Etat de l'art annonce mi-2026 : KaLM-Embedding-Gemma3-12B no.1 MMTEB, Microsoft Harrier-OSS-v1 a 74,3 MTEB v2, Jina v5-text a 71,7, Gemini Embedding 2.

Sources : https://modal.com/blog/mteb-leaderboard-article , https://app.ailog.fr/en/blog/news/embedding-models-2026 , https://zc277584121.github.io/rag/2026/03/20/embedding-models-benchmark-2026.html , https://docs.cohere.com/docs/cohere-embed , https://docs.voyageai.com/docs/pricing

**Avertissement qui compte plus que le classement.** Un travail de 2026 sur les documents financiers conclut que **les classements MTEB/BEIR ne predisent pas la performance de retrieval dans un domaine donne** **[A]**, https://arxiv.org/pdf/2604.01733 . Nos 52 000 fiches Parcoursup/ONISEP/RNCP sont un domaine, avec un vocabulaire ferme (mentions, codes, attendus, taux d'insertion). **Le classement MTEB-fr sert a choisir les 3 candidats a tester, pas a choisir le gagnant.**

---

## 3. Architectures RAG agentiques pour un assistant conseil sur base structuree

### 3.1 Ce qui est etabli

**a) La qualite du retrieval domine la qualite de generation, et c'est ce qui rend notre mesure du 05/09 contre-intuitive.** Le consensus 2026 rapporte est que "la qualite du retrieval compte bien plus que la qualite de generation ; le chunking pauvre et le filtrage de pertinence faible causent plus d'echecs que le LLM lui-meme" **[A]**, https://futureagi.com/blog/rag-architecture-llm-2025/ . **Or notre mesure dit l'inverse** : Sonnet 5 avec NOS fiches monte a 3,3 contre 2,0 pour notre pipeline complet. Deux lectures possibles, et seul un test chez nous tranche : soit notre generation est vraiment le goulot (ce que la mesure suggere), soit le juge note la **forme du conseil** plutot que l'exactitude des references, et un modele plus fort gagne des points sur la redaction sans que le retrieval bouge. **Cette ambiguite doit etre levee avant de depenser un euro de refonte.**

**b) Le pipeline de reference 2026 est stable et il n'est pas agentique.** La recommandation de production convergente : retrieval hybride, top-100, deduplication MMR des chunks quasi-identiques, reranking cross-encoder, top-5 a top-10 vers le LLM **[A]**, https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026 . Nous avons deja hybride + RRF. Il nous manque exactement **le MMR et le reranker**, c'est-a-dire les deux etages centraux.

**c) Le reranker cross-encoder est le plus gros gain unitaire mesure.** "Le reranker cross-encoder apporte la plus grande amelioration unique", avec un MRR@3 passant de 0,433 a 0,605 **[A]**. Sur WANDS, un hybride regle atteint 0,7497 nDCG contre 0,6983 pour BM25 seul et 0,6953 pour le vectoriel seul, soit +7,4 % **[A]**. Sur texte+tableaux, hybride RRF + rerank neuronal donne Recall@5 = 0,816 **[A]**. Sources : https://arxiv.org/pdf/2604.01733 , https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026

**d) Le query rewriting et la decomposition ont un gain publie et un cout connu.** Reecriture vers une forme "retrieval-friendly" plus longue, avec synonymes et expansion d'entites, et decomposition en 2 a 4 sous-requetes. Les etudes multi-hop sur HotpotQA et MuSiQue rapportent des gains de rappel "de quelques points a des dizaines de points, au prix d'un appel LLM supplementaire par tour" **[A]**, https://futureagi.com/blog/agentic-rag-systems-2025/ . Pour nous, la decomposition est directement pertinente : "je veux faire du droit a Lyon mais je ne sais pas si mon dossier passe" contient au moins trois faits a retrouver separement.

**e) Mistral Agentic Search : le seul chiffre spectaculaire de 2026 avec une source primaire.** Annonce du 20/08/2026 **[P]**, https://mistral.ai/news/agentic-search/ . Cinq operations exposees au modele : `search`, `open`, `navigate`, `read`, `grep`. Le modele inspecte, affine sa recherche, ouvre, navigue vers une section, lit la source, puis repond. Resultats primaires :
- FinanceBench, 368 depots SEC, 150 questions : **26,7 % a 86 % de justesse pour Mistral Medium 3.5**, soit +47,3 points en search-only ; **p90 de latence 255 s a 154 s** ; **-23,9 % a -33,7 % de tokens**.
- OfficeQA Pro, 696 bulletins du Tresor, 133 questions : **+45,6 points** (6,3 % a 51,9 % pour GLM-5.2).
- Disponible via **Mistral Search Toolkit** (integration custom, cloud ou on-prem) et via **Libraries** (cle en main dans Studio et Vibe). **Prix non communique dans l'annonce [P].**

Ce chiffre est important **et il faut le lire avec prudence** : FinanceBench, ce sont des documents de ~147 pages ou l'information est enfouie. Le gain de 26,7 a 86 mesure surtout la capacite a **naviguer dans un document long**. Nos fiches formation sont courtes et structurees. **Rien ne garantit que ce gain se transporte chez nous, et beaucoup suggere que non.** En revanche, le fait que la latence p90 **baisse** et que les tokens **baissent** en passant a l'agentique contredit l'objection habituelle de cout, et ca, c'est transposable.

**f) Le routage lookup structure vs semantique est un pattern etabli.** Un agent coordinateur en premiere etape route vers base relationnelle (calculs precis, agregats, filtres) ou vers vectoriel (semantique) **[A]**, https://www.gigaspaces.com/blog/text-to-sql-vs-rag-for-structured-data . Regle donnee : "pour toute tache de calcul ou de reporting precis, text-to-SQL est plus adapte que RAG". Pour nous c'est central : **"les BUT informatique a moins de 50 km de Rennes avec un taux d'acces superieur a X" est une requete SQL, pas une requete d'embedding.** Aujourd'hui on la traite en semantique, donc mal, par construction.

### 3.2 Ce qui est a la mode et qu'il faut manier avec precaution

- **Self-RAG (Asai et al., 2023) et FLARE (Jiang et al., 2023)** sont les references canoniques du retrieval dans la boucle **[A]**. Ce sont des papiers de 2023 : trois ans en 2026, ce ne sont plus des nouveautes, ce sont des classiques. Self-RAG integre l'evaluation dans le modele via des reflection tokens ; Corrective RAG ajoute un evaluateur externe avec trois chemins correctifs.
- **Le sur-retrieval est le mode d'echec numero un rapporte en production** : "l'agent boucle, appelle le retriever 8 a 12 fois pour une question que deux retrieves auraient reglee, brule des tokens et de la latence, et sort souvent une **moins bonne** reponse finale parce que le generateur est noye" **[A]**. Regle qui en decoule et qui est unanime : **plafonner durement le nombre d'iterations**.
- **Budget latence a assumer** : chaque tour de retrieval coute 200 a 500 ms de recherche vectorielle plus 300 a 800 ms de reranking ; trois tours plus trois appels LLM = **5 a 15 secondes** sur les questions complexes **[A]**, https://futureagi.com/blog/rag-architecture-llm-2025/ . Pour un lyceen sur mobile en periode de voeux, 15 secondes est un abandon. Notre mono-passe actuel est un choix de latence, pas seulement une paresse d'architecture. **Toute refonte agentique doit budgeter la latence comme une contrainte produit, pas comme un detail.**
- **HyDE** : je n'ai trouve aucune source 2026 qui le mesure comme gagnant. Il n'apparait dans aucun des pipelines de production recommandes que j'ai lus. **Statut : a la mode en 2023-2024, absent des recommandations 2026. Ne pas en faire un chantier.**

### 3.3 Memoire de profil et clarification

- **Memoire.** L'architecture de production 2026 decrite : hybride vectoriel + graphe, **profils utilisateurs ecrits de facon asynchrone pour ne pas bloquer la reponse**, et conformite RGPD / chiffrement / droit a l'effacement traites des le premier jour **[A]**, https://supermemory.ai/blog/how-to-make-ai-remember-user-preferences-across-conversations/ . Point technique interessant pour nous : **HiMeS** (arXiv 2601.06152) utilise la memoire courte pour compresser l'historique en une requete raffinee, et la memoire longue (profil persistant) **pour re-ranker les chunks retrouves**. C'est exactement notre besoin : le profil d'un lyceen (filiere, notes, mobilite geographique, contraintes financieres) devrait ponderer le classement des formations, pas juste habiller le prompt. Autres references 2026 : PERMA (arXiv 2603.23231), Mem-PAL (arXiv 2511.13410), STALE sur l'obsolescence des souvenirs (arXiv 2605.06527), "Learning User-Aware Recall" (arXiv 2607.00017).
- **Clarification.** Litterature ancienne et continue (Qulac, ClariQ), reactivee par les LLM : "Asking Clarifying Questions for Preference Elicitation With Large Language Models", Google Research, arXiv 2510.12015. Constat honnete des auteurs : **generer de bonnes questions de clarification sequentielles a travers plusieurs domaines reste un probleme ouvert**. Statut : etabli comme utile, non resolu comme technique. Pour nous, la version pauvre et sure (une seule question de clarification, declenchee sur regles explicites du type "ni ville ni domaine detectes") est bien plus defendable qu'un modele de clarification apprise.

---

## 4. Evaluation : pratiques 2026 (section courte, comme demande)

- **Calibration obligatoire contre l'humain.** Pratique de reference : echantillonner **100 a 300 traces de production**, faire annoter par **2 a 3 humains** sur la rubrique, calculer le kappa de Cohen inter-annotateurs. **kappa > 0,6 acceptable, > 0,8 fort.** Puis kappa juge-vs-humain sur la meme echelle : **si < 0,5, c'est la rubrique qu'il faut reecrire, pas le juge qu'il faut changer** **[A]**, https://www.openlayer.com/blog/llm-as-judge-evaluation-guide
- **Quatre biais a neutraliser** : position (passer les deux ordres et moyenner), verbosite (normaliser par la longueur), **auto-preference (prendre un juge d'une autre famille de modele)**, biais de famille **[A]**. Notre eval du 05/09 utilise un juge Opus qui note entre autres du Claude Sonnet 5 : **c'est exactement le cas d'auto-preference**. Le 3,3 de Sonnet 5 avec nos fiches est potentiellement gonfle. A re-mesurer avec un juge d'une autre famille avant de conclure que "la generation est la premiere cause".
- **Deflation du kappa** : un travail a grande echelle mesure un ecart universel de **33,8 a 41,3 points** entre accord brut et kappa de Cohen sur MT-Bench **[A]**, https://arxiv.org/pdf/2606.19544 . Un "les juges sont d'accord a 80 %" ne vaut donc rien sans kappa.
- **Outils** : Ragas (metriques sans reference, faithfulness et relevance), ARES (juges legers entraines), RAGChecker (diagnostic), et cote plateformes DeepEval, Phoenix, Braintrust, Galileo Luna-2, Openlayer, FutureAGI **[A]**. Je n'ai **pas** trouve de source confirmant l'existence d'un "Ragas 0.4" : **non verifie**.
- **Personas simules vs vrais utilisateurs** : aucune source solide trouvee tranchant la question pour un assistant conseil. **Non etabli.** Ce que la litterature dit en revanche, c'est qu'un juge doit etre calibre sur des **traces de production**, pas sur des questions synthetiques.

---

## 5. Concurrents directs et sources de donnees

### 5.1 Le vrai concurrent est ChatGPT, et c'est mesure

Le fait le plus important de cette section, avec source secondaire fetchee **[S]** citant une enquete Diplomeo pour la session Parcoursup 2026 :

- **61 % des lyceens de terminale utilisent l'IA pour gerer Parcoursup.** 35 % pour obtenir des reponses rapides, 28 % pour peaufiner leurs candidatures.
- **23 % font davantage confiance a l'IA qu'a Parcoursup lui-meme.** 25 % lui font plus confiance qu'aux sites d'information, 22 % qu'aux centres et conseillers d'orientation, 17 % qu'aux enseignants, 14 % qu'a leurs proches.
- Enquete complementaire EDHEC / JobTeaser / Kantar, **2 578 etudiants et jeunes diplomes**, terrain aout-octobre 2025, publiee le **03/02/2026** : **48 % des etudiants font confiance a l'IA pour leurs choix d'etudes**.

Sources : https://www.vu-du-web.com/intelligence-artificielle/lyceens-ia-2025-2026-usage-orientation/ **[S, fetchee]** , https://diplomeo.com/actualite-enquete_orientation_2026_diplomeo **[S]**

Lecture pour OrientAI : **notre concurrent n'est pas une edtech, c'est ChatGPT en usage direct, deja adopte par 61 % de la cible.** Et notre eval du 05/09 dit que GPT-5.5 **sans aucun contexte** nous bat 3,9 contre 2,0 sur la pertinence des references. Autrement dit : **le produit gratuit que le lyceen utilise deja fait mieux que nous sur le critere ou nos 52 000 fiches etaient censees etre notre avantage.** C'est le chiffre a mettre au centre de la decision de refonte.

### 5.2 Officiel

- **Parcoursup a bien un assistant conversationnel**, developpe sous la supervision du ministere de l'Enseignement superieur et de la Direction du numerique pour l'education (DNE) **[A]**, https://www.digischool.fr/lemag/parcoursup/parcoursup-2026-lintelligence-artificielle-peut-elle-vraiment-vous-aider-a-choisir-votre-orientation/ . **Je n'ai pas pu confirmer en source primaire** : parcoursup.gouv.fr/services-numeriques rend un **HTTP 403** au fetch. **A verifier manuellement dans un navigateur : c'est un point competitif structurant.**
- **Avenir(s)** (ONISEP) : plateforme d'accompagnement a la reflexion d'orientation, connexion EduConnect/Educagri, contenus metiers et temoignages **[S]**, https://www.onisep.fr/avenir-s
- **MonProjetSup** : outil de la plateforme Avenir(s), de la seconde a la terminale. Trois etapes : profil (situation, scolarite, interets, metiers), **suggestions personnalisees de formations issues de Parcoursup**, ajout de favoris avec niveau d'ambition. Objectif affiche : **elargir l'eventail des choix et reduire l'autocensure** **[S]**, https://www.onisep.fr/orientation/monprojetsup-bien-preparer-son-orientation-post-bac . C'est fonctionnellement le concurrent public le plus proche de notre coeur de produit. Il est gratuit, institutionnel, et adosse aux donnees Parcoursup.
- Une source mentionne un outil "Avenir" developpe avec l'ONISEP "encore en phase de developpement" et une plateforme tierce **oria-avenir.com** presentee par son createur comme un "copilote qui aide a choisir sa voie" **[A]**.
- Cadre d'usage de l'IA publie par l'Education nationale en **juin 2025** : ne jamais transmettre bulletins scolaires ni informations personnelles a ces outils, verifier systematiquement sur les sites officiels **[A]**. **A lire en entier : c'est le cadre de conformite qui s'applique a nous, et un argument produit si on le respecte mieux que ChatGPT.**

### 5.3 Startups francaises

- **Hello Charly** : chatbot d'orientation, **660 000 jeunes accompagnes** depuis la creation **[S]**, https://www.campusmatin.com/numerique/edtechs/ces-quatre-edtechs-veulent-depoussierer-l-orientation.html . **Gratuit pour les particuliers** : parcours d'exploration, echanges avec le chatbot, decouverte des metiers, mise en relation avec les entreprises. **Modele economique B2B/B2G** : partenariats avec collectivites, etablissements scolaires, acteurs institutionnels de l'insertion, appels a projets regionaux, et financement d'Etat via le PIC (programme d'investissement dans les competences) **[S]**. Partenariat IBM SkillsBuild pour des formations certifiantes gratuites en IA, cybersecurite, cloud **[S]**, https://fr.newsroom.ibm.com/Hello-Charly-et-IBM-renforcent-leur-engagement-pour-linclusion-numerique-et-proposent-une-formation-gratuite-a-lintelligence-artificielle
- **Wilbi** : decouverte de metiers par video, **250+ metiers**, mecanique de swipe et d'abonnement a des metiers, stories immersives. Gratuit **[S]**. Partenariat Wilbi x Hello Charly **[S]**.
- **Diagoriente** : **start-up d'Etat**, plateforme gratuite, cible jeunes, seniors, sportifs en reconversion **[S]**.
- **Impala** : orientation pour colleges et lycees et etablissements, **developpe des algorithmes IA pour personnaliser les suggestions**, 2 tours de financement, montants non divulgues, investisseur cite Newfund **[A]**.
- **Studizz** : orientation + chatbot + analyse de CV, depuis 2012 **[A]**.
- **Thotis** : media de reference sur l'orientation, application "Thotis IA" pour lyceens, etudiants, parents et enseignants **[A]**.

**Constat de marche a assumer : le prix de reference du marche francais de l'orientation pour le particulier est zero.** Hello Charly, Wilbi, Diagoriente, MonProjetSup, Avenir(s) sont tous gratuits pour l'utilisateur final, finances par le B2B, le B2G ou l'Etat. **Aucune source trouvee ne donne un tarif grand public.** Toute monetisation B2C d'OrientAI se heurte a ca. Le modele viable observe est B2B/B2G : etablissements, collectivites, regions, PIC.

**Sur la qualite de ces concurrents : je n'ai trouve aucune evaluation independante, aucun benchmark public, aucune mesure de pertinence pour aucun d'entre eux.** C'est une opportunite (personne n'a publie de mesure, on peut etre les premiers) et un piege (personne ne sait qui est bon, donc la qualite ne se vend pas toute seule).

### 5.4 Donnees ouvertes officielles et leur fraicheur

- **Cartographie des formations Parcoursup**, data.gouv.fr : couvre 2020 a **2026**, **mise a jour quotidienne**, les donnees 2026 completees progressivement jusqu'au **15 janvier** **[S]**, https://www.data.gouv.fr/datasets/cartographie-des-formations-parcoursup . C'est le jeu le plus frais de tous.
- **Portail data MESRE** : https://data.enseignementsup-recherche.gouv.fr/pages/parcoursupdata/ **[S]**
- **InserSup** : systeme d'information de la sous-direction des systemes d'information et des etudes statistiques (SIES) du MESR **[S]**.
- **MonMaster** : recense tous les masters nationaux, procedures, **nombre de places, criteres de selection, calendrier** ; collecte les candidatures depuis 2023, campagne annuelle de mars a septembre **[S]**, https://en.wikipedia.org/wiki/Monmaster.gouv.fr
- **API ONISEP, source primaire fetchee [P]**, https://opendata.onisep.fr/3-api.htm :
  - base : `https://api.opendata.onisep.fr/api/1.0/`
  - **cle API obligatoire**, quotas journaliers modifiables a tout moment par l'ONISEP, header `Daily-Remaining-Request`
  - **jetons valides 24 h**, a regenerer
  - JSON, filtrage, tri, pagination
  - licence **ODbL**
  - **recommandation officielle de l'ONISEP : ne pas appeler l'API en direct de facon repetee, mais faire un dump unique hebdomadaire ou quotidien vers une base locale, "les jeux de donnees se mettant a jour mensuellement ou sporadiquement"**.

Ce dernier point **[P]** valide notre architecture d'ingestion par lots, et il pose une contrainte de fraicheur : cote ONISEP, le frais c'est le mois, pas le jour. Cote Parcoursup, c'est le jour. **Un assistant qui melange les deux sans dater ses fiches affirmera des choses fausses en periode de voeux.** La licence ODbL impose par ailleurs l'attribution et le partage a l'identique des bases derivees : **a faire verifier juridiquement avant toute commercialisation.**

---

## 6. Synthese : cinq choix recommandes, trois incertitudes

**Les cinq choix, avec l'argument mesure de chacun.**

1. **Remplacer `mistral-embed-2312` par `bge-multilingual-gemma2` servi chez Scaleway Paris a 0,10 EUR/M.** Argument : le catalogue officiel Mistral du 05/09/2026 ne liste qu'un embedding generaliste, en version **v23.12** **[P]** ; bge-multilingual-gemma2 est le seul modele que les sources associent explicitement a l'etat de l'art **FR-MTEB** **[A]** ; et il est disponible en region Paris a prix public **[P]**, donc sans perdre l'argument souverainete.
2. **Ajouter un reranker cross-encoder entre le RRF et la generation, avec `bge-reranker-v2-m3` auto-heberge sur un L4 a 679 EUR/mois.** Argument : c'est le plus gros gain unitaire mesure d'un pipeline RAG (MRR@3 de 0,433 a 0,605, hybride+rerank a Recall@5 0,816) **[A]**, c'est l'etage exact qui manque au pipeline de reference 2026 **[A]**, Mistral n'offre aucun endpoint rerank **[P]**, et le cout GPU est publie **[P]**.
3. **Router les requetes filtrables vers du SQL au lieu du semantique.** Argument : "pour toute tache de calcul ou de reporting precis, text-to-SQL est plus adapte que RAG" **[A]** ; nos fiches portent des champs structures (ville, type, domaine, places, taux d'acces, taux d'insertion) qu'un embedding ne peut pas filtrer correctement par construction. C'est le changement au meilleur rapport gain/risque parce qu'il ne touche pas a la latence.
4. **Ajouter une passe de decomposition de requete, plafonnee a 2 sous-requetes et 2 tours de retrieval maximum.** Argument : gains de rappel publies "de quelques points a des dizaines de points" pour un appel LLM supplementaire **[A]** ; et le plafond est impose par le mode d'echec dominant en production, le sur-retrieval qui degrade la reponse finale **[A]**, plus le budget latence de 5 a 15 s a trois tours **[A]**, incompatible avec un lyceen sur mobile.
5. **Refaire l'eval avant la refonte, avec un juge d'une autre famille que les modeles evalues et une calibration humaine.** Argument : notre juge Opus a note du Claude Sonnet 5, c'est le cas d'auto-preference que la litterature 2026 demande explicitement de neutraliser **[A]** ; et la calibration exige 100 a 300 traces, 2 a 3 annotateurs, kappa > 0,6 inter-annotateurs et > 0,5 juge-humain **[A]**. Sans ca, le 2,0 contre 3,9 oriente une refonte entiere sur un instrument non calibre.

**Les trois incertitudes que seul un test chez nous peut trancher.**

1. **La generation est-elle vraiment la premiere cause, ou le juge note-t-il la forme du conseil ?** Sonnet 5 + nos fiches = 3,3, ce qui accuse la generation ; mais le consensus 2026 dit que le retrieval domine **[A]**, et notre juge est de la meme famille que le modele qui gagne. Test : reprendre les 67 tours avec un juge non-Claude, et separer la note "exactitude des references" de la note "qualite du conseil".
2. **Le gain d'Agentic Search se transporte-t-il a des fiches courtes ?** Les chiffres primaires (26,7 % a 86 %) portent sur des documents SEC de ~147 pages ou l'information est enfouie **[P]**. Nos fiches font quelques centaines de mots et sont deja structurees. Le mecanisme mesure (naviguer dans un long document) n'existe pas chez nous. Test : rejouer 20 tours avec le Search Toolkit sur notre index et comparer, avant d'engager quoi que ce soit.
3. **Le classement MTEB-fr predit-il quoi que ce soit sur notre corpus ?** Un travail 2026 mesure explicitement que MTEB/BEIR ne predit pas la performance en domaine **[A]**. Notre domaine a un vocabulaire ferme et beaucoup de quasi-doublons (des centaines de "BUT informatique" presque identiques). Test : construire 50 paires question/fiche-attendue depuis nos vrais logs et mesurer Recall@10 des trois candidats embeddings sur ce jeu, pas sur MTEB.

---

## Annexe : ce que je n'ai pas pu etablir

A traiter comme **non verifie**, et a ne pas citer au present de l'indicatif :

- Prix officiels Mistral par modele : page pricing fetchee mais tableau non rendu. Tous les chiffres Mistral de ce rapport sont d'agregateurs.
- Prix officiels OpenAI : **HTTP 403** sur openai.com/api/pricing.
- Prix officiels Google Gemini : aucun fetch primaire.
- Existence et perimetre exact du chatbot officiel Parcoursup : **HTTP 403** sur parcoursup.gouv.fr/services-numeriques. A ouvrir a la main.
- Endpoints regionaux Mistral du 11/08/2026 : deux sources secondaires concordantes, aucune primaire mistral.ai.
- Exclusion des developpeurs UE par la licence Llama 4 : une seule source agregateur. A lire dans le texte de licence.
- "Ragas 0.4" : aucune trace. Version non confirmee.
- Fusion Magistral/Devstral dans Medium 3.5 : absents du catalogue officiel, mais la fusion elle-meme n'est affirmee que par un blog.
- Tarifs grand public des concurrents francais : aucun trouve, parce que tous semblent gratuits pour le particulier. Absence de preuve, pas preuve d'absence.
- Toute mesure independante de qualite d'un concurrent francais : aucune n'existe publiquement a ma connaissance apres recherche.
