# Request: keys and one billing check (2026-11-19)

Nothing below blocks the free lanes (literature, design, testbed build, tests). It blocks the independent review and every multi-backbone run.

## 1. Reviewer key (needed now)

- **Role:** read-only cross-family reviewer for the Phase E memo, the pre-registration v3 and the analysis code.
- **Model wanted:** DeepSeek V4.1 Flash (used in the earlier review rounds), or any model that is not from the Muse family and not from the family that wrote the code under review.
- **How to supply:** add `Reviewer_Base_Url`, `Reviewer_API_Key` and `Reviewer_Model` to `.env`. One key for this role only.
- **Expected spend:** under Rs.50 for three review rounds (**assumed**: about 150k input and 30k output tokens per round at the listed price of about $0.15 / $0.60 per million tokens).

## 2. Backbone keys (needed before the confirmatory campaign)

The design needs at least three model families or tiers. Candidates, with prices still to be verified at the time of the run:

| Role | Candidate | Variables |
|---|---|---|
| Backbone A (have) | `meta/muse-spark-1.3-contributor` via AiCredits | `AiCredits_*` |
| Backbone B | DeepSeek V4.1 Flash | `BackboneB_Base_Url`, `BackboneB_API_Key`, `BackboneB_Model` |
| Backbone C | a Claude model (small tier) or Muse Wonder | `BackboneC_*` |
| Monitor (different family from the agent under test) | may reuse B or C as a *model*, but with its own key | `Monitor_*` |
| Task author (different model from every model under test) | any other family | `Author_*` |

If AiCredits serves several of these, separate keys on the same account are enough: the rule is one key per role, so spend and failures can be attributed.

## 3. One billing check (five minutes)

The audit found that the client silently retried each failed request up to twice (SDK default), so some HTTP requests were never logged. The ledger equals our logs, but it has never been compared with the provider's own figure.

- Please read the total billed amount for the AiCredits key from the provider's usage page, for 2026-11-04 to today, and note it here or in a reply.
- Ledger total for comparison: **Rs.286.64** (study) plus about Rs.250 of early development runs outside the ledger (**reported**, deviation D2).
- A gap much larger than that means cut-off generations were billed, which changes the cost model for long reasoning calls.

## 4. Human annotation (later)

A blinded label check of the IrrevOps v3 task set (is each should-abstain item really harmful, is each should-act item really safe) needs about two to three hours from a person who did not author the tasks. This is requested now so it can be scheduled; the tasks will be ready after the pilot.
