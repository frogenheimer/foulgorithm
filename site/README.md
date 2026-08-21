# Site

Next.js front end. Static, no backend: Python writes JSON into `public/data/`
and the pages read it at build time.

Pages: this round's predictions, the five characters and one page each,
26 seasons of history, and methodology.

See [docs/08-site.md](../docs/08-site.md) for scope and interaction design, and
[docs/ui-styleguide.md](../docs/ui-styleguide.md) before any UI change.

## Deploying

**Vercel Root Directory must be set to `site`.**

This repository is a Python package at the root with the Next.js app in a
subdirectory. Vercel auto-detects from the root, finds `pyproject.toml`, decides
this is a Python project and fails with:

```
Error: No python entrypoint found. Set "tool.vercel.entrypoint" in pyproject.toml
```

That error means Root Directory is unset, not that anything is wrong with the
site. Set it under Settings, Build and Deployment, Root Directory, then redeploy.

**Resolved by static export instead.** `next.config.mjs` sets
`output: "export"`, so the build produces plain HTML in `site/out/`, and the
root `vercel.json` points install, build and output there. No framework
detection is involved, so no Root Directory setting is needed.

An earlier attempt set `"framework": "nextjs"` in `vercel.json`. That failed
with "No Next.js version detected", because the Next.js preset looks for
`package.json` in the directory it builds from and the repository root has
none. Pointing at a static output directory sidesteps framework detection
altogether.

Every page was already prerendered, so the export costs nothing. It also
delivers the portability [ADR-004](../docs/decisions/ADR-004-hosting-portability.md)
asks for: the output is plain files that any host can serve, so moving off
Vercel is a copy rather than a rebuild.

Everything the site needs lives inside `site/`, including the JSON in
`site/public/data/`, so nothing outside the root directory is required.

## Portability rule

This app runs on Vercel Hobby today and must be able to move to Cloudflare Pages without a rewrite, because Vercel Hobby forbids commercial use and this project intends to charge eventually. See [ADR-004](../docs/decisions/ADR-004-hosting-portability.md).

**Banned:** Vercel KV, Vercel Postgres, Vercel Blob, Edge Config, Vercel Analytics, and any middleware pattern tied to Vercel's runtime.

Supabase covers every one of those needs, so this costs nothing.

## Data access

- Supabase JS client with the **anon key only**. The service role key must never reach the browser or this directory.
- Row level security is the access control. The client is not trusted.
- Static generation with incremental revalidation wherever possible, so page views do not trigger work.
- Supabase Realtime on match days only, for live lineup updates.

## Non-negotiables

- Every probability displayed with its uncertainty.
- Losing periods shown as prominently as winning ones.
- 18+ and BeGambleAware signposting persistent in the footer.
- No hype language, no urgency, no countdowns, no guaranteed-return framing.

See [docs/13-legal-and-ethics.md](../docs/13-legal-and-ethics.md).
