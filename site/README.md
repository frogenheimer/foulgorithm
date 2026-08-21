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
site. Set it under Settings, General, Root Directory, then redeploy.

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
