# Agregation juge opus (batterie Jarvis 2026-09-05)

## Moyennes par systeme (1-5)

| systeme | n | references | comprehension | expression | couverture | moy. 4 | refus | err. fact. |
|---|---|---|---|---|---|---|---|---|
| local | 67 | 2.04 | 2.07 | 2.15 | 1.9 | 2.04 | 27 (40 %) | 11 (16 %) |
| claude_ctx | 65 | 3.35 | 3.89 | 3.35 | 3.97 | 3.64 | 0 (0 %) | 22 (34 %) |
| claude_norag | 64 | 3.47 | 4.14 | 4.27 | 4.03 | 3.98 | 0 (0 %) | 26 (41 %) |
| gpt_norag | 67 | 3.9 | 4.1 | 4.64 | 4.49 | 4.28 | 0 (0 %) | 1 (1 %) |
| agent_sonnet | 66 | 3.56 | 4.23 | 4.12 | 4.12 | 4.01 | 0 (0 %) | 14 (21 %) |
| agent_mistral | 65 | 2.77 | 3.37 | 3.62 | 3.38 | 3.28 | 3 (5 %) | 40 (62 %) |

## Par persona

| systeme | persona | n | ref | compr | expr | couv |
|---|---|---|---|---|---|---|
| local | etudiant | 33 | 1.88 | 2 | 2.15 | 1.82 |
| local | lyceen | 34 | 2.21 | 2.15 | 2.15 | 1.97 |
| claude_ctx | etudiant | 31 | 3.26 | 3.84 | 3.26 | 3.81 |
| claude_ctx | lyceen | 34 | 3.44 | 3.94 | 3.44 | 4.12 |
| claude_norag | etudiant | 31 | 3.23 | 4.06 | 4.1 | 3.84 |
| claude_norag | lyceen | 33 | 3.7 | 4.21 | 4.42 | 4.21 |
| gpt_norag | etudiant | 33 | 3.85 | 4.09 | 4.67 | 4.42 |
| gpt_norag | lyceen | 34 | 3.94 | 4.12 | 4.62 | 4.56 |
| agent_sonnet | etudiant | 32 | 3.44 | 4.12 | 4.12 | 4.06 |
| agent_sonnet | lyceen | 34 | 3.68 | 4.32 | 4.12 | 4.18 |
| agent_mistral | etudiant | 31 | 2.65 | 3.26 | 3.58 | 3.29 |
| agent_mistral | lyceen | 34 | 2.88 | 3.47 | 3.65 | 3.47 |

## Distribution des notes 'references' (critere 1)

| systeme | 1 | 2 | 3 | 4 | 5 | part >= 4 |
|---|---|---|---|---|---|---|
| local | 20 | 27 | 17 | 3 | 0 | 4 % |
| claude_ctx | 0 | 11 | 24 | 26 | 4 | 46 % |
| claude_norag | 1 | 6 | 19 | 38 | 0 | 59 % |
| gpt_norag | 0 | 0 | 10 | 54 | 3 | 85 % |
| agent_sonnet | 0 | 6 | 21 | 35 | 4 | 59 % |
| agent_mistral | 5 | 21 | 24 | 14 | 1 | 23 % |

## cause_echec (quand references < 3 ou couverture < 3)

- local : generation 46, retrieval 8 (total 54)
- claude_ctx : generation 7, retrieval 3, data_absente 1 (total 11)
- claude_norag : generation 5, retrieval 1, data_absente 1 (total 7)
- gpt_norag :  (total 0)
- agent_sonnet : generation 6 (total 6)
- agent_mistral : generation 23, retrieval 2, data_absente 1 (total 26)

## local vs claude_ctx, memes fiches (isole retrieval vs generation)

- references : delta moyen +1.29 ; ctx meilleur sur 51, pire sur 3, egal 11 (n=65)
- comprehension : delta moyen +1.8 ; ctx meilleur sur 60, pire sur 0, egal 5 (n=65)
- expression : delta moyen +1.22 ; ctx meilleur sur 50, pire sur 1, egal 14 (n=65)
- couverture : delta moyen +2.06 ; ctx meilleur sur 62, pire sur 0, egal 3 (n=65)
- references <= 2 chez local : 45 tours ; dont toujours <= 2 avec Sonnet sur les memes fiches (=> fiches en cause) : 8 ['E04.0', 'E05.0', 'E10.0', 'E14.0', 'E22.0', 'L03.0', 'L13.1', 'L21.0'] ; dont remontes a >= 4 (=> generation en cause) : 18 ['E02.0', 'E08.0', 'E11.1', 'E15.0', 'E16.0', 'E18.0', 'E19.0', 'E21.0', 'E28.0', 'E30.0', 'L04.0', 'L13.0', 'L14.0', 'L16.0', 'L22.0', 'L25.1', 'L25.2', 'L28.0']
- tours sans aucune fiche servie : ['E23.0', 'E28.0', 'L06.0', 'L24.0']

### Notes 'references' sur les tours 'fiches en cause', tous systemes

| tour | local | claude_ctx | claude_norag | gpt_norag | agent_sonnet | agent_mistral |
|---|---|---|---|---|---|---|
| E04.0 | 1 | 2 | 3 | 4 | 3 | 2 |
| E05.0 | 1 | 2 | 3 | 4 | 2 | 2 |
| E10.0 | 2 | 2 | 3 | 4 | 4 | 2 |
| E14.0 | 1 | 2 | 2 | 4 | 3 | 3 |
| E22.0 | 2 | 2 | 3 | 3 | 4 | 3 |
| L03.0 | 2 | 2 | 1 | 3 | 3 | 2 |
| L13.1 | 1 | 2 | 4 | 4 | 4 | 4 |
| L21.0 | 1 | 2 | 2 | 4 | 3 | 2 |

## Agents a outils : usage des outils

- agent_sonnet : n=67, appels/tour med 2 max 10, 0 appel sur 13 tours, fiches lues med 0, latence med 17.97 s, erreurs 0
- agent_mistral : n=67, appels/tour med 4 max 16, 0 appel sur 13 tours, fiches lues med 1, latence med 8.54 s, erreurs 0

## Multi-tour (tour >= 1) vs premier tour

| systeme | tour 0 : ref / compr | tour >= 1 : ref / compr | n1 |
|---|---|---|---|
| local | 2.05 / 2.05 | 2 / 2.29 | 7 |
| claude_ctx | 3.33 / 3.84 | 3.57 / 4.29 | 7 |
| claude_norag | 3.47 / 4.1 | 3.5 / 4.5 | 6 |
| gpt_norag | 3.9 / 4.07 | 3.86 / 4.43 | 7 |
| agent_sonnet | 3.54 / 4.2 | 3.71 / 4.43 | 7 |
| agent_mistral | 2.76 / 3.34 | 2.86 / 3.57 | 7 |

## Pires tours de local (moyenne 4 criteres)

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
- E08.0 1/2/2/1 [generation] 'Je veux faire une annee de cesure apres ma L2 pour voyager et bosser. Comment on fait et e' : La césure est une procédure encadrée de culture générale (demande motivée auprès de l'université, avis du président, convention, statut étudiant conservé avec i
- E13.0 1/2/2/1 [generation] "Je suis en M1 biologie, je veux faire un doctorat. Comment on trouve un financement et c'e" : La reponse esquive totalement la question : le financement de these (contrat doctoral d'etablissement ~2 200 € brut/mois, concours des ecoles doctorales en mai-
- E14.0 1/2/2/1 [generation] "Je suis accepte en master marketing en alternance mais j'ai pas d'entreprise. Si je trouve" : La question est procédurale (délai légal de signature du contrat d'apprentissage : jusqu'à 3 mois après le début de la formation, possibilité d'inscription prov
- E27.0 1/2/2/1 [generation] "Ingenieur diplome d'ecole vs master universitaire en informatique : difference de salaire " : La question est standard et documentée (enquête CGE : ~38-40 k€ brut annuel pour un ingénieur informatique en 2025, ~33-36 k€ pour un master universitaire, écar
- L03.0 2/2/2/1 [generation] 'Je veux devenir medecin, je suis a Bordeaux. PASS ou LAS ? Et est-ce que je peux faire la ' : Le cœur de la question (différence PASS/LAS, existence d'une L.AS option santé à Bordeaux, possibilité d'une LAS psychologie) est esquivé alors qu'une fiche L.A

## Erreurs factuelles relevees (local)

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

### Erreurs factuelles claude_norag (26)

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

### Erreurs factuelles gpt_norag (1)

- E21.0 : Le corps des contrôleurs du travail est en extinction depuis 2013 (fusion dans le corps de l'inspection du travail) : il n'y a plus de concours externe de contrôleur du travail. Mineur : le concours C

### Erreurs factuelles claude_ctx (22)

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
