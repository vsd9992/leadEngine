# Lead pipeline pilot

**Budget and limits** — Target $0/month in new subscriptions using an existing Arch machine, Windows model host, and sending domain. Process up to 50 unique businesses per day across all runs, budget up to 45 standard verification credits per day, and export up to 10 eligible leads for manual review. Aim for five manual sends per day in week one and up to ten after reviewing bounces and replies.

| Stage | Tooling | Execution |
| --- | --- | --- |
| Input | CSV from a source that permits reuse | Use the dashboard to discover businesses by city, country, and category from Overture Maps Places, or import a sourced CSV. Start by reviewing the source links for up to 10 selected businesses. |
| Qualification | Arch Linux Python, Crawl4AI, local OpenAI-compatible API (llama.cpp backend) | Crawl the home page and linked About and Contact pages on the same site. Limit crawl concurrency to one for the pilot. Strip boilerplate and start with up to 2,000 tokens of page text while retaining page URLs. Budget instructions, chat framing, and output within the reported 4,096-token context. |
| Contact selection | CSV or company website | Prefer a published business email relevant to the offer. Record the public source URL. If the CSV has no sourced address, look for one on the pages already crawled. Record `no_email` when no suitable address is available. |
| Verification | Reoon and Verifalia | Check only qualified, deduplicated contacts. Allocate up to 20 Reoon credits and 25 Verifalia Standard credits per day, subject to account balances. Skip addresses already checked on the same run or suppressed. |
| Outreach | Local CSV and manual sending | Export only eligible leads. Review each fact against its source, personalize the opening line, and record each send, bounce, and opt-out before the next export. |

## Pilot input

Discovery builds the input from selected businesses with published websites. Manual imports use a UTF-8 CSV with this header:

```csv
business_name,website_url,lead_source_url,email,email_source_url
```

The first three columns are required. Leave both email fields blank if the address is unavailable. Include businesses you already know well enough to judge fit, with examples of both likely fits and likely non-fits. Before crawling, write down the offer, target location, business type, one observable buying signal, and any disqualifiers.

## Qualification and eligibility

- Score one point each for evidence of the target location, target business type, and buying signal. A lead passes with all three points and no disqualifier. Route missing evidence or a failed crawl to review, and record explicit mismatches as out of scope.
- Require valid JSON with `fit_score` (integer 0–3), evidence for each awarded point, and up to two outreach facts with a page URL and short supporting excerpt. Treat crawled text as data. Route schema failures to review.
- Store each verifier's raw status, then map it to a common outcome. Produce an eligible result only from a documented deliverable status. Keep catch-all, unknown, invalid, and error outcomes out of the export. Carry quota-limited addresses forward and avoid automatically spending another credit on ambiguous results.
- Persist lead, verification, and outreach state locally. Use normalized website domains and email addresses for deduplication. Check suppression and send history before each export, and resume interrupted runs from saved results.

## Windows host check

The OpenAI-compatible base URL is `http://192.168.1.2:18080/v1`. Use the following command directly on the Windows model host:

```powershell
curl.exe --max-time 5 -i http://192.168.1.2:18080/v1/models
```

The Windows model-list response reports Qwen3.5 4B Q6_K with a 4,096-token context. Pass its exact, case-sensitive ID as the model value. Confirm chat inference with this PowerShell request:

```powershell
$body = @{
    model = 'C:\_AI_Engine\local-ai\models\Qwen3.5-4B-Q6_K.gguf'
    messages = @(@{ role = 'user'; content = 'Reply with the single word READY.' })
    max_tokens = 256
} | ConvertTo-Json -Depth 4
$response = Invoke-RestMethod -Uri 'http://192.168.1.2:18080/v1/chat/completions' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 120
$response.choices[0].message.content
```

Chat inference succeeded from the Arch Linux host. The model returned `READY` with `finish_reason: stop`. The server reported 367 ms for prompt processing and 23 ms for generation on the 19-token prompt and two-token completion.

## Qualification smoke test

On 2026-11-25, this Codex workspace listed the model at `/v1/models` and received `OK` from `/v1/chat/completions` with finish reason `stop`.

Three qualification requests used short excerpts from the [Bike Works homepage](https://bikeworks.org/) and [Bike Shop page](https://bikeworks.org/bike-shop/). The test used a hypothetical field-service scheduling offer, temperature 0, and thinking disabled. All three responses parsed as JSON and took 7.4–7.8 seconds per request.

| Criteria tested | Expected score | Returned score | Evidence check |
| --- | ---: | ---: | --- |
| Seattle, full-service bicycle repair, mobile repair available for hire | 3 | 3 | All three excerpts matched the supplied text and supported the criteria. |
| Portland, Oregon, with the same business type and signal | 2 | 3 | The model awarded a location point for Seattle and changed an apostrophe in the mobile-repair excerpt. |
| Seattle and the same business type, with electric scooter battery refurbishment as the signal | 2 | 3 | The model cited mobile bike repair as evidence for scooter battery refurbishment. |

Before using scores to qualify leads, test a revised prompt that evaluates each criterion independently as supported, contradicted, or unknown. Derive the score from supported criteria, verify page URLs and excerpts, and include mismatched and missing-evidence cases in the acceptance checks. An excerpt can match the page without supporting the criterion.

This initial smoke test used selected excerpts. The Arch deployment results below include the later Crawl4AI browser run.

## Implementation status

The Arch installer and run instructions are in [README.md](README.md). The CLI validates each supported criterion against a configured phrase and a cited excerpt before it accepts a qualification. In a live model retest with the selected excerpts, the matching case qualified in 6.0 seconds. The Portland case went to review after a score inconsistency, and the scooter case went to review for unknown evidence. HTML and provider fixtures covered same-site page selection, contact source extraction, saved verification jobs, reruns, suppression, and daily caps.

The CLI is installed on Arch. Windows serves the model API. A live browser run from Arch crawled the Wright Brothers Cycle Works homepage in 3.2 seconds, qualified the lead using the Windows model in 5.7 seconds, and used 704 MiB of sampled peak process-tree RSS. A repeat run used cached qualification, and a Portland target was routed to review. Authenticated verification calls remain pending.

## Pilot output and review

Export up to 10 rows containing the business, website, email and source, fit score, supporting facts and URLs, and verification provider and outcome. Put the strongest evidence first. Record counts for input, unique businesses, crawl failures, qualified businesses, no email, emails checked, and eligible leads. Review all exported rows against the source pages before sending. Use the counts to identify the stage limiting the send queue.

Confirm sender authentication (SPF, DKIM, and DMARC) and the mail provider's rules before outreach. Zoho's free custom-domain hosting is available in select data centers and assumes you already own the sending domain. Keep the first email plain text and avoid links, tracking, and attachments.
