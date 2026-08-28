# The clock: a scheduler that fires on time

**Status: Proposed 2026-08-28. Code in `ops/clock/`, needs two accounts to
switch on. Becomes Decided when the first dispatched run appears in Actions.**

GitHub's *schedule* trigger ran this repo's wakes about two hours late on
every run from 23 to 25 August and not at all on the 28th, when the confirmed
elevens had to be published by hand. Its *dispatch* API runs a workflow
immediately. So every job stays exactly where it is, and only the clock moves.

> 💡 **The one design rule.** The clock knows nothing about our jobs except
> when they are due. It reads `season.json` from the repo every 30 minutes and
> presses the button. If it dies, the backbone crons in `lineups.yml` are still
> there; if both die, the settle audit line says MISSING.

---

## 🎯 What runs where

| Piece | Where | Cost |
|---|---|---|
| Lineups, settle, reschedule jobs | GitHub Actions, unchanged | Free: public repository |
| The clock | Cloudflare Worker, cron every 30 min | Free plan: 100,000 requests a day, we use 48 |
| The fixture list it reads | `season.json` via raw.githubusercontent.com | Free, no token |

**Why it can never cost money.** The Cloudflare account carries no payment
method: the Free plan cannot bill, it stops. GitHub Actions minutes are
unlimited on public repositories. The token is scoped to one repository and
one permission and expires; the worst a leak can do is start our own jobs.

---

## 🚦 Setup, in order

1. **GitHub token.** Settings → Developer settings → Fine-grained tokens →
   Generate. Repository access: *only* `frogenheimer/foulgorithm`. Permissions:
   Actions **Read and write**, nothing else. Expiry: 1 year. Copy it once.
2. **Cloudflare account.** Sign up at dash.cloudflare.com. Do **not** add a
   payment method. Workers → the Free plan is the default.
3. **Deploy**, from `ops/clock/` in a terminal:
   ```
   npm install
   npx wrangler login          # opens the browser once
   npx wrangler secret put GITHUB_TOKEN   # paste the token
   npx wrangler deploy
   ```
4. **Check.** `npx wrangler tail` shows each 30-minute tick and what it
   dispatched. The first dispatched run appears under Actions with event
   `workflow_dispatch`.
5. **Renew the token** in a year. Put it in the calendar now.

---

## ✅ What "due" means

| Job | Fires when | Then |
|---|---|---|
| lineups | a kickoff is 60 to 130 minutes ahead | the watcher waits until T-65, polls each minute, publishes at the sheets |
| settle | a matchday's last kickoff was 4h00 to 4h30 ago | grades, refreshes, marks, evolves |
| reschedule | Tuesday 04:00 to 04:30 UTC | regenerates the backbone's generated block |

Each window is 30 minutes wide and the clock ticks every 30 minutes, so a
job is dispatched once. A second dispatch on a boundary queues behind the
first in the workflow's concurrency group and exits in a minute.

---

## ⚠️ Pitfalls

- The token is the only secret. Never commit it; `wrangler secret put` stores
  it in Cloudflare.
- Kickoff moves reach the clock the moment `season.json` is pushed, which
  settle does after every matchday and reschedule weekly.
- If Cloudflare ever changes the Free plan's terms to require a card, delete
  the worker. The backbone crons take over, two hours late but present.
