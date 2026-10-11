#!/usr/bin/env python3
"""Publish a finished Cheryl news edition to the podcast feed.

Copies the MP3 to hearth, registers the episode, rebuilds feed.xml,
deploys it, and commits the repo. Idempotent: re-running with the same
file updates the entry instead of duplicating it.

Usage:
    publish_edition.py --mp3 <path> --edition morning --date 2026-10-11 \\
        --duration-sec 380 --stories-file stories.txt [--title "..."]

--stories-file: plain text, one story per line (the delivery story list).
Only call this for editions whose audio passed QC; never publish a
text-only fallback edition.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
EPISODES_JSON = REPO / "episodes.json"

SSH = ["ssh", "-F", "/home/hatch/.ssh/config", "hearth"]
SCP = ["scp", "-F", "/home/hatch/.ssh/config"]
REMOTE_DIR = "/var/www/cheryl-news"
REMOTE_EPISODES = REMOTE_DIR + "/episodes"

sys.path.insert(0, str(REPO))
import generate_feed  # noqa: E402


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def remote_size(path):
    try:
        out = run(SSH + ["stat", "-c", "%s", path])
    except RuntimeError:
        return None  # not there yet
    return int(out) if out.isdigit() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp3", required=True)
    ap.add_argument("--edition", required=True, choices=["morning", "midday", "evening"])
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--duration-sec", required=True, type=int)
    ap.add_argument("--stories-file", required=True)
    a = ap.parse_args()

    mp3 = Path(a.mp3)
    if not mp3.is_file():
        sys.exit(f"MP3 not found: {mp3}")
    local_size = mp3.stat().st_size
    if local_size < 1_000_000:
        sys.exit(f"MP3 suspiciously small ({local_size} bytes), refusing to publish")

    stories = [
        line.strip()
        for line in Path(a.stories_file).read_text().splitlines()
        if line.strip()
    ]
    if not stories:
        sys.exit("stories file is empty, refusing to publish")

    # 1. Ship the MP3 first, so the feed never references a missing file.
    if remote_size(f"{REMOTE_EPISODES}/{mp3.name}") == local_size:
        print(f"remote already has {mp3.name} ({local_size} bytes), skipping copy")
    else:
        run(SCP + [str(mp3), f"hearth:{REMOTE_EPISODES}/"])
        got = remote_size(f"{REMOTE_EPISODES}/{mp3.name}")
        if got != local_size:
            sys.exit(f"copy verification failed: local {local_size} != remote {got}")
        print(f"copied {mp3.name} ({local_size} bytes)")

    # 2. Register the episode (upsert by filename).
    episodes = json.loads(EPISODES_JSON.read_text()) if EPISODES_JSON.exists() else []
    entry = {
        "edition": a.edition,
        "date": a.date,
        "file": mp3.name,
        "bytes": local_size,
        "duration_sec": a.duration_sec,
        "stories": stories,
    }
    episodes = [e for e in episodes if e["file"] != mp3.name] + [entry]
    EPISODES_JSON.write_text(json.dumps(episodes, indent=2) + "\n")

    # 3. Rebuild the feed and deploy it.
    generate_feed.main()
    run(SCP + [str(REPO / "feed.xml"), f"hearth:{REMOTE_DIR}/feed.xml"])
    print("deployed feed.xml")

    # 4. Commit the repo (push failure is non-fatal; hearth already serves it).
    run(["git", "-C", str(REPO), "add", "-A"])
    status = run(["git", "-C", str(REPO), "status", "--porcelain"])
    if status:
        run(["git", "-C", str(REPO), "commit", "-m",
             f"Publish {a.edition} edition {a.date}"])
        try:
            run(["git", "-C", str(REPO), "push"])
            print("pushed to origin")
        except RuntimeError as e:
            print(f"WARNING: git push failed (feed is still live on hearth):\n{e}")
    else:
        print("nothing new to commit")

    print(f"done: {a.edition} {a.date} is live at {generate_feed.BASE_URL}/feed.xml")


if __name__ == "__main__":
    main()
