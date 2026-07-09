# Jobhuntbot

Pings you on Discord when a **new-grad job matching your profile** is posted to
[zapplyjobs/New-Grad-Jobs-2027](https://github.com/zapplyjobs/New-Grad-Jobs-2027).

Runs **free** on GitHub Actions cron — no server, no need to leave your computer on.

## How it works

Every 20 minutes a scheduled Action:

1. Fetches the source repo's `README.md` (its committed job table, refreshed ~every 15 min).
2. Parses each row into a job (company, title, location, visa, apply URL).
3. Keeps only jobs matching [`config.yaml`](config.yaml): **Data/ML roles**, **California/US**
   locations, **sponsor-friendly** visa.
4. Posts new matches to Discord as embeds.
5. Records seen apply URLs in [`state/seen.json`](state/seen.json) (committed back) so you're
   never pinged twice.

The **first run seeds state silently** so you aren't flooded; after that you only hear about
genuinely new postings. A `per_run_cap` (default 15) guards against bursts.

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

- `roles.include` / `roles.exclude` — title keywords to match / block.
- `location.include` — allowed location substrings (delete `remote` to force on-site CA).
- `location.reject_if_contains` + `us_only` — hard blocks for non-US rows.
- `visa_required` — set `false` if you don't need sponsorship.
- `per_run_cap`, `prune_after_days` — safety valves.

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

- Long titles are **truncated with `…`** in the source table; a role keyword past the cutoff
  can be missed. Embeds flag truncated titles so you can spot-check.
- GitHub cron can be delayed a few minutes under load, and **pauses scheduled workflows after
  60 days of repo inactivity** — the per-run state commit keeps the repo active, so it won't
  trip in normal use.
