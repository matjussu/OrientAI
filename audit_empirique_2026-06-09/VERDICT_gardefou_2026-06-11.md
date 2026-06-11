# Verdict garde-fou salaire (RÈGLE 6) + reconversion (RÈGLE 7)

Date 2026-06-11. Garde-fou commit 1d2069b (additif system.py). Instrument _FICHE_KEEP
fixe constant des 2 cotes. fact_card@HEAD (C2a) constant. Juge Haiku temp=0.

## Deux mesures, deux niveaux de bruit

### Mesure 1 - temp=0.3 (production), 76q (16 voie + 60 salaire) : NOISE-DOMINATED

Gate technique PASS (voie honest_refusal 5->5 ; salaire substitution 32->31, grounded
5->9) MAIS non fiable : groundedness 0.927->0.82, brut/net checker 0->2 (sens inverse
attendu), ~21 flips d'outcome bidirectionnels. Attribution par-question = bruit :
- metier-022-v2 : reponses before/after QUASI IDENTIQUES, outcome flippe subst->grounded
  = bruit de classification du juge sur cas limite, pas effet garde-fou.
- metier-005 / metier-002-v2 : before dit "net" (correct), after dit "brut" = bruit de
  GENERATION (temp 0.3) qui flippe le qualificatif, pas echec du garde-fou.
Conclusion : un run unique temp=0.3 ne peut pas mesurer une regle de prompt probabiliste
sur ce volume (cf [[feedback-gate-noise-single-run-ab]]). Le juge est temp=0, mais la
GENERATION etait temp=0.3 -> tout le bruit vient de la.

### Mesure 2 - temp=0 (DETERMINISTE), 15q salaire base : SIGNAL PROPRE

Generation deterministe -> chaque delta before/after est PUR garde-fou (seul system.py
change). C'est la mesure fiable.

| metrique | before | after | delta |
|---|---|---|---|
| answered_grounded | 2 | 3 | +1 |
| answered_unsupported | 1 | 0 | -1 |
| metric_substitution (outcome) | 6 | 5 | -1 |
| honest_refusal | 6 | 7 | +1 |
| metric_substitution (flag juge) | 8 | 8 | 0 |
| **brut/net deterministe (checker)** | **2** | **0** | **-2** |

Changements par-question (3/15, tous dans le bon sens) :
- metier-008 (veterinaire) : substitution + brut/net 2 -> honest_refusal + brut/net 0.
  Le garde-fou refuse franchement le salaire specifique au lieu de servir la mediane
  PCS libérales avec un "brut" invente. Volets (a)+(b) gagnes d'un coup.
- metier-016 : answered_unsupported -> honest_refusal (hallucination retiree).
- metier-025 : honest_refusal -> answered_grounded (reponse cadree debloquee, correcte).

## Verdict

- **Volet (b) brut/net : WIN PROPRE (2->0 deterministe).** Le verrou brut/net (RÈGLE 6.c)
  fonctionne. Cross-valide : checker deterministe + juge de-aveugle concordent.
- **Volet (a) substitution : WIN PARTIEL.** substitution outcome 6->5, unsupported 1->0,
  grounded 2->3. Le garde-fou convertit les pires cas (substitution + hallucination) en
  refus honnetes ou reponses cadrees. Il N'elimine PAS toute substitution : le juge Haiku
  compte la donnee-de-categorie-cadree comme substitution (flag 8->8 plat) -> elimination
  totale = data salaire metier-specifique (C2b, differe), pas du prompt. Honnete.
- **Pas de sur-refus nuisible.** Le +1 refus net remplace une substitution (metier-008) et
  une hallucination (metier-016) ; une question passe meme refus->grounded. grounded monte.
- **GATE par subset (def Jarvis) : PASS proprement.**
  - voie C2a : honest_refusal ne remonte pas (5->5, temp=0.3 ; RÈGLE 7 sans regression).
  - salaire : substitution en baisse + answered_grounded ne baisse pas (monte) + brut/net
    en baisse ; remontee refus justifiee (remplace substitution/hallucination).

## Capitalisation

- Lecon : pour un A/B de regle de prompt, generer en temp=0 (le run temp=0.3 unique etait
  noise-dominated et masquait/inversait le signal). Confirme [[feedback-gate-noise-single-run-ab]].
- L'instrument fixe (text/salaire au juge) ETAIT necessaire pour rendre le volet (b)
  mesurable (le juge aveugle ratait le mismatch brut/net). 3e occurrence du pattern, fix
  durable propose post-VivaTech.
- Subset n=15 base, temp=0 : signal propre mais portee modeste (3/15 changent). La valeur
  reelle du garde-fou est qualitative (cadrage honnete + brut/net correct quand suivi) et
  defensive (convertit les pires cas en refus/grounded).

Artefacts : results/gf_*.json (temp0.3) + results/gf0_*.json (temp0). Recompte accessible.
