# Point de reprise OrientAI, ecrit le 05/09/2026 (Jarvis)

A lire en premier par quiconque reprend le projet (Matteo, Ella, Claudette, Jarvis apres /clear).
Ce fichier dit ce qui est etabli, ce qui est perime, ou vit chaque chose, et par quoi on commence.

## 0. Lot 0 livre le 23/09/2026 (Claudette, ordre 2026-09-23-0817)

Le banc est versionne dans `src/eval/battery/` (README dans ce dossier). Une commande :
`python -m src.eval.battery bench --tag <nom> --systems local,mistral_large_norag`. Chaque passage
ecrit `results/battery/<tag>/` avec un manifeste (commit, sha de la batterie et du corpus, modeles,
couts). Les scripts de ce dossier (`run_battery.py`, `judge.py`, `aggregate.py`, `spike_agent.py`,
`smoke.py`, `battery.json`) y ont ete deplaces ; les runs bruts du 05/09 restent ici, dans `runs/`.

Mesures du 23/09 (traces : `results/battery/2026-09-23_lot0/REPORT.md` et `manifest.json`) :

| systeme | moy. 4 criteres | refus | err. fact. (juge) | chiffres adosses a une fiche (temoin de hasard) |
|---|---|---|---|---|
| local (prod) | 1,99 | 33 % | 24 % | 58 % (38 %) sur 438 chiffres |
| mistral-large-2512 sans fiche | 3,20 | 0 % | 94 % | 0 % par construction, 805 chiffres |

- **local = la prod** : empreinte de provenance identique a `/health` le 23/09 a 06:49Z (prompt
  `601adcee86b9`, corpus `2e4276e6155b`, index `8c91dfcf5323`, modeles epingles).
- **Delta local contre 05/09 (2,04) : -0,06, du bruit.** Tours apparies : IC95 [-0,14 ; +0,03],
  59 tours sur 67 a 0,25 pres alors que 66 reponses sur 67 ont change (temperature 0,3). Le drapeau
  `erreur_factuelle` du juge est instable d'un passage a l'autre (11 puis 16 tours, 7 en commun) :
  ne pas conclure sur l'ecart d'un seul passage.
- **Mistral Large sans donnees** : mieux note que le produit servi (3,20) mais le juge releve une
  erreur factuelle sur 94 % des tours, et aucun chiffre n'est montrable. Ses reponses font 604 mots
  en mediane (le prompt en demande 250 a 450) : plus de faits exposes au juge.
- **Controle des chiffres (nouveau)** : part des chiffres cites presents dans une fiche que le
  systeme a exposee, comparaison typee (%, EUR, places), toujours publiee avec son temoin de hasard.
  Sur les runs du 05/09 : local 61 % (32 %), claude_ctx 80 % (28 %), agent_sonnet 42 % (13 %),
  agent_mistral 63 % (21 %), GPT et Sonnet sans fiche 0 % (`results/battery/2026-09-05_runs-jarvis/`).
- **Juge** : les 8 verdicts manquants du 05/09 etaient des JSON tronques (plafond de 1 200 tokens) ;
  corrige a 4 000.

Set de pertinence (`scripts/relevance_set/`, `STATE.md` y dit tout) :
- **`eval_retrieval.py` vit dans `scripts/relevance_set/eval_retrieval.py`**. Il venait du WIP `c7402d3`
  et n'etait pas sur main avant ce lot : le RAPPORT le citait sans chemin.
- La cle d'identite est corrigee (position dans `formations.json`, sha du corpus verifie). Le bug
  touchait les modes dense ET bm25 du miner. Les 1 172 references des 135 labels migrent, 0 perdue.
- **recall@10 = 0,419 en raw, 0,616 en serving** (recall@5 : 0,314 et 0,547), sur 86 questions
  scorables. **Ce sont des bornes basses** : 49 % du pool re-mine n'a jamais ete juge. L'ancienne cle
  aurait rendu 0,198 en raw, et non 0 comme l'ecrivait le RAPPORT l.112.
- **Pas de recall sur golden_qa** : ses 676 entrees n'ont aucune verite terrain de pertinence
  (question et reponse, aucun identifiant de fiche). Erreur du RAPPORT du 05/09 (l.112 et 176).

Dette laissee au lot retrieval : le RRF de la prod reste casse (`_orig_index` absent cote dense,
RAPPORT l.107). Le lot 0 ne l'a pas corrige, pour que `local` reste le code servi.

## 1. Ce qui est etabli (mesure dans la nuit du 4 au 5 septembre 2026)

Source : `RAPPORT.md` (ce dossier, chaque chiffre cite fichier et ligne), version lisible :
https://claude.ai/code/artifact/4046b246-e9db-412a-b16f-0e200a2819b2

- Le produit servi (Mistral medium + RAG, mode strict v4) fait **2,04/5** sur une batterie neuve de
  60 conversations lyceens et etudiants, juge Opus 5 aveugle. GPT-5.5 sans aucune fiche : 4,28.
  Sonnet 5 sans fiche : 3,98. Sonnet 5 avec les fiches que le pipeline sert : 3,64.
- **Les fiches retrouvees n'apportent rien**, meme a un bon modele (3,35 avec vs 3,47 sans, critere
  references). Le retrieval a une contribution nulle ou negative.
- **Le mode strict detruit** ce qui reste (40 % de refus, 2 puces, 90 mots) mais c'etait le seul
  garde-fou : Mistral medium libere passe a 3,28 avec **62 % d'erreurs factuelles**.
- **Le lookup structure** (spike `spike_agent.py`) retrouve ce que le RAG rate (LAS Psycho Bordeaux,
  Licence Info Toulouse III) ; agent Sonnet 4,01, egal a Sonnet seul en moyenne : un juge LLM ne
  voit pas la valeur du corpus, seul un controle deterministe des chiffres la verra (lot 0).
- Contre-juge GPT-5.5 (30 tours x 4 systemes, partiel par credits OpenAI) : meme ordre, pas
  d'auto-preference Opus.

Causes par maillon (section 4 du rapport) : textualisation qui dit faux sur 13 011 fiches et tait le
type de formation, 0 cout, 12 831 sans ville, session 2025 servie en 09/2026 ; embedding qui ne
discrimine pas (3,2 % d'ecart rang 1 / rang 100), hybride BM25 mort, 5 fiches lues sur 10-12,
requete = message courant seul ; generation strict v4, corpus_check qui rend faux en dur, streaming
sans post-traitement ; evaluation sans humain depuis le 22/04, bancs incompatibles, recall@5 jamais
mesure.

## 2. Ce qui est perime (ne plus s'appuyer dessus sans le relire a la lumiere du rapport)

| Document | Pourquoi perime |
|---|---|
| `CLAUDE.md` racine (statut 16/04, matrice 7 systemes, "V2 RAFT") | decrit l'etat d'avril ; la banniere en tete renvoie ici. Reecriture prevue au palier 3 du menage |
| `docs/STRATEGIE_VISION_2026-04-16.md` | roadmap V2 (agentic + RAFT) non executee ; remplacee par les lots 0-5 |
| `docs/SESSION_HANDOFF.md` | etat operationnel d'avant l'ete |
| Roadmap H0/H1/H2 de l'audit du 15/07 et l'ordre H1 lot 2 (set de pertinence, commit `c7402d3` WIP) | remplaces par les lots 0-5 ; le set de pertinence 135/387 reste reutilisable dans le lot 0 |
| Gel du 11/06 (groundedness 0,949, "hallucinations 54 -> 10") | mesure sur les affirmations seulement, correction de rubrique incluse, pas un etat du produit |
| Bancs `results/_archive_pre_2026-06/`, `run1..run10`, `run_F_robust` | historiques, non comparables entre eux ni avec la batterie 2026-09-05 |
| `LLM_Final.md`, README (corpus "47k") | chiffres perimes, corpus reel 52 040 |

Ce qui reste valide : le corpus (52 040 fiches, muet mais reel), l'infra (pipeline, 3 202 tests,
Langfuse), le controle deterministe des chiffres du lot 1 de juillet (`src/eval/`), le banc gratuit de
676 questions embarquees (`golden_qa.index`, mais sans verite terrain de pertinence : cf section 0), la note de vision fondateur du 16/07 (vault) pour le
cap produit.

## 3. Ou vit chaque chose

- **Rapport technique et traces** : ce dossier sur `main` (merge 05/09). Runs bruts dans `runs/`,
  jugements dans `AGGREGATE_*.md`, 11 rapports de scouts dans `scouts/`. Batterie et scripts
  deplaces le 23/09 dans `src/eval/battery/` (section 0).
- **Branche d'experimentation** `jarvis/analyse-2026-09-05` : meme contenu, posee sur le WIP
  `c7402d3` de Claudette. Ne pas merger (elle porte le WIP), on peut la supprimer une fois ce dossier
  sur main.
- **QG partage** : https://orientai-hq.vercel.app (repo `~/projets/orientai-hq`, remote prive
  `matjussu/orientai-hq` depuis le 05/09). `content/decisions.json` porte les 3 decisions,
  `content/chantiers.json` les lots 0-5 (statut `propose`).
- **Vault Obsidian** : `01-Projets/Actifs/OrientAI-Analyse-Complete-2026-09-05.md` (pointeur +
  verdict), `OrientAI-Vision-Direction-2026-07-16.md` (cap produit).
- **Memoire Jarvis** : `project_orientia.md` (bloc de reprise 05/09 prioritaire).
- **Dossiers sur le PC** apres menage du 05/09 : `~/projets/OrientIA` (backend), `OrientAI_Platform`
  (front, 7 fichiers non commites depuis le 15/07 a traiter), `orientai-hq` (QG), `_orientai-ref`
  (dossier concours, pitch, refonte-ia-2026). Les archives `~/orientia-*-20260614` (10,4 G) ont ete
  supprimees ; reconstruction d'index assumee (`scripts/embed_unified.py`, ~5-10 EUR Mistral).

## 4. Par quoi on commence

1. **Trancher les 3 decisions** (Matteo + Ella, section 8 du rapport) : modele de generation
   (reco A : Sonnet 5), lookup structure + embedding hors Mistral (reco : lot 1 puis lot 3), ce qu'on
   vend (chiffres verifies + eval publique). **Tranchees le 23/09** (ordre 2026-09-23-0817) :
   generation Mistral ou open-weights, jamais un modele americain proprietaire ; recherche
   structuree a la place du RAG plat ; on vend la plateforme, argument « chaque chiffre verifiable ».
2. **Lot 0 sans attendre** (livre le 23/09, section 0) : le banc devient le gate. Integrer batterie + juge + agregation dans
   `src/eval/battery/`, brancher le controle deterministe des chiffres cites, reparer
   `eval_retrieval.py` (ids `idx:NNNNN` vs `fiche.id` absent sur 38 596 fiches) et mesurer recall@10
   sur les 676 questions (impossible : pas de verite terrain, mesure faite sur le set de pertinence). Cout ~3 USD par passage. Dispatch a Claudette par Jarvis via `/order`.
3. **Palier 3 du menage** en meme temps que le lot 0 : reecrire `CLAUDE.md`, regrouper `docs/`
   (87 fichiers), traiter `raw_responses_*_bak` et `sprint*_2026-04-2x.json`, consolider ou jeter le
   WIP de `OrientAI_Platform`.
4. Recharger les credits OpenAI si on veut completer le contre-juge (non bloquant).

Regle du projet a garder en tete (regle 13 Jarvis/Claudette) : une affirmation qui porte une decision
cite sa mesure. Le rapport est ecrit comme ca ; les lots doivent l'etre aussi.
