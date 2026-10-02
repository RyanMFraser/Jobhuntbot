# Jobhuntbot

Pings you on Discord when a **new-grad software / AI / ML engineering job in California** is
posted to any of these lists:

- [SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions)
- [speedyapply/2027-SWE-College-Jobs](https://github.com/speedyapply/2027-SWE-College-Jobs)
- [vanshb03/New-Grad-2027](https://github.com/vanshb03/New-Grad-2027)
- [zapplyjobs/New-Grad-Jobs-2027](https://github.com/zapplyjobs/New-Grad-Jobs-2027)

Runs **free** on GitHub Actions cron — no server, no need to leave your computer on.

## How it works

Every 20 minutes a scheduled Action:

1. Fetches every source in [`config.yaml`](config.yaml) (a failing source is skipped, not fatal).
2. Parses each listing into a job (company, title, location, posted time, visa, apply URL).
3. Keeps only jobs that are:
   - **SWE / AI / ML-type roles** (`roles`),
   - **new grad** (`new_grad`): interns, level II+, senior, etc. are dropped. zapply also lists
     experienced roles, so its titles must explicitly say new grad / early career / associate / etc.,
   - in **California** (`location`),
   - not explicitly closed to sponsorship (`visa`).
4. Drops repeats of the same job listed by several sources.
5. Posts new matches posted in the last `max_age_days` to Discord as embeds.
6. Records seen jobs (apply URL + company/title) in [`state/seen.json`](state/seen.json)
   (committed back) so you're never pinged twice.

Older postings that are new to the bot (e.g. after adding a source) are recorded silently
instead of flooding the channel. A `per_run_cap` (default 15) guards against bursts.

## Setup

1. **Create a Discord webhook**: Server Settings → Integrations → Webhooks → *New Webhook* →
   pick a channel → *Copy Webhook URL*.
2. **Add it as a secret**: in this repo, Settings → Secrets and variables → Actions →
   *New repository secret* → name `DISCORD_WEBHOOK_URL`, paste the URL.
3. **Enable Actions** (Actions tab → enable workflows if prompted).
4. Optionally edit [`config.yaml`](config.yaml) to tune roles/locations, then commit.

That's it — the bot runs on schedule. Trigger a run immediately from the **Actions → Hunt jobs
→ Run workflow** button.

## Editing your filters

Everything lives in [`config.yaml`](config.yaml):

- `sources` — the job lists to pull from, and whether each needs an explicit new-grad title.
- `roles.include` / `roles.exclude` — title keywords to match / block (whole words).
- `new_grad.exclude` / `new_grad.keywords` — what disqualifies a title / what counts as new grad.
- `location.include` — allowed California cities/keywords (add `remote` to also get remote roles).
- `location.reject_if_contains` — hard blocks for non-US rows.
- `visa` — `any`, `not_blocked` (default), or `sponsor_only`.
- `max_age_days`, `per_run_cap`, `prune_after_days` — safety valves.

## Local development

```bash
pip install -r requirements.txt
pytest                                    # run tests

# Dry run against the LIVE source: prints matches, sends nothing, writes no state.
DRY_RUN=1 python -m src.hunt

# Real run (posts to Discord, updates state/seen.json):
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." python -m src.hunt
```

## Notes & limits

- Long titles are **truncated with `…`** in the zapply table; a role keyword past the cutoff
  can be missed. Embeds flag truncated titles so you can spot-check.
- GitHub cron can be delayed a few minutes under load, and **pauses scheduled workflows after
  60 days of repo inactivity** — the per-run state commit keeps the repo active, so it won't
  trip in normal use.
