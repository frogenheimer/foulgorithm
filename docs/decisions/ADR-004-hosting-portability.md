# ADR-004 — Host on Vercel Hobby, stay portable to Cloudflare

**Status**: Accepted
**Date**: 2026-08-21

## Decision

Deploy the site to Vercel's free Hobby tier, and write it using only portable Next.js features so it can move to Cloudflare Pages without a rewrite.

## Context

Vercel Hobby is free and excellent, and its terms restrict it to non-commercial use. The project is free today and intends to charge eventually. The moment money is involved, staying on Hobby is not an option.

The restriction is broader than "do not sell things". Verified from Vercel's fair use guidelines on 21 August 2026:

> **Hobby teams** are restricted to non-commercial personal use only. All commercial usage of the platform requires either a Pro or Enterprise plan.
>
> Commercial usage is defined as any Deployment that is used for the purpose of financial gain of **anyone** involved in **any part of the production** of the project [...]
> - Any method of requesting or processing payment from visitors of the site
> - Advertising the sale of a product or service
> - **Affiliate linking is the primary purpose of the site**
> - The inclusion of advertisements

Asking for donations also counts. So a paywall, ads, affiliate-led content or even a tip jar all end Hobby eligibility. A purely free site with no monetisation of any kind stays compliant, which is where we are.

Cloudflare's free tier, by contrast, carries **no non-commercial restriction**. Its terms were checked for "non-commercial" and "personal use" and neither appears. One clause does matter later: free services may not be used to process or collect credit card information, so a paid phase needs hosted checkout on a separate domain.

Two smaller Vercel facts, both verified: Hobby has **no monthly build-minute quota** (the limits are 45 minutes per deployment and 100 deployments per day), and Hobby **cannot connect to repositories owned by GitHub organisations**, only personal ones.

Choosing a host that permits commercial use from the start would avoid the migration entirely, but Vercel gives the best developer experience for Next.js and the migration is only painful if we make it painful.

## Options considered

**Start on Cloudflare Pages.** Free tier permits commercial use, so no future migration. Rejected for now because the Next.js developer experience is better on Vercel and this project needs iteration speed more than it needs to avoid a future afternoon of work.

**Start on Vercel Pro.** Costs money. Violates the hard zero-cost constraint.

**Static export to any host.** Maximum portability, but gives up incremental revalidation and makes the realtime matchday experience awkward.

**Vercel Hobby with a portability rule.** Chosen.

## Consequences

- The following are banned in the site codebase: Vercel KV, Vercel Postgres, Vercel Blob, Edge Config, Vercel Analytics, and any middleware pattern that only works on Vercel's runtime. Supabase provides all of these needs anyway.
- Preview deployments stay off, to conserve build minutes.
- A migration checklist gets written before the first paid user, not after.
- If Vercel's terms or free tier change, we move rather than pay. That is a design constraint, not a preference.
