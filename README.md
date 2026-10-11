# Cheryl's Newscast

Private podcast feed for Topher's Cheryl dayparted news editions — morning,
midday, and evening briefings read by Cheryl Tunt.

- **Feed:** http://hearth.ts.secwarz.com/feed.xml
- **Host:** hearth (nginx vhost `cheryl-news`, default on :80,
  root `/var/www/cheryl-news`)

## How it works

Each edition worker runs `publish_edition.py` after the MP3 passes QC:

```
publish_edition.py --mp3 <file> --edition morning --date 2026-10-11 \
    --duration-sec 380 --stories-file stories.txt
```

That copies the MP3 to hearth, registers the episode in `episodes.json`,
rebuilds `feed.xml` via `generate_feed.py`, deploys it to hearth, and
commits here. Publishing is idempotent — re-running updates the entry
instead of duplicating it.

## Files

- `generate_feed.py` — builds `feed.xml` (RSS 2.0 + iTunes tags) from `episodes.json`
- `publish_edition.py` — the worker-facing publisher (see above)
- `episodes.json` — episode registry (the source of truth)
- `feed.xml` — generated feed, committed for history
- `art/cover.jpg` — podcast cover art (also deployed to hearth)
