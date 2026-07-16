# Gate avant/apres - portage R8+R9 vers le prompt servi (H1 lot 1.1)

Ordre 2026-07-16-0905, mesure du 16/07. Golden 50q, temperature 0,
pipeline.answer local (index 52 040, cle Mistral post-regularisation).
Seul delta entre les deux runs : src/prompt/system_v4_strict.py
(AVANT = origin/main 3ff3f4c, APRES = portage R8/R9).

## Observables deterministes (analyze_motifs.py, regex, 50/50 questions, 0 erreur)

| Observable | AVANT | APRES | Lecture |
|---|---|---|---|
| r8_constat (constat d'absence explicite) | 7 | 13 | +86 %, motif R8 se systematise (net +6 : 9 gains, 3 pertes attribuees au bruit de generation) |
| r9_tag_avant (source annoncee avant le chiffre) | 7 | 18 | x2.6, direction voulue |
| r9_tag_apres (chiffre puis tag, motif legacy) | 150 | 165 | toujours dominant : R9 emerge mais n'est PAS encore systematique |
| bloc "Sources :" final (interdit R9) | 0 | 0 | RAS |
| n_mots moyen | 81.0 | 75.3 | pas de derive R6 |

Attribution par question dans la sortie d'analyze_motifs.py (aucune
regression concentree ; deltas disperses compatibles avec le bruit de
generation temp 0 cote serveur, cf feedback_gate_noise_single_run_ab).

## Groundedness (juge LLM) - EN ATTENTE

Le juge historique (claude-haiku, judge_groundedness.py) est bloque :
credits API Anthropic epuises ("credit balance too low", constate 16/07).
Options remontees a Jarvis/Matteo :
  a) recharge Anthropic (~2-3 EUR pour 2x50 jugements) -> comparabilite
     avec la baseline historique 0.945 preservee ;
  b) juge mistral-small (finance) -> delta A/B valide mais NON comparable
     a l'historique ;
  c) merger sur le gate deterministe seul (le portage est additif prompt-only,
     la suite pytest 3 185 est verte, l'inclusion est verrouillee par CI).
Les batteries AVANT/APRES sont versionnees ici : le juge peut etre rejoue
tel quel des que les credits existent.

## Verdict propose

Gate deterministe VERT (motifs en progression, zero regression structurelle,
longueur stable). Groundedness a rejouer des credits disponibles.

## Note hors scope (demande Jarvis)

Autres regles legacy candidates au portage, reperees pendant l'item,
NON portees (arbitrage ulterieur) : anti-chiffre-conversationnel,
anti-confession, regle geo ville d'implantation, biais interdisciplinaire,
glossaire anti-amnesie reformes, pyramide inversee Tier 2.
