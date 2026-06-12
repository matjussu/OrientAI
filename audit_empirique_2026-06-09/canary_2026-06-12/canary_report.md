# Canary juge groundedness — 30 réponses figées du gel

Re-jugement avec le juge ACTUEL (claude-haiku-4-5-20251001) des réponses+sources STRICTEMENT identiques au gel 2026-06-11.

## Accords verdict par verdict

- **outcome identique : 30/30 = 100.0%** (seuil PASS 95%)
- groundedness identique (exact) : 25/30 = 83.3%
- hallucinated_numbers flag identique : 27/30 = 90.0%
- |Δ groundedness| moyen (cas chiffrés) : 0.0300
- relabels bénins (grounded<->alt_disclaimed à g=1.0) : 0
- mismatches SUBSTANTIELS (fidélité) : 7

## Verdict

**PASS-AVEC-RESERVE** — outcome 100.0% >= seuil MAIS 7 mismatch(es) substantiel(s) sur l'axe fidélité. À arbitrer : noise isolé ou début de drift ? Voir détail ci-dessous.

## Mismatches substantiels (détail)

| id | outcome stocké | outcome re-jugé | g stocké | g re-jugé | hallu stocké | hallu re-jugé |
|---|---|---|---|---|---|---|
| geo-013 | answered_unsupported | answered_unsupported | 0.833 | 0.833 | True | False |
| metier-004-v1 | answered_grounded | answered_grounded | 0.9 | 1.0 | True | False |
| reconv-002-v1 | answered_unsupported | answered_unsupported | 0.0 | 0.2 | True | True |
| malform-003-v2 | answered_unsupported | answered_unsupported | 0.8 | 0.833 | True | True |
| malform-003-v3 | answered_unsupported | answered_unsupported | 0.8 | 0.8 | True | False |
| metier-004-v3 | answered_grounded | answered_grounded | 0.75 | 0.857 | True | True |
| fact-002-v3 | metric_substitution | metric_substitution | 0.75 | 1.0 | False | False |
