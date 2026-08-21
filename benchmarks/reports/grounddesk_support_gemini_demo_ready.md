# GroundDesk Product-Specific Evaluation

- **Embedding backend/model:** `gemini` / `gemini-embedding-2`
- **Generation:** `gemini` / `gemini-2.5-flash`

## Strategy: `hybrid+lexical`

### Results

- **Dataset:** `grounddesk_support_v1` v1.0
- **Corpus:** `corpus`
- **Cases:** 21 (16 answerable, 5 no-answer/ambiguous, 5 follow-up)
- **Review status:** engineer-authored baseline; manually review before presenting results as release quality
- **Generation mode:** `provider`
- **Generation models used:** `gemini-2.5-flash, gemini-2.5-flash-lite`
- **Retrieved citations per answer (top_k):** `3`

## Product Behavior Metrics

| Measure | Score |
| --- | ---: |
| Relevant evidence retrieved for answerable cases | 100.0% |
| Correct top citation for answerable cases | 100.0% |
| Citation precision for answerable cases | 33.3% |
| Expected answer-term coverage | 93.8% |
| Escalation decision accuracy, all cases | 85.7% |
| Unsupported/ambiguous case escalation accuracy | 100.0% |
| Follow-up correct top citation with context | 100.0% |
| Follow-up correct top citation without context | 100.0% |

## Interpretation Boundary

- This is a small product-specific evaluation over the bundled demo knowledge base; it is useful for regression and demonstration, not a customer-scale accuracy claim.
- Relevant evidence and escalation labels are explicit. Expected answer-term coverage is a proxy and does not replace human judgement of generated-answer correctness.
- In `template` mode the report tests the retrieval/evidence/escalation pipeline deterministically; run Gemini mode and manually review outputs before discussing live-generation quality.
- Follow-up comparison measures whether stored conversational context improves evidence selection for underspecified later questions.

## Failed or Weak Cases

| Case | Category | Top citation | Expected | Escalation hit | Answer-term hit |
| --- | --- | --- | --- | --- | --- |
| `auth_sso_checks` | answerable | authentication | authentication | no | yes |
| `usage_invite_expiry` | answerable | product_usage | product_usage | no | no |
| `followup_large_export_delivery` | follow_up | product_usage | product_usage | no | yes |
