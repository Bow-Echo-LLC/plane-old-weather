# Deploy runbook — Cloudflare Pages

planeoldweather.com is a static Astro build hosted on **Cloudflare Pages**
(static files, global CDN, automatic SSL — no server to run). The domain is
already on Cloudflare, so attaching it is a click. Two ways to deploy; do **A**
to go live in a couple of minutes, or **B** for hands-off auto-deploys on push.

The model asset bundle (`web/public/assets/model/`, ~17 MB / 362 files) ships
with the build — well within Pages' limits (25 MiB/file, 20k files).

Build settings (whichever method):

| Setting | Value |
|---|---|
| Framework preset | Astro |
| Root directory | `web` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Node version | 22 (pinned by `web/.nvmrc`) |

---

## A. Fastest — direct upload with Wrangler (no GitHub needed)

```bash
cd web
npm ci
npm run build
npx wrangler pages deploy dist --project-name=plane-old-weather
```

`wrangler` opens a browser to log in to Cloudflare the first time. When it
finishes you get a `https://plane-old-weather.pages.dev` URL — that's production.
(`web/wrangler.toml` already sets the project name and output dir, so
`npx wrangler pages deploy` with no args works too.)

## B. Recommended — connect the Git repo (auto-deploy on push)

1. Push the repo to GitHub (see "First push" below).
2. Cloudflare dashboard → **Workers & Pages → Create → Pages → Connect to Git**.
3. Pick the repo, then set the build settings from the table above (Root
   directory **`web`** is the important one for this monorepo).
4. **Save and Deploy.** Every push to `main` now builds and deploys automatically;
   pull requests get preview deployments.

(No GitHub Actions deploy workflow is needed in this mode — Pages builds itself.
`.github/workflows/deploy.yml` is an optional manual Wrangler deploy for people
who prefer Actions; it stays inert unless run.)

---

## Attach the domain (same for A or B)

1. In the Pages project → **Custom domains → Set up a custom domain** →
   `planeoldweather.com`. Cloudflare adds the DNS record and provisions the TLS
   cert automatically (the zone is already on your account).
2. Add `www.planeoldweather.com` too and set it to **redirect to the apex**
   (Custom domains lets you mark it as a redirect), or add a Cloudflare
   **Redirect Rule** `www → apex`.
3. SSL/TLS mode **Full (strict)** is fine — Pages serves valid certs end to end.

That's it — `https://planeoldweather.com` is live.

---

## First push (for method B)

```bash
# from the repo root, with the initial commit already made:
gh repo create plane-old-weather --public --source=. --remote=origin --push
# (or --private; Pages can connect to private repos)
```

Then update the placeholder URLs in `web/src/consts.ts` (`REPO_URL`, `DATA_URL`)
to the real repository, and the footer/methodology "Source"/"Raw data" links go
live too.

## Scaling note

If the model bundle's bandwidth ever matters, move `/assets/model/` to
**Cloudflare R2** (S3-compatible, same account) and point the manifest base URL
there — the documented scaling path. Not needed at launch.
