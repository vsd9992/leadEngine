# leadEngine

A local lead discovery, qualification, and email verification dashboard. Find businesses by city and category, review evidence from their websites, then verify selected prospects' business email addresses in a separate step.

- **Find leads** searches Overture Places. The local model can correct spelling and expand related terms.
- **Qualify** defaults to the COOHOM prospect identifier. The 50-point rubric prioritizes customer-facing design and sales workflows, especially modular kitchens, wardrobes, and custom furniture. A custom campaign mode is available.
- **Verify** uses saved qualified contacts and the configured Reoon or Verifalia account. Review the queue before manual outreach.

## Quick start

On Arch Linux with Chromium's native libraries, uv, and a reachable llama.cpp endpoint:

```sh
./install.sh
./bin/leadengine-discovery-setup
./bin/leadengine-web --bind 127.0.0.1
```

Open <http://127.0.0.1:8080/>. Sign in as `leadengine` with the password generated in `state/web/password`. See the [detailed how-to](HOWTO.md) for LAN deployment, browser and model setup, the scoring rubric, CSV imports, verification credentials, and troubleshooting.

Discovery results are directory records. Qualification uses website excerpts and may leave company fields unknown when evidence is sparse. See [Overture Places](https://docs.overturemaps.org/guides/places/) and [GeoNames](https://www.geonames.org/) for data provenance.

The code is available under the [MIT License](LICENSE). Upstream directory data retains its source terms. COOHOM is a third-party product and brand.
