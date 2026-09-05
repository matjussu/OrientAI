# Agregation juge gpt (batterie Jarvis 2026-09-05)

## Moyennes par systeme (1-5)

| systeme | n | references | comprehension | expression | couverture | moy. 4 | refus | err. fact. |
|---|---|---|---|---|---|---|---|---|
| local | 30 | 2.13 | 2.37 | 2.97 | 1.97 | 2.36 | 16 (53 %) | 5 (17 %) |
| claude_ctx | 30 | 3.2 | 4.1 | 4.17 | 4.03 | 3.88 | 0 (0 %) | 19 (63 %) |
| claude_norag | 28 | 3.43 | 4.5 | 4.61 | 4.21 | 4.19 | 0 (0 %) | 20 (71 %) |
| gpt_norag | 14 | 4 | 4.93 | 5 | 4.93 | 4.71 | 0 (0 %) | 0 (0 %) |
| agent_sonnet | 0 | | | | | | | |
| agent_mistral | 0 | | | | | | | |

## Par persona

| systeme | persona | n | ref | compr | expr | couv |
|---|---|---|---|---|---|---|
| local | etudiant | 13 | 2 | 2.23 | 3 | 1.85 |
| local | lyceen | 17 | 2.24 | 2.47 | 2.94 | 2.06 |
| claude_ctx | etudiant | 14 | 3 | 4 | 3.93 | 3.93 |
| claude_ctx | lyceen | 16 | 3.38 | 4.19 | 4.38 | 4.12 |
| claude_norag | etudiant | 13 | 3.23 | 4.46 | 4.38 | 4.15 |
| claude_norag | lyceen | 15 | 3.6 | 4.53 | 4.8 | 4.27 |
| gpt_norag | etudiant | 7 | 4.14 | 5 | 5 | 4.86 |
| gpt_norag | lyceen | 7 | 3.86 | 4.86 | 5 | 5 |

## Distribution des notes 'references' (critere 1)

| systeme | 1 | 2 | 3 | 4 | 5 | part >= 4 |
|---|---|---|---|---|---|---|
| local | 7 | 15 | 5 | 3 | 0 | 10 % |
| claude_ctx | 0 | 4 | 16 | 10 | 0 | 33 % |
| claude_norag | 0 | 3 | 10 | 15 | 0 | 54 % |
| gpt_norag | 0 | 0 | 2 | 10 | 2 | 86 % |
| agent_sonnet | 0 | 0 | 0 | 0 | 0 | 0 % |
| agent_mistral | 0 | 0 | 0 | 0 | 0 | 0 % |

## cause_echec (quand references < 3 ou couverture < 3)

- local : generation 16, retrieval 7, aucune 1 (total 24)
- claude_ctx : generation 3, retrieval 1 (total 4)
- claude_norag : generation 2, retrieval 1 (total 3)
- gpt_norag :  (total 0)
- agent_sonnet :  (total 0)
- agent_mistral :  (total 0)

## local vs claude_ctx, memes fiches (isole retrieval vs generation)

- references : delta moyen +1.11 ; ctx meilleur sur 15, pire sur 2, egal 2 (n=19)
- comprehension : delta moyen +1.74 ; ctx meilleur sur 16, pire sur 0, egal 3 (n=19)
- expression : delta moyen +1.42 ; ctx meilleur sur 18, pire sur 0, egal 1 (n=19)
- couverture : delta moyen +1.95 ; ctx meilleur sur 17, pire sur 0, egal 2 (n=19)
- references <= 2 chez local : 13 tours ; dont toujours <= 2 avec Sonnet sur les memes fiches (=> fiches en cause) : 1 ['E14.0'] ; dont remontes a >= 4 (=> generation en cause) : 5 ['E11.1', 'E15.0', 'L12.0', 'L28.0', 'L29.0']
- tours sans aucune fiche servie : ['E28.0']

### Notes 'references' sur les tours 'fiches en cause', tous systemes

| tour | local | claude_ctx | claude_norag | gpt_norag | agent_sonnet | agent_mistral |
|---|---|---|---|---|---|---|
| E14.0 | 2 | 2 | 3 | 5 | - | - |

## Agents a outils : usage des outils

- agent_sonnet : n=67, appels/tour med 2 max 10, 0 appel sur 13 tours, fiches lues med 0, latence med 17.97 s, erreurs 0
- agent_mistral : n=67, appels/tour med 4 max 16, 0 appel sur 13 tours, fiches lues med 1, latence med 8.54 s, erreurs 0

## Multi-tour (tour >= 1) vs premier tour

| systeme | tour 0 : ref / compr | tour >= 1 : ref / compr | n1 |
|---|---|---|---|
| local | 2.15 / 2.33 | 2 / 2.67 | 3 |
| claude_ctx | 3.19 / 4.04 | 3.25 / 4.5 | 4 |
| claude_norag | 3.42 / 4.5 | 3.5 / 4.5 | 2 |
| gpt_norag | 4.08 / 4.92 | 3.5 / 5 | 2 |

## Pires tours de local (moyenne 4 criteres)

- L21.0 1/1/3/1 [retrieval] "BTS SIO option SLAM : c'est quoi le taux d'insertion et le salaire a la sortie ? Et apres " : La réponse ne traite pas le BTS SIO SLAM : elle remplace la question par des chiffres de masters, non comparables pour un lycéen. Il fallait donner au moins des
- L25.2 1/2/3/1 [retrieval] 'Entre licence MIASHS et prepa ECG, tu prends quoi a ma place ?' : La réponse esquive la comparaison demandée alors que, pour ce profil, il fallait opposer clairement MIASHS et ECG à Rennes avec les débouchés data/finance et le
- E27.0 1/2/3/1 [generation] "Ingenieur diplome d'ecole vs master universitaire en informatique : difference de salaire " : La réponse esquive la question centrale alors qu'il fallait donner des ordres de grandeur de salaire de départ et expliquer que l'écart dépend surtout du type d
- E13.0 1/2/3/1 [generation] "Je suis en M1 biologie, je veux faire un doctorat. Comment on trouve un financement et c'e" : La réponse esquive la question principale et remplace le doctorat par des informations de Master peu pertinentes. Il fallait expliquer les financements doctorau
- E11.1 1/2/3/1 [retrieval] 'Je suis en L3 maths a Grenoble, 14 de moyenne, je veux rester dans la region si possible.' : La réponse ne tient pas compte du fait que l’étudiant cherche un master après une L3 et propose une licence Parcoursup hors sujet. Il fallait rechercher/citer d
- L30.0 2/2/2/2 [generation] 'Je suis en zone rurale dans la Creuse, il y a rien pres de chez moi. Comment je fais pour ' : La réponse cite une aide Master hors profil pour un lycéen et oublie l’essentiel : aide à la mobilité Parcoursup, DSE/bourse CROUS, logement CROUS/APL, internat
- L22.0 1/2/3/2 [generation] 'Comment je fais une bonne lettre de motivation Parcoursup pour un BUT MMI ? Ils regardent ' : Il fallait exploiter la fiche BUT MMI disponible et répondre concrètement sur les attendus MMI : intérêt pour communication numérique, web, audiovisuel, créativ
- E30.0 1/2/4/1 [generation] 'Je veux faire mon master en Belgique en logopedie. Le diplome est reconnu en France apres ' : La réponse esquive une question standard sur une profession réglementée : il fallait expliquer que la logopédie/orthophonie relève d'une autorisation d'exercice
- E22.0 2/2/3/1 [generation] "Comment les masters selectionnent sur MonMaster ? C'est que la moyenne ou la lettre compte" : La réponse esquive la question principale : il fallait expliquer que chaque master sélectionne via une commission sur dossier MonMaster, avec relevés de notes m
- L03.0 2/2/2/2 [retrieval] 'Je veux devenir medecin, je suis a Bordeaux. PASS ou LAS ? Et est-ce que je peux faire la ' : La réponse ne traite pas vraiment le choix PASS/LAS ni la question centrale sur la LAS psychologie à Bordeaux, et elle se contente de dire que l’information man
- L12.0 2/2/3/1 [generation] "Je suis boursier echelon 6, je veux faire une ecole d'ingenieur. Est-ce que les ecoles pri" : La réponse cite deux écoles privées mais ne répond pas à la vraie question du coût pour un boursier échelon 6. Il fallait expliquer les bourses CROUS selon habi
- L16.0 2/2/3/1 [generation] 'Licence eco-gestion a Dauphine ou BUT GEA ? Je veux bosser en finance plus tard.' : La réponse n’effectue pas la comparaison demandée entre Dauphine et un BUT GEA pour viser la finance, alors que les éléments généraux étaient accessibles même s
- E15.0 2/2/2/2 [generation] 'Apres un BTS compta-gestion, licence pro ou DCG ? Je veux etre expert-comptable un jour.' : La réponse ne tranche pas clairement : pour viser l’expertise comptable après un BTS CG, il faut recommander prioritairement le DCG/DGC puis DSCG et DEC, en exp
- L11.0 2/2/3/2 [generation] "Je suis sportif et je veux bosser dans le sport mais pas prof d'EPS. STAPS c'est la seule " : La réponse part d’une mauvaise hypothèse (« ta L1 STAPS ») alors que le jeune est lycéen, et cite surtout un master hors niveau. Il fallait répondre clairement 
- E14.0 2/3/2/2 [generation] "Je suis accepte en master marketing en alternance mais j'ai pas d'entreprise. Si je trouve" : La réponse cite des masters et des chiffres de sélectivité sans rapport avec la question pratique. Il fallait expliquer la règle générale en alternance : admiss

## Erreurs factuelles relevees (local)

- E06.0 : Dire qu'il reste des places disponibles dans ces masters à la rentrée est infondé : les chiffres de capacité, candidatures et dernier appelé ne prouvent pas une place vacante, et en septembre la procé
- E30.0 : La réponse parle de « masters français en orthophonie » : en France, l'accès à la profession passe par le Certificat de capacité d'orthophoniste, diplôme d'État en 5 ans conférant le grade de master, 
- L03.0 : Les capacités indiquées pour le PASS de l’Université de Bordeaux (45 places) et de Limoges (26 places) sont très vraisemblablement fausses ou mal interprétées pour un PASS Parcoursup : elles sont beau
- L19.0 : La réponse présente comme « directement accessibles » après une LEA anglais-espagnol des métiers comme professeur de FLE ou lecteur de langues dans le supérieur, alors qu'ils nécessitent généralement 
- L22.0 : L'assistant affirme ne pas avoir de BUT MMI dans ses sources alors qu'une fiche 'BUT - Métiers du multimédia et de l'internet | I.U.T. Laval' était disponible. Les exemples cités sont en plus hors suj

### Erreurs factuelles claude_norag (20)

- E01.0 : La réponse affirme que le BUT Carrières juridiques n'existe pas, alors que cette spécialité de BUT existe bien en France, même si elle n'est pas forcément proposée à Montpellier.
- E06.0 : EPSI est une école d'informatique et IPSA une école d'ingénieurs aéronautique/spatial, pas des écoles de psychologie permettant d'obtenir le titre de psychologue. La phase complémentaire MonMaster n'e
- E10.0 : La réponse parle de « redoubler PASS » / « 2e tentative épuisée » : depuis la réforme PASS/L.AS, le redoublement de PASS n'est pas autorisé ; la 2e chance passe en général par une L.AS. L'idée d'un « 
- E11.0 : La réponse renvoie aux candidatures via eCandidat alors que, pour une entrée en M1 de master en France, la procédure standard est la plateforme Mon Master (eCandidat ne concerne que certains cas : M2,
- E13.0 : Le contrat doctoral n'est pas d'environ 2100 € net/mois : ce montant correspond plutôt à un ordre de grandeur brut récent ; le net est inférieur, selon les cotisations et revalorisations applicables.
- E14.0 : La réponse classe les IAE avec les écoles privées/écoles de commerce, alors que les IAE sont des composantes universitaires publiques. Elle omet aussi le cadre national important de l'alternance : en 
- E15.0 : Dire que DCG→DSCG→stage→DEC est « le seul chemin » est trop catégorique : on peut aussi accéder au DSCG via un master, notamment master CCA, puis obtenir le DEC. Une licence pro n'est pas la voie dire
- E22.0 : Mon Master est la plateforme nationale de candidature en M1 depuis la campagne 2023, pas seulement depuis 2024. En 2026, il existe bien une phase complémentaire structurée sur Mon Master, contrairemen
- E25.0 : L'INSA Centre-Val de Loire à Blois délivre le Diplôme d'État de paysagiste via l'École de la nature et du paysage, ce n'est pas un “cycle ingénieur paysagiste”. La réponse omet aussi la voie important
- E26.0 : Le taux annoncé pour la L1 de psychologie en France, « autour de 15 à 25 % », est très probablement trop bas pour un taux national de validation/passage en L2 en un an ; les données SIES/Parcoursup pa
- L01.0 : La réponse affirme que le réseau Polytech n'est « pas à Lyon », alors que Polytech Lyon existe à l'Université Lyon 1 et propose notamment un cursus ingénieur avec accès post-bac via le PeiP.
- L02.0 : Le réseau Polytech ne recrute pas via le concours Puissance Alpha ; il a ses propres procédures/concours selon les niveaux. Le concours ATOUT+3 concerne surtout des écoles de commerce/management, pas 
- L10.0 : Le BTS Design graphique avec options communication/médias imprimés ou numériques n'est plus une voie standard ouverte en 2026 : il a été remplacé par le DNMADE depuis plusieurs années. Le présenter co
- L12.0 : L'échelon 6 n'est pas l'échelon le plus élevé des bourses CROUS : il existe un échelon 7. Le montant annuel indiqué autour de 6 900 € pour l'échelon 6 est également très probablement surestimé/confus 
- L13.0 : L'IUT de Blagnac est rattaché à l'Université Toulouse - Jean Jaurès, pas à Paul Sabatier 'selon rattachement'. Quelques éléments sont aussi imprécis ou non sourcés, comme les taux de réussite/insertio
- L21.0 : La fourchette de 1600 à 2000 € brut/mois est problématique : en 2026, 1600 € brut mensuels pour un temps plein est inférieur au SMIC brut, donc ce n’est pas un salaire légal possible. Par ailleurs, di
- L25.0 : La formulation « MP2I puis MP » est trompeuse/fausse : la MP2I mène principalement à la 2e année MPI (éventuellement PSI selon parcours/options), tandis que MPSI mène à MP/PSI. Les ENS ne sont pas des
- L26.0 : La Fémis, pour le cursus principal visé (réalisation/montage), n'est pas accessible simplement avec le bac à 18 ans : le concours général exige en pratique un niveau bac+2 ou équivalent/expérience sel
- L29.0 : La réponse affirme que le titre RNCP est délivré par l'école elle-même : ce n'est pas forcément le cas, l'école peut seulement préparer à une certification détenue par un certificateur tiers. Elle nua
- L30.0 : L'aide au mérite n'est pas accordée avec une mention Bien : elle concerne les étudiants boursiers ayant obtenu la mention Très Bien au bac. La réduction SNCF via carte Avantage n'est pas un droit lié 

### Erreurs factuelles claude_ctx (19)

- E01.0 : Sciences Po Toulouse est cité comme piste de réorientation en cours d'année via des places vacantes/SCUIO-IP à Montpellier, ce qui est trompeur : ce n'est pas une L1 universitaire montpelliéraine et l
- E05.0 : Puissance Alpha n'est pas le concours du groupe INSA et ne regroupe pas les INSA de Toulouse, Lyon, Rennes, Rouen, Strasbourg. Le concours/voie 'Ambitions X-Insa' associant Arts et Métiers et Polytech
- E10.0 : La réponse cite des exemples probablement inexacts ou mal qualifiés : Lyon 2 n'est pas une référence pertinente pour une L1 mention Informatique classique, et UPHF n'est pas « adossée au réseau Polyte
- E11.0 : La réponse suggère que les mastères spécialisés en data science sont accessibles en admission parallèle après une licence ; un Mastère Spécialisé CGE est normalement accessible après un bac+5, ou parf
- E13.0 : Le calendrier se trompe d'année : nous sommes en septembre 2026, donc un étudiant en M1 en 2026-2027 viserait plutôt un M2 en 2027-2028 puis une thèse à partir d'octobre 2028, pas octobre 2027. Le mon
- E14.0 : La réponse affirme de façon générale que sans entreprise à la rentrée il n'y a pas d'inscription possible et perte de place. Or en apprentissage, un CFA/une formation peut accueillir un jeune sans con
- E21.0 : Les CAF/CPAM relèvent du régime général de la Sécurité sociale et recrutent en principe hors statut de la fonction publique : 'technicien Assurance Maladie / CAF' n'est donc pas un concours de la fonc
- E23.1 : La recommandation de candidater à des « Mastère Spécialisé RNCP » après un BUT est trompeuse : un Mastère Spécialisé CGE est en principe accessible après bac+5 ou bac+4 avec expérience, pas directemen
- E24.0 : L'affirmation selon laquelle la voie la plus adaptée serait une admission parallèle après L2 STAPS, avec une majorité d'IFMK réservant 10 à 30% de places sur dossier + oral, est trompeuse/fausse comme
- E25.0 : L'ENSA Nancy n'est pas une école délivrant le Diplôme d'État de paysagiste ; l'école de Blois / INSA Centre-Val de Loire, qui le délivre, est oubliée. Le DEP recrute classiquement après bac+2 pour une
- L10.0 : Le BTS design graphique n'existe plus comme voie standard en 2026 : il a été remplacé par le DN MADE depuis la réforme des arts appliqués. Parler d'un 'BTS design graphique en alternance' comme option
- L11.0 : L'assistant écrit « Ingénierie et ergonomie de l'activité physique (APAS) » : APAS désigne normalement Activité Physique Adaptée et Santé, pas l'ingénierie/ergonomie. Il cite aussi EPSI comme école de
- L12.0 : Le prêt étudiant garanti par l'État n'est pas limité à 15 000 € : le plafond usuel est de 20 000 €. La mention d'un 'bonus' boursier dans le classement Parcoursup est aussi imprécise : il s'agit plutô
- L14.0 : Pour les lycéens/candidats Parcoursup en IFSI, la sélection se fait normalement sur dossier via Parcoursup, sans concours ni entretien complémentaire organisé par les IFSI ; les épreuves/entretiens co
- L19.0 : Le code ROME K2130 pour professeur de FLE paraît inexistant/inexact. De plus, en 2026, dire que devenir professeur suppose d'abord un master MEEF puis le CAPES est au minimum obsolète/trop catégorique
- L20.0 : La mention d'une ENSA à « Angers Ouest » est fausse : il n'existe pas d'école nationale supérieure d'architecture à Angers. Par ailleurs, le Diplôme d'État d'architecte ne suffit pas à porter le titre
- L21.0 : Le 'réseau FIED' n'est pas une école d'ingénieurs mais une fédération d'universités pour l'enseignement à distance. EPSI ne doit pas être présenté sans nuance comme une école délivrant un diplôme d'in
- L23.0 : ENSICA n'existe plus comme école distincte depuis sa fusion dans l'ISAE-SUPAERO ; la citer comme option actuelle après prépa est inexact/obsolète.
- L30.0 : L'avance du dépôt de garantie relève surtout de l'Avance Loca-Pass d'Action Logement, pas d'une 'aide à la première installation CROUS' générique. L'aide à la mobilité Parcoursup n'est pas pertinente 
