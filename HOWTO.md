# leadEngine on Arch Linux

leadEngine is installed in this workspace. The crawler, SQLite state, and review CSV run on Arch. Qualification uses the Qwen model at `http://192.168.1.2:18080/v1` on the Windows machine.

## Run your pilot

From the project directory, create your working files once.

```sh
cd /home/vishnu/leadEngine
cp -n campaign.example.json campaign.local.json
cp -n leads.example.csv leads.local.csv
```

Set your actual offer, target location, business type, buying signal, and disqualifiers in `campaign.local.json`. Each criterion requires literal phrase alternatives that could appear in a supporting excerpt. Keep those phrases specific to your offer. Start with up to ten known businesses and include likely matches and mismatches. Use sources that permit reuse and keep the CSV header as shipped. If you supply an email, include its public source URL.

Run qualification first with provider calls disabled.

```sh
./bin/leadengine run leads.local.csv --campaign campaign.local.json --skip-verification
```

Read the per-business JSON and the final counts. Inspect the cited excerpts for all three criteria. For a qualified business without a CSV contact, the crawler looks for a published same-domain business mailbox. If the model is unreachable, check that the Windows service is running and reachable from Arch.

```sh
curl --connect-timeout 3 --max-time 5 --fail-with-body http://192.168.1.2:18080/v1/models
```

The optional `--api` and `--model` arguments to `run` override the defaults. The server also needs to expose llama.cpp's `/tokenize` endpoint.

## Verify, review, and record outreach

Set `REOON_API_KEY` and/or `VERIFALIA_USERNAME` and `VERIFALIA_PASSWORD` in your shell using your usual secret handling. The Verifalia user needs permissions to read credits and submit and retrieve jobs. Then run with provider verification enabled.

```sh
./bin/leadengine run leads.local.csv --campaign campaign.local.json
```

Open `state/review.csv` and check every fact against its public source before sending manually. The queue includes only qualified contacts with a deliverable provider result, up to ten distinct leads in a UTC day. The pilot uses daily credits only and checks at most 20 addresses with Reoon Power and 25 with Verifalia Standard per UTC day. Ambiguous or interrupted submissions are held. Verifalia jobs with a saved ID are polled on subsequent runs.

Keep `state/leadengine.sqlite` across runs. It holds the 50-business daily cap, verification history, export reservations, and outreach events. Rerun the same files to resume. Updating campaign criteria causes the next run to qualify those sites again. Before generating another export, record each send, bounce, or opt-out. Use the respective event on each command.

```sh
./bin/leadengine record sent sales@example.com https://example.com
./bin/leadengine record bounce sales@example.com https://example.com
./bin/leadengine record opt_out sales@example.com https://example.com
```

Confirm sender authentication and your provider's rules before sending. Review email-provider results using the [Reoon API documentation](https://www.reoon.com/articles/api-documentation-of-reoon-email-verifier/) and [Verifalia result documentation](https://verifalia.com/developers/email-verifications/retrieving-jobs).

## Reinstall or repeat the deployment check

The installed CLI is launched through `bin/leadengine`. Its Python environment is in `.venv`, Chromium is in `.browsers`, and this machine's supplemental Chromium libraries are in `.runtime/libroot`. On this deployment the installer reuses the installed runtime and browser downloads. When installing the package into a fresh directory, supply `uv` and use a host with Chromium's native libraries available.

```sh
./install.sh dist/leadengine-0.1.0-py3-none-any.whl
./bin/leadengine --help
```

The smoke-test campaign and input are in `state/smoke` on this machine. Use the same database to check resume, or choose a fresh state path to repeat the live crawl and inference.

```sh
./bin/leadengine --state state/smoke/leadengine.sqlite run state/smoke/leads.csv \
  --campaign state/smoke/campaign.json --skip-verification
```

The live sample required 3.2 seconds to crawl and 5.7 seconds for inference, with 704 MiB of sampled peak RSS across Python and its browser processes. It qualified as a Seattle bike shop offering repair classes. A rerun used the cached result, and changing the target location to Portland routed the same site to review. Verification and suppression tests used simulated provider responses. [Wright Brothers Cycle Works](https://www.wrightbrotherscycleworks.com/)

## Use the LAN dashboard

Open [leadEngine](http://192.168.1.101:8080/) from a browser on the trusted local network. Sign in as `leadengine` with the dashboard password stored on Arch in `state/web/password`. The browser uses plain HTTP on the LAN. The password is separate from the provider key.

1. Open **Find leads** and enter a city, two-letter country code, business category, and search radius. The local model corrects likely spelling errors and suggests related terms. leadEngine searches Overture Maps Places for businesses with a listed website, shows the terms used, and labels related matches. Direct matches appear first. When the model is unavailable, discovery uses the original query with built-in spelling corrections. Select the businesses you want and click **Use selected leads**.
2. Open **Qualify** to confirm the target, set your offer and buying signal, and start qualification. An existing CSV can also be imported here. Review the results and their source links.
3. Open **Verify** and click **Verify qualified emails** when you want to use provider credits. The verification step reads saved qualifications and contacts. Download the review CSV after the run, then use **Record outreach** to log sent messages, bounces, and opt-outs.

Discovery returns up to 50 distinct website domains within 5, 10, or 20 km of a supported city center. It uses the GeoNames city index and Overture Maps Places, so directory coverage and category labels affect results. Browser runs and CLI runs share the default SQLite state. [Overture Places](https://docs.overturemaps.org/guides/places/) · [GeoNames](https://www.geonames.org/)

For a fresh install, populate the local city index after running the installer.

```sh
./bin/leadengine-discovery-setup
```

The local launcher reads the Reoon key from `_reoonAPI` unless `REOON_API_KEY` is set. Keep the file readable only by your Arch user. Verifalia credentials can be added later to the service environment.

The dashboard runs as the enabled Arch user service `leadengine-web.service`. Check or restart it from the Arch session with these commands.

```sh
systemctl --user status leadengine-web.service
systemctl --user restart leadengine-web.service
```

The service starts with the Arch user session. To start it manually when the user service is stopped, run `./bin/leadengine-web` in the project directory.

## COOHOM prospect qualification

The **Qualify** tab defaults to **COOHOM prospect identifier**. It combines the campaign settings into **Market**, **Prospect focus**, and optional **Research notes**. Default searches prioritize Delhi NCR modular kitchen and wardrobe studios, custom furniture, and retailers or manufacturers with design-led sales. Selecting businesses from discovery fills the market. Use **Custom campaign** for the original three-criterion workflow.

On Arch you can also run the preset directly.

```sh
./bin/leadengine run leads.local.csv --campaign campaign.coohom.json --qualify-only
./bin/leadengine run leads.local.csv --campaign campaign.coohom.json --verify-only
```

| Dimension | Maximum | Evidence to look for |
| --- | ---: | --- |
| Customer-facing design | 15 | Showrooms, design consultations, customization and design-led sales |
| Commerce reach | 10 | Dealers, stores, franchises, digital sales and geographic reach |
| Product alignment | 10 | Kitchens, wardrobes, cabinetry, interiors, modular systems and visualization needs |
| Commercial and digital viability | 10 | Published operating scale, digital maturity and catalog depth |
| Manufacturing integration | 5 | Documented CAD/CAM or standardized production with integration potential |

Scores are ranked as Strong (40–50), Good (32–39), Conditional (24–31), Weak (15–23), and Not Worth Pursuing (0–14). Pure production or missing evidence of a customer-facing commercial workflow caps the score at 23. Clear evidence that the company ceased operating caps the score at 14. Manufacturing contributes up to five points, and the Strong tier also requires at least 35 points across the other dimensions and at least 9 in customer-facing design. Outsourced production earns no manufacturing integration points and is otherwise neutral. Good and Strong prospects can enter the separate verification stage when a sourced email is available.

Expand a result to read its profile, score breakdown, website excerpts, evidence gaps, and the primary and optional secondary sales angle. Treat the suggested approach as a hypothesis for manual review. The local crawler starts with the homepage and follows relevant linked About, Contact, product and sales pages when available. It can miss dynamic content, pages behind a login, or facts that require independent research. In particular, confirm decision makers, revenue and headcount independently before relying on them. COOHOM's product site describes its design and visualization offerings. [COOHOM](https://www.coohom.com/)

## Troubleshooting

- **No discovery results** — Check the country code and city spelling. Try a closely related category or a wider radius. The service only returns businesses with listed usable websites.
- **Review or weak fit** — Open the evidence panel. A website with sparse content or blocked crawling may need manual research.
- **Verification deferred** — Check the provider credentials and the remaining daily balance. Pending Verifalia jobs resume from the same SQLite state.
- **Another run in progress** — Wait for that run to finish before starting another browser or CLI job against the same state.
- **Fresh copy cannot find the model** — Pass `--api` and `--model` to the CLI, or set `LEADENGINE_API_URL` and `LEADENGINE_MODEL` in the dashboard service environment. To run the dashboard on a different LAN, pass the Arch host address via `--bind` and the subnet via `--allow`. Update the user service path if you install elsewhere.
