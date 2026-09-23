# Runs du 05/09 rapportes par le banc : runs

Pas de manifeste (run anterieur au banc versionne). Juge `opus`.

## Tableau de tete

Note du juge de 1 a 5. **Chiffres adosses** = part des chiffres cites (%, EUR, places) presents dans une fiche que le systeme a exposee sur ce tour ; entre parentheses, le temoin de hasard (memes reponses contre les fiches d'un autre tour). Un systeme sans fiche est a 0 par construction : ses chiffres ne peuvent pas etre montres.

| systeme | tours | erreurs | moy. 4 | references | comprehension | expression | couverture | refus | err. fact. | chiffres cites | adosses (hasard) | corpus seul | non retrouves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| local | 67 | 0 | 2.04 | 2.04 | 2.07 | 2.15 | 1.9 | 40 % | 16 % | 420 | 61 % (32 %) | 6 % | 33 % |
| claude_norag | 64/67 | 0 | 3.98 | 3.47 | 4.14 | 4.27 | 4.03 | 0 % | 41 % | 99 | 0 % (n/a) | 7 % | 93 % |
| claude_ctx | 65/67 | 0 | 3.64 | 3.35 | 3.89 | 3.35 | 3.97 | 0 % | 34 % | 361 | 80 % (28 %) | 1 % | 19 % |
| gpt_norag | 67 | 0 | 4.28 | 3.9 | 4.1 | 4.64 | 4.49 | 0 % | 1 % | 91 | 0 % (n/a) | 4 % | 96 % |
| agent_sonnet | 66/67 | 0 | 4.01 | 3.56 | 4.23 | 4.12 | 4.12 | 0 % | 21 % | 424 | 42 % (13 %) | 26 % | 32 % |
| agent_mistral | 65/67 | 0 | 3.28 | 2.77 | 3.37 | 3.62 | 3.38 | 5 % | 62 % | 648 | 63 % (21 %) | 6 % | 30 % |

Positions des fiches exposees : local : 53 fiches exposees a signature ambigue, 0 introuvables ; claude_ctx : 53 fiches exposees a signature ambigue, 0 introuvables ; agent_sonnet : 0 fiches exposees a signature ambigue, 8 introuvables ; agent_mistral : 0 fiches exposees a signature ambigue, 8 introuvables. Une signature ambigue compte toutes ses fiches (leger biais favorable au taux adosse) ; une fiche introuvable n'en compte aucune.

**Corpus seul** : chiffre absent des fiches exposees mais present dans une des 5 fiches que la ligne designe (BM25). Indicatif : calibre le 23/09, cet ancrage ne retrouve que 37 a 60 % des chiffres adosses et coincide par hasard sur ~15 % des chiffres. **Non retrouve** ne veut pas dire faux.

## Par domaine (moyenne des 4 criteres, n tours juges)

| domaine | local | claude_norag | claude_ctx | gpt_norag | agent_sonnet | agent_mistral |
|---|---|---|---|---|---|---|
| arts-design-archi | 2.31 (4) | 4.12 (4) | 4.06 (4) | 4.62 (4) | 4.19 (4) | 3.62 (4) |
| droit-eco-gestion | 1.98 (10) | 3.94 (9) | 3.67 (9) | 4.42 (10) | 4.12 (10) | 3.39 (9) |
| informatique | 2.02 (14) | 4.04 (14) | 3.48 (14) | 4.18 (14) | 4.12 (14) | 3.25 (14) |
| ingenieur | 1.67 (6) | 3.92 (6) | 3.42 (6) | 4.33 (6) | 3.75 (6) | 3.25 (6) |
| lettres-langues-shs | 2.21 (7) | 3.68 (7) | 3.54 (6) | 4.11 (7) | 3.75 (6) | 3.12 (6) |
| maths-sciences | 1.95 (5) | 4.44 (4) | 4.0 (5) | 4.4 (5) | 4.1 (5) | 3.55 (5) |
| sante | 2.29 (6) | 3.55 (5) | 3.42 (6) | 4.04 (6) | 3.54 (6) | 3.17 (6) |
| sport | 1.75 (1) | 4 (1) | 3.75 (1) | 4.5 (1) | 4.5 (1) | 1.5 (1) |
| transversal | 2.02 (13) | 4.12 (13) | 3.79 (13) | 4.29 (13) | 4.04 (13) | 3.29 (13) |
| voie-pro | 2.5 (1) | 3.75 (1) | 3.5 (1) | 4.5 (1) | 5 (1) | 3.75 (1) |

Chiffres adosses par domaine :

| domaine | local | claude_norag | claude_ctx | gpt_norag | agent_sonnet | agent_mistral |
|---|---|---|---|---|---|---|
| arts-design-archi | 48 % (21) | 0 % (9) | 73 % (30) | 0 % (7) | 63 % (43) | 76 % (54) |
| droit-eco-gestion | 58 % (65) | 0 % (15) | 81 % (43) | 0 % (16) | 43 % (46) | 41 % (74) |
| informatique | 69 % (120) | 0 % (19) | 74 % (93) | 0 % (20) | 41 % (125) | 66 % (201) |
| ingenieur | 100 % (16) | 0 % (10) | 74 % (23) | 0 % (6) | 27 % (30) | 45 % (56) |
| lettres-langues-shs | 33 % (92) | 0 % (13) | 76 % (46) | 0 % (10) | 59 % (51) | 53 % (75) |
| maths-sciences | 77 % (26) | 0 % (3) | 92 % (36) | 0 % (6) | 0 % (30) | 75 % (51) |
| sante | 100 % (20) | 0 % (6) | 86 % (35) | 0 % (2) | 50 % (44) | 87 % (91) |
| sport | 60 % (10) | 0 % (2) | 100 % (10) | 0 % (1) | 0 % (8) |  |
| transversal | 61 % (46) | 0 % (20) | 84 % (32) | 0 % (21) | 24 % (29) | 28 % (32) |
| voie-pro | 100 % (4) | 0 % (2) | 85 % (13) | 0 % (2) | 72 % (18) | 100 % (14) |

## Distribution du critere references

| systeme | 1 | 2 | 3 | 4 | 5 | part >= 4 |
|---|---|---|---|---|---|---|
| local | 20 | 27 | 17 | 3 | 0 | 4 % |
| claude_norag | 1 | 6 | 19 | 38 | 0 | 59 % |
| claude_ctx | 0 | 11 | 24 | 26 | 4 | 46 % |
| gpt_norag | 0 | 0 | 10 | 54 | 3 | 85 % |
| agent_sonnet | 0 | 6 | 21 | 35 | 4 | 59 % |
| agent_mistral | 5 | 21 | 24 | 14 | 1 | 23 % |

## Causes d'echec (quand references < 3 ou couverture < 3)

- local : generation 46, retrieval 8 (total 54)
- claude_norag : generation 5, retrieval 1, data_absente 1 (total 7)
- claude_ctx : generation 7, retrieval 3, data_absente 1 (total 11)
- gpt_norag : aucune (total 0)
- agent_sonnet : generation 6 (total 6)
- agent_mistral : generation 23, retrieval 2, data_absente 1 (total 26)

## local contre claude_ctx, memes fiches (isole la generation)

- references : delta moyen +1.29 ; ctx meilleur sur 51, pire sur 3 (n=65)
- comprehension : delta moyen +1.8 ; ctx meilleur sur 60, pire sur 0 (n=65)
- expression : delta moyen +1.22 ; ctx meilleur sur 50, pire sur 1 (n=65)
- couverture : delta moyen +2.06 ; ctx meilleur sur 62, pire sur 0 (n=65)

## Multi-tour contre premier tour (references / comprehension)

| systeme | tour 0 | tours >= 1 | n tours >= 1 |
|---|---|---|---|
| local | 2.05 / 2.05 | 2 / 2.29 | 7 |
| claude_norag | 3.47 / 4.1 | 3.5 / 4.5 | 6 |
| claude_ctx | 3.33 / 3.84 | 3.57 / 4.29 | 7 |
| gpt_norag | 3.9 / 4.07 | 3.86 / 4.43 | 7 |
| agent_sonnet | 3.54 / 4.2 | 3.71 / 4.43 | 7 |
| agent_mistral | 2.76 / 3.34 | 2.86 / 3.57 | 7 |

## Pires tours de local

- L06.0 1/1/2/1 [retrieval] "Prepa MPSI a Louis-le-Grand ou ecole d'ingenieur post-bac type INSA Lyon, qu'est-ce qui es" : La reponse esquive totalement une question de culture generale du systeme (INSA Lyon = cycle integre 5 ans avec passage quasi assure si travail serieux, vs MPSI
- L24.0 1/1/2/1 [generation] "J'ai trop peur de me tromper de voie et de gacher ma vie. Comment on choisit ?" : La question 'comment choisir sa voie sans se tromper' est au coeur meme de l'orientation post-bac : le refus est injustifie. Il fallait rassurer sur la reversib
- L21.0 1/1/2/1 [generation] "BTS SIO option SLAM : c'est quoi le taux d'insertion et le salaire a la sortie ? Et apres " : Le BTS SIO SLAM est une formation ultra-standard : il fallait donner l'essentiel de culture générale (poursuite majoritaire en licence pro/BUT/bachelor ou école
- L25.2 1/1/2/1 [retrieval] 'Entre licence MIASHS et prepa ECG, tu prends quoi a ma place ?' : Il fallait répondre sur le fond : MIASHS (voie universitaire, économie/maths appliquées, passerelles vers masters MIASHS/data) vs prépa ECG (voie sélective vers
- E04.0 1/1/2/1 [generation] "J'ai fait une annee de prepa PCSI et j'arrete. Je peux rentrer en L2 directement ou je rep" : La question est standard et relève de la culture générale du système : la 1re année de CPGE validée donne 60 ECTS via la convention lycée-université, ce qui per
- E12.0 1/1/2/1 [generation] "Apres une licence d'eco, integrer une ecole de commerce via les admissions paralleles ca v" : La reponse esquive totalement la question (admissions paralleles apres licence : concours Passerelle/Tremplin, AST HEC/ESSEC/ESCP/EM Lyon/Audencia, ~15-20 k€/an
- E16.0 1/1/2/1 [generation] 'Je veux partir un semestre en Erasmus pendant ma L3 LLCER anglais. Comment ca marche et il' : La question porte sur la procedure Erasmus+ en L3 (candidature un an avant via le service RI, learning agreement/ECTS, bourse Erasmus+ ~250-500 euros/mois, AMI 
- E21.0 1/1/2/1 [generation] 'Avec une L3 AES, quels concours de la fonction publique je peux passer directement ?' : La réponse esquive totalement une question de culture générale professionnelle (attaché territorial/d'administration via IRA, inspecteur des finances publiques,
- E23.0 1/1/2/1 [generation] 'Je suis en BUT informatique 3e annee a Villetaneuse.' : Le message "Je suis en BUT informatique 3e annee a Villetaneuse" est une ouverture d'orientation typique : il fallait rebondir (poursuite en master, ecole d'ing
- E29.0 1/1/2/1 [generation] "J'ai un BTS et 2 ans de boulot, je veux reprendre en licence pro. Je passe par Parcoursup " : C'est une question de procedure relevant de la culture generale : une licence pro ne se demande PAS sur Parcoursup (reserve au primo-acces post-bac) mais par ca

## Erreurs factuelles relevees par le juge

### local (11)

- E04.0 : L'assistant confond la prépa PCSI (CPGE scientifique) avec le 'Portail PCSI' de l'Université de Perpignan (Physique-Chimie-Sciences pour l'ingénieur), sans rapport avec le profil ni avec la géographie
- E05.0 : Les fiches citees (Polytech Sorbonne, ECE Paris avec taux d'acces et places Parcoursup) concernent l'admission post-bac en cycle preparatoire integre, pas les admissions paralleles apres BUT3 : les ch
- E06.0 : Les deux masters sont presentes comme ayant 'des places disponibles' alors que les chiffres cites (22 places / 599 candidats, dernier appele rang 43) sont des statistiques d'admission passees, pas des
- E11.1 : Affirmer qu'il n'existe pas de master data science en Auvergne-Rhone-Alpes est faux : UGA propose le master MIASHS/Statistique et science des donnees (SSD), le master Informatique parcours MoSIG/Data 
- E15.0 : Le DGC du CNAM-INTEC est présenté comme 'une étape clé vers le DCG' : c'est en réalité le diplôme d'établissement équivalent au DCG (mêmes UE, dispenses), pas une étape préalable. De plus, proposer un
- L03.0 : 45 places pour le PASS de l'Université de Bordeaux est invraisemblable : la capacité du PASS bordelais se compte en plusieurs centaines/milliers de places. Chiffre probablement mal lu ou hors contexte
- L13.0 : L'assistant affirme qu'aucune licence informatique pure n'existe a Toulouse, alors que l'Universite Toulouse III - Paul Sabatier propose bien une Licence Informatique (presente dans ses propres fiches
- L13.1 : L'assistant repete qu'il n'existerait pas de licence informatique a Toulouse : l'Universite Toulouse III - Paul Sabatier propose bien une Licence Informatique (portail Maths-Info), presente sur Parcou
- L14.0 : La reponse laisse croire que infirmier scolaire et infirmier de sante au travail sont des voies de formation distinctes ; ce sont des specialisations/exercices accessibles APRES le Diplome d'Etat d'in
- L17.0 : Depuis 2021 la procédure Sciences Po passe par Parcoursup mais elle n'est pas 'uniquement sur dossier' : elle comprend 4 étapes (dossier scolaire, notes du bac de spécialité/français, écrits personnel
- L25.2 : Affirmer qu'il n'existe ni licence MIASHS ni prépa ECG est faux : le MIASHS existe à l'Université Rennes 2 et des prépas ECG existent à Rennes (ex. lycée Chateaubriand). La mention des 'filières santé

### claude_norag (26)

- E01.0 : Le BUT Carrières juridiques existe bel et bien (spécialité du BUT dispensée dans plusieurs IUT) : affirmer qu'il « n'existe pas » est faux, et c'est justement une piste pertinente pour un L1 droit en 
- E05.0 : ESIGELEC et CPE Lyon sont rattachees au concours Puissance Alpha, pas au concours Advance (Advance = EPITA, ESME, IPSA, Sup'Biotech). Par ailleurs 'les Arts et Metiers, l'ENSAM' est un doublon : l'ENS
- E06.0 : L'IPSA est une école d'ingénieurs en aéronautique, pas une école de psychologie ; l'établissement privé de référence est l'École de Psychologues Praticiens (EPP) rattachée à l'ICP. 'Institut de Psycho
- E09.0 : La reforme entree en vigueur pour la session 2026 place le concours (CAPES externe, dont histoire-geographie) en FIN DE LICENCE (L3), et non en fin de M1 : le laureat suit ensuite un master MEEF en de
- E10.0 : Deux points fautifs : (1) en septembre 2026, une candidature Parcoursup porte sur la rentree 2027, pas '2026-2027' comme ecrit ; (2) le 'BUT en 2 ans si tu as un bac+1 valide' n'existe pas comme dispo
- E11.1 : La candidature en M1 se fait depuis 2023 via la plateforme nationale Mon Master (monmaster.gouv.fr, dépôt fin février-mars), pas via eCandidat de l'UGA (réservé aux M2 et cas particuliers). L'acronyme
- E12.0 : HEC, ESSEC, EM Lyon et EDHEC ne recrutent pas via le concours Ambitions+ (issu de la fusion Passerelle/Ecricome Tremplin) : elles ont leurs propres admissions sur titre (HEC AST, ESSEC AST, EDHEC AST.
- E13.0 : Le contrat doctoral MESR est d'environ 2 200 € BRUT/mois (soit ~1 800 € net), pas 2 100 € net ; la confusion brut/net gonfle nettement la rémunération annoncée. La CIFRE se traduit par une subvention 
- E14.0 : Les IAE sont des composantes publiques d'universite, pas des 'ecoles de commerce/privees' aux frais eleves. Surtout, la reponse affirme qu'il n'y a 'pas de regle nationale' alors que le Code du travai
- E17.0 : La mention « s'inscrit dans la continuité Parcoursup/dossier universitaire » est fausse : Parcoursup ne concerne que l'entrée en 1re année post-bac ; l'admission en M2 se fait via les candidatures pro
- E21.0 : Les IRA (Instituts régionaux d'administration) n'ont PAS été supprimés en 2022 : ils existent toujours (Bastia, Lille, Lyon, Metz, Nantes) et constituent la voie principale du concours d'attaché d'adm
- E22.0 : Mon Master est en place depuis la campagne 2023 (pas 2024) et il existe bien une phase complementaire officielle sur la plateforme (fin juin-juillet), contrairement a ce qui est affirme. Par ailleurs 
- E24.0 : La reponse affirme que la voie PASS/LAS est "fermee" et que la kine passe surtout par des admissions paralleles post-L2/L3. Or, depuis l'arrete du 17 janvier 2020, la L1 STAPS (comme la L1 sciences/sc
- E25.0 : L'Institut Agro Rennes-Angers (ex-Agrocampus Ouest, site d'Angers) est bien habilité à délivrer le Diplôme d'État de Paysagiste : il est ici présenté à tort comme une simple 'alternative ne donnant pa
- E26.0 : Le taux de reussite en licence 'en 3 ans' est donne a 45-50% alors que les donnees SIES le situent plutot autour de 30-33% (environ 45-50% en 3 ou 4 ans). Le taux de reussite L1 en psycho annonce a 15
- L01.0 : La reponse affirme que le reseau Polytech n'est 'pas a Lyon' : Polytech Lyon existe bien (Villeurbanne, rattachee a l'Universite Lyon 1) et recrute en cycle preparatoire integre (PeiP) via Parcoursup 
- L03.0 : Le PASS n'a PAS ete supprime au niveau national en 2024 : il coexiste toujours avec les LAS en 2026, et l'Universite de Bordeaux propose bien un PASS (avec options disciplinaires) en plus de ses LAS. 
- L07.0 : Le "BTS Domotique" n'existe pas : il s'agit du BTS FED option C Domotique et bâtiments communicants. Par ailleurs Pôle emploi s'appelle France Travail depuis 2024, et les taux de réussite avancés (60-
- L09.0 : Sorbonne Universite ne propose pas de licence de psychologie (l'Institut de psychologie releve d'Universite Paris Cite, a Boulogne). De meme, l'UVSQ, Cergy et Evry n'ont pas de licence de psycho ; en 
- L10.0 : Le BTS Design graphique n'existe plus : les BTS design (graphique, espace, produits, mode) ont ete supprimes et remplaces par le DNMADE depuis 2019-2020 ; il n'est donc plus une alternative Parcoursup
- L12.0 : L'echelon 6 n'est pas l'echelon le plus eleve : la bourse sur criteres sociaux comporte un echelon 7 (montant le plus haut, ~6 335 € puis revalorise). Le montant de ~6 900 €/an annonce pour l'echelon 
- L16.0 : Le conseil de faire une 'licence pro' apres un BUT GEA est errone : le BUT est deja un diplome bac+3 qui confere le grade de licence (et integre la licence pro), la suite logique est un master, un DSC
- L17.0 : Deux points inexacts : depuis la reforme de 2021, les candidats en Convention Education Prioritaire passent par la MEME procedure Parcoursup (4 phases) et non une 'procedure allegee avec oral local' ;
- L25.0 : La MP2I se poursuit en MPI (et non en MP) ; l'assistant ecrit 'MP2I puis MP'. Par ailleurs les ENS Paris/Lyon ne se rejoignent pas via une 'L3 selective' mais par concours (dont le concours normalien 
- L26.0 : Le concours general de La Fémis n'est pas ouvert 'des 18 ans sans diplôme' : il exige un bac+2 valide (ou equivalent/VAE) et une limite d'age (27 ans). Par ailleurs La CinéFabrique (Lyon) est une ecol
- L28.0 : Le BUT confère le grade de licence (bac+3) : on candidate directement en master via MonMaster, il n'est pas nécessaire de passer par une 'L3 passerelle'. L'affirmation inverse est fausse (elle valait 

### claude_ctx (22)

- E01.0 : "Sciences Po Toulouse en dossier" est cite comme une mention de L1 accessible en reorientation interne a l'Universite de Montpellier : c'est un IEP, hors de l'universite montpellieraine, et il ne recr
- E05.0 : Puissance Alpha n'est pas le concours du groupe INSA (c'est un concours d'écoles privées post-bac, avec une voie AST distincte) ; les villes citées (Toulouse, Lyon, Rennes, Rouen, Strasbourg) sont cel
- E06.0 : "Lyon (ICP, 12%)" : l'ICP est l'Institut catholique de Paris, pas de Lyon (l'établissement lyonnais est l'UCLy) ; "Institut de Psychologie de Paris" est présenté comme privé alors que l'Institut de ps
- E07.0 : Le dispositif Inserjeunes ne couvre pas les masters (il porte sur les CAP/bac pro/BTS et l'apprentissage secondaire) : les donnees d'insertion des masters proviennent de l'enquete du SIES (insertion a
- E09.0 : Depuis la reforme de la formation des enseignants, le concours (CAPES externe, dont histoire-geographie) est place en fin de LICENCE (L3) a partir de la session 2026, suivi d'un master MEEF en deux an
- E10.0 : Contradiction interne : la réponse dit d'abord qu'on ne peut pas redoubler le PASS puis suggère de 'retenter une PASS en parallèle' (impossible, le PASS n'est pas redoublable). UPHF Valenciennes n'est
- E13.0 : L'ARED est le dispositif d'allocations de recherche doctorale de la Region BRETAGNE, pas de la region Sud. Le montant du contrat doctoral annonce (~2100 EUR net/mois) est surevalue : apres la revalori
- E17.0 : L'entree en M2 ne se fait pas via monmaster.gouv.fr : la plateforme ne concerne que l'admission en M1. Pour une reorientation disciplinaire vers l'urbanisme, il faut soit candidater en M1 via MonMaste
- E19.0 : Les montants annoncés comme 'chiffres 2024-2025' (1080 € à 5965 €) correspondent en réalité au barème 2022-2023 ; en 2024-2025 l'échelon 0bis était à environ 1454 € et l'échelon 7 à environ 6335 €.
- E24.0 : Depuis la reforme, l'acces principal aux IFMK depuis STAPS se fait apres une L1 STAPS VALIDEE dans une universite conventionnee avec l'IFMK (contingent de places fixe chaque annee), et non 'apres L2' 
- E29.0 : La licence professionnelle n'est pas 'integree aux BUT' : les LP existent toujours comme mentions autonomes (bac+3, un an post-BTS/BUT2), meme si le BUT a absorbe une partie de l'offre en IUT. Confusi
- L03.0 : Le PASS de l'Universite de Bordeaux n'a pas '45 places' (la capacite est de l'ordre de plus d'un millier de places) ; le chiffre cite est invraisemblable. Par ailleurs 'ecandidat' n'est pas la procedu
- L07.0 : Le "Lycée Élisa Lemonnier" est un lycée parisien (12e), il n'existe pas à Douai ; l'offre de BTS Électrotechnique du Douaisis relève d'autres établissements (ex. lycée Edmond Labbé). Les chiffres asso
- L11.0 : L'EPSI est une ecole d'informatique, pas une ecole de management du sport ; les references pertinentes seraient AMOS, Sports Management School, ESG Sport. La mention 'STAPS Kinesitherapie' est aussi t
- L12.0 : Le prêt étudiant garanti par l'État est plafonné à 20 000 € (depuis 2023), pas 15 000 €. Les chiffres d'insertion « 58% à 6 mois / 71% à 12 mois » identiques pour ECE/ESME/EFREI sont invraisemblables 
- L16.0 : Le BUT GEA etant deja un diplome bac+3 grade licence, la 'poursuite quasi garantie vers licence pro' est fausse (la licence pro se fait apres un bac+2). Par ailleurs le parcours 'management des foncti
- L17.0 : Le contenu du dossier Sciences Po est faussé : il n'existe ni "deux notes de vie de classe" ni "grand oral blanc" evalue par le lycee. La procedure reelle repose sur 4 volets : performance academique 
- L19.0 : Le parcours enseignement est presente comme 'master MEEF puis CAPES' : depuis la reforme entree en vigueur en 2026, le concours du CAPES se passe desormais en fin de licence (bac+3), suivi de deux ann
- L20.0 : Il n'existe pas d'ENSA a Angers : les ecoles publiques d'architecture les plus proches de Nantes sont l'ENSA Bretagne (Rennes) et l'ENSA Normandie (Rouen). Par ailleurs le DEA seul ne suffit pas pour 
- L21.0 : Le "réseau FIED" n'est pas un réseau d'écoles d'ingénieurs (c'est la Fédération Interuniversitaire de l'Enseignement à Distance) ; EPSI n'est pas une école d'ingénieurs habilitée CTI. Le salaire annon
- L25.1 : L'ENSAI ne recrute pas en admission post-bac : le recrutement se fait sur concours après CPGE (MP, ECG, BL, TSI) ou sur titres à bac+2/+3, pas via une 'voie post-bac sélective en 3 ans'. Le chiffre de
- L26.0 : Le BTS Métiers de l'audiovisuel existe bel et bien (option Montage et postproduction) et n'a pas été remplacé par un BUT : il n'existe pas de BUT audiovisuel. La prépa Ciné-Sup est à Nantes (lycée Gui

### gpt_norag (1)

- E21.0 : Le corps des contrôleurs du travail est en extinction depuis 2013 (fusion dans le corps de l'inspection du travail) : il n'y a plus de concours externe de contrôleur du travail. Mineur : le concours C

### agent_sonnet (14)

- E05.0 : Le concours Advance est un concours POST-BAC (ESME, EPITA, IPSA, Sup'Biotech) et ne regroupe pas ESTIA, ICAM, ESIGELEC, CPE Lyon ou l'ISEP ; Puissance Alpha est egalement un concours post-bac et ne co
- E08.0 : Le texte de reference cite est errone : la cesure est encadree par la circulaire du 22 juillet 2015 puis le decret n°2018-372 du 18 mai 2018 (et arrete du meme jour) ; la 'circulaire du 23 juillet 201
- E09.0 : Le coeur de la reponse est faux : depuis la session 2026, le concours (CAPES externe, dont histoire-geographie) est place a la fin de la LICENCE (bac+3), pas en fin de M1. Les laureats deviennent ensu
- E12.0 : Le pret etudiant garanti par l'Etat est plafonne a 20 000 euros (et non 45 000) ; le chiffre de 45 000 euros sans caution releve d'offres bancaires privees, pas du dispositif garanti par l'Etat. Par a
- E15.0 : Affirmer qu'une licence pro « ne donne pas accès au DSCG » est faux : le DSCG est accessible à tout titulaire d'un diplôme conférant le grade de licence, licence pro incluse (l'inconvénient réel étant
- E17.0 : MonMaster ne gere que l'entree en M1 : on ne candidate pas en M2 via la plateforme (admissions M2 en direct aupres des universites, souvent en avril-juin). De plus, depuis la reforme du master, les ma
- E23.2 : Les taux d'admission annonces sont invraisemblables : 0,13% pour le master UPEC signifierait environ 1 admis pour 770 candidats, et 0,6-0,8% pour Paris Cite. Il y a manifestement confusion entre taux 
- E24.0 : L'idee d'une 'admission parallele/sur titre' en IFMK pour un titulaire de L1/L2/L3 scientifique est presentee comme la voie la plus realiste : or depuis la reforme de 2019, l'entree en IFMK passe obli
- L05.0 : Deux erreurs : la date limite de formulation des voeux est mi-mars (autour du 13 mars), pas 'debut mars / 10-12 mars' ; surtout, la confirmation des voeux (finalisation du dossier + projet de formatio
- L08.0 : Les IRA (Instituts régionaux d'administration) recrutent des attachés d'administration de l'État, pas des attachés territoriaux (qui passent un concours distinct organisé par les centres de gestion / 
- L10.0 : GOBELINS (Paris Gambetta) n'est pas un lycee public : c'est un etablissement de la CCI Paris Ile-de-France, prive, dont le DN MADE est payant plusieurs milliers d'euros par an. Dire qu'il 'reste publi
- L12.0 : L'echelon 6 n'est pas l'echelon le plus eleve : il existe un echelon 7 (mentionne d'ailleurs plus haut dans la reponse, contradiction interne). Le montant annonce (~7700 euros/an) est invraisemblable 
- L17.0 : Depuis la reforme de 2021, la procedure d'admission au Bachelor de Sciences Po comporte 4 epreuves : 3 sur dossier (notes du lycee, epreuves ecrites du bac/specialites, ecrits de motivation) ET un ORA
- L18.0 : La reponse affirme qu'on n'entre pas directement en ecole veto post-bac hors Oniris : c'est faux depuis 2021, il existe une voie d'acces post-bac sur Parcoursup vers les 4 ENV (Alfort, Toulouse, Nante

### agent_mistral (40)

- E01.0 : ESILV n'a pas de campus a Montpellier (Paris-La Defense, Nantes, Bordeaux) ; par ailleurs les 'taux d'acces' et nombres de places cites (BUT Informatique 28%, Science politique 12%, Bachelor EPF 52%) 
- E02.0 : Plusieurs données semblent inventées ou hors procédure : MonMaster ne publie pas de 'rang du dernier appelé' ni de moyennes des admis (le '472' et le 'entre 12 et 14/20' sont fabriqués) ; le 'CFA Afia
- E04.0 : Les taux d'acces et capacites cites (Nantes 100%, Strasbourg 227 places, Lyon 1 480 places) sont des donnees Parcoursup relatives a l'entree en L1 : elles n'ont aucune valeur pour une admission en L2,
- E05.0 : Plusieurs affirmations fausses : le concours ATS n'est pas un concours 'Centrale/Mines/Ponts' ouvert directement aux BUT, c'est un concours reserve aux eleves ayant fait une prepa ATS (une annee post-
- E06.0 : On n'entre pas en L3 de psychologie via Parcoursup ni en phase complémentaire (Parcoursup ne gère que la L1 ; l'entrée en L2/L3 se fait par candidature directe/eCandidat). La phase complémentaire 2026
- E07.0 : Le salaire annonce (environ 2 000 EUR brut / 1 600 EUR net a 30 mois) est invraisemblablement bas pour un diplome de master : c'est quasiment le niveau du SMIC 2026. Les enquetes MESR d'insertion des 
- E09.0 : Depuis la réforme, le CAPES se passe désormais en fin de licence (bac+3), session 2026 : le concours n'est plus en M1 ni en M2. Le parcours est ensuite un master MEEF 'métiers du professorat' en 2 ans
- E10.0 : Les licences Portail Informatique d'Avignon et de Caen sont presentees comme des LAS avec mineure sante : ce sont des portails informatiques classiques (les fiches ne mentionnent pas de LAS). De plus,
- E12.0 : Les concours communs sont mal decrits : Passerelle 1 (bac+2) et Passerelle 2 (bac+3) servent a integrer le Programme Grande Ecole, pas 'un Bachelor en 1 an' ; Tremplin 1/2 (Ecricome) sont des concours
- E13.0 : Montant du contrat doctoral sous-estime : le minimum reglementaire est d'environ 2 200 € brut/mois (~1 780-1 850 € net) et non 2 100 € brut / 1 500 € net. Par ailleurs l'ED 518 (IPGP) citee en exemple
- E16.0 : Le Royaume-Uni est cite deux fois comme destination Erasmus+ (avec bourse de 350-400 EUR/mois) alors qu'il a quitte le programme Erasmus+ apres le Brexit (2021) ; les mobilites vers le UK relevent d'a
- E17.0 : MonMaster n'est PAS la plateforme d'entrée en M2 : elle sert aux candidatures en M1 (les trois masters cités sont d'ailleurs des offres M1 sur MonMaster). Une réorientation depuis un M1 droit des affa
- E18.0 : Chiffres inventés présentés comme des données ('~30% conseil, ~40% industrie'), nomenclature 'RNCP niveau 1' obsolète (niveau 7 depuis 2019), et durée/coût du double diplôme Centrale Nantes–Audencia a
- E20.0 : Le DN MADE est un diplôme post-bac en 3 ans recruté sur Parcoursup, pas une formation en 1 an accessible/pertinente pour une L2 ; la licence pro n'est pas non plus une entrée Parcoursup pour un étudia
- E21.0 : L'ENA est devenue l'INSP (Institut national du service public), pas 'ISP' ; et son concours externe est accessible dès un diplôme de niveau licence (bac+3), pas bac+5. Le chiffre de '1 200 postes' d'a
- E23.0 : Proposer une Licence Pro apres un BUT3 est absurde (meme niveau bac+3). Epitech n'est pas une ecole d'ingenieur (titre RNCP 7, non CTI). Salaire median annonce 35-40k a la sortie d'un BUT informatique
- E23.1 : Salaires très surévalués : un sortant de BUT Informatique ne démarre pas à 2 500–3 000 € NET/mois (réalité ~1 800–2 200 € net, soit ~30-35 k€ brut/an), ni un sortant de master cyber à 3 500–4 500 € ne
- E24.0 : Plusieurs erreurs de procedure : (1) l'admission en IFMK via STAPS se joue sur selection en FIN de L1 STAPS (quota), on n'entre pas en 'L2 parcours kine' sur dossier ; (2) le PASS ne se redouble pas e
- E26.0 : Le taux national de passage de L1 en L2 en un an est d'environ 30-35 % selon le SIES/MESR (et non 60 %). De plus, le droit n'est pas une licence sélective et la médecine n'est pas une licence ; les ch
- E29.0 : Faux : les licences professionnelles (bac+3) ne se recrutent PAS via Parcoursup. Parcoursup ne gere que l'entree en premiere annee d'etudes superieures. Les candidatures en LP se font en direct aupres
- E30.0 : Le diplôme français n'est pas un 'Diplôme d'État d'orthophoniste' mais le Certificat de Capacité d'Orthophoniste (CCO, grade master). De plus, il n'existe pas d'Ordre des orthophonistes en France : l'
- L02.0 : Le BTS est annoncé comme un diplôme de niveau Bac+3 (il est Bac+2, ce que la réponse contredit elle-même deux lignes plus bas). Le chiffre '40% des BTS poursuivent' est sous-estimé (environ 6 diplômés
- L03.0 : Chiffres invraisemblables et contradictoires : le PASS de Bordeaux accueille plus d'un millier d'etudiants, pas 45 places ; '97% avec mention Bien ou TB' contredit la ligne suivante (8% TB, 30% B, 49%
- L05.0 : 1) Parcoursup ne comporte plus de classement/ordre des vœux depuis 2018 : la date du 2 avril correspond à la finalisation du dossier et à la CONFIRMATION des vœux, pas à une 'modification de l'ordre'.
- L07.0 : Statistiques incohérentes ('83 % de bacs pro (dont 17 % de bacs techno)'), Pôle emploi n'existe plus (France Travail depuis 2024) et le lien labonnealternance.pole-emploi.fr est obsolète ; entreprises
- L12.0 : Plusieurs chiffres semblent inventés ou faux : 'taux d'accès souvent < 10 % pour les prépas intégrées' des écoles publiques (INSA, Polytech, GEIPI, UT ont des taux bien supérieurs), les '9 % d'admis b
- L13.0 : Deux erreurs sûres : (1) Parcoursup ne hiérarchise pas les vœux en phase principale — conseiller de mettre la licence 'en vœu 1' et des sécurités 'en vœu 2-3' est une procédure fausse ; (2) statistiqu
- L13.1 : SUPINFO n'existe plus (liquidation judiciaire en 2022) et ne recrute donc pas a Toulouse ; par ailleurs une licence professionnelle se prepare apres un bac+2 (elle correspond a la 3e annee), elle n'es
- L14.1 : Les 'taux d'accès par type de bac' (32% techno vs 55% généraux, etc.) n'existent pas dans les données Parcoursup, qui ne publient que la répartition des admis par bac : ces chiffres semblent fabriqués
- L17.0 : L'affirmation 'admission uniquement sur dossier' est fausse : depuis la reforme 2021, la procedure Sciences Po via Parcoursup comporte 4 epreuves, dont un ORAL d'admission (entretien de ~30 min devant
- L18.0 : Affirmation fausse : depuis 2021 il existe bien une voie d'accès POST-BAC aux écoles nationales vétérinaires via Parcoursup (concours voie post-bac, ~160 places réparties entre Alfort, Toulouse, Oniri
- L20.0 : Le 'BTS Design d'espace' n'existe plus (remplacé par le DN MADE mention espace depuis 2018) ; le DN MADE est cité via l'École de design Nantes Atlantique, école privée coûteuse alors que les DN MADE p
- L21.0 : La Licence Pro ASRALL est à l'IUT Nancy-Charlemagne, pas à Paris. Le BUT ne se fait pas 'en 1 an après le BTS' : la passerelle mène en BUT2, soit 2 ans restants. Écoles d'ingénieurs 'en 3 ans' après B
- L22.0 : Le 'projet de formation motivé' sur Parcoursup est limité à 1500 caractères (pas 'une page'), et proposer un entretien est hors procédure pour un BUT (recrutement sur dossier, pas d'entretien). Le TPE
- L25.1 : Il existe bien un BUT STID a l'IUT de Vannes (departement Statistique et informatique decisionnelle) : dire que le plus proche est un BUT Informatique a Lannion/Vannes est faux. Par ailleurs 'Universi
- L25.2 : Affirmer qu'il n'y a « aucune MIASHS à Rennes » est très probablement faux : l'Université Rennes 2 propose une licence MIASHS (parcours math-info/économie), présente sur Parcoursup. Par ailleurs, la «
- L26.0 : La CinéFabrique (Lyon) recrute sur concours dès le niveau bac (sans condition de diplôme), et non 'après un premier cycle' comme l'affirme la réponse. Le chiffre d'insertion '53 % pour les licences en
- L27.0 : Le PAI et le PPS n'existent pas dans l'enseignement supérieur (dispositifs scolaires du 1er/2nd degré) ; la statistique '92% des étudiants avec PAP/RQTH a l'Universite Paris Cite en 2025, source rappo
- L29.0 : La licence professionnelle est présentée comme une alternative directe pour un lycéen alors qu'elle se prépare en 1 an après un bac+2 (BTS/BUT2/L2) ; l'exemple 'Licence pro Métiers du numérique parcou
- L30.0 : Bourse echelon 7 annoncee a 'jusqu'a 1 100 EUR/mois' : le montant reel est d'environ 6 335 EUR/an, soit ~633 EUR/mois sur 10 mois. Aide au merite annoncee a '400 a 1 800 EUR/an' et ouverte aux mention
