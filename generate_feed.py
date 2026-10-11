#!/usr/bin/env python3
"""Build feed.xml for Cheryl's Newscast from episodes.json.

Usage:  python3 generate_feed.py   (run from the repo root)

Reads episodes.json, writes feed.xml. RSS 2.0 with iTunes podcast tags.
Deployed to http://hearth.ts.secwarz.com/feed.xml by publish_edition.py.
"""

import json
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent
EPISODES_JSON = REPO / "episodes.json"
FEED_XML = REPO / "feed.xml"

BASE_URL = "https://feeds.secwarz.com"
ET = ZoneInfo("America/New_York")

# Wall-clock air times per edition, in ET.
AIR_TIMES = {"morning": "04:30", "midday": "11:30", "evening": "17:15"}
EDITION_TITLES = {
    "morning": "Morning briefing",
    "midday": "Midday briefing",
    "evening": "Evening briefing",
}
# Newest episode sorts first in the feed.
EDITION_ORDER = {"morning": 0, "midday": 1, "evening": 2}

CHANNEL = {
    "title": "Cheryl's Newscast",
    "link": BASE_URL + "/",
    "description": (
        "Three short news briefings a day \u2014 morning, midday, evening "
        "\u2014 read by Cheryl Tunt in her trademark deadpan. Private feed."
    ),
    "language": "en-us",
    "author": "Topher",
    "category": "News",
    "image": BASE_URL + "/art/cover.jpg",
}


def episode_pubdate(ep):
    """RFC 2822 pubDate at the edition's air time, in ET."""
    air = AIR_TIMES.get(ep["edition"], "12:00")
    dt = datetime.strptime(f"{ep['date']} {air}", "%Y-%m-%d %H:%M")
    return format_datetime(dt.replace(tzinfo=ET))


def episode_title(ep):
    """'Morning briefing \u2014 Saturday, October 11'."""
    dt = datetime.strptime(ep["date"], "%Y-%m-%d")
    day = f"{dt.strftime('%A')}, {dt.strftime('%B')} {dt.day}"
    return f"{EDITION_TITLES.get(ep['edition'], ep['edition'])} \u2014 {day}"


def episode_description(ep):
    lines = ["Stories in this edition:"]
    lines += [f"\u2022 {s}" for s in ep.get("stories", [])]
    return "\n".join(lines)


def build_item(ep):
    url = f"{BASE_URL}/episodes/{ep['file']}"
    return (
        "    <item>\n"
        f"      <title>{escape(episode_title(ep))}</title>\n"
        f"      <description>{escape(episode_description(ep))}</description>\n"
        f"      <pubDate>{episode_pubdate(ep)}</pubDate>\n"
        f'      <enclosure url="{escape(url)}" length="{ep["bytes"]}" type="audio/mpeg"/>\n'
        f'      <guid isPermaLink="true">{escape(url)}</guid>\n'
        f"      <itunes:duration>{int(ep['duration_sec'])}</itunes:duration>\n"
        "      <itunes:explicit>yes</itunes:explicit>\n"
        "    </item>"
    )


def build_feed(episodes):
    ordered = sorted(
        episodes,
        key=lambda e: (e["date"], EDITION_ORDER.get(e["edition"], 9)),
        reverse=True,
    )
    items = "\n".join(build_item(ep) for ep in ordered)
    c = CHANNEL
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
        "  <channel>\n"
        f"    <title>{escape(c['title'])}</title>\n"
        f"    <link>{escape(c['link'])}</link>\n"
        f"    <description>{escape(c['description'])}</description>\n"
        f"    <language>{c['language']}</language>\n"
        f"    <itunes:author>{escape(c['author'])}</itunes:author>\n"
        "    <itunes:owner>\n"
        f"      <itunes:name>{escape(c['author'])}</itunes:name>\n"
        "    </itunes:owner>\n"
        f"    <itunes:category text=\"{c['category']}\"/>\n"
        "    <itunes:explicit>yes</itunes:explicit>\n"
        "    <itunes:type>episodic</itunes:type>\n"
        f"    <itunes:image href=\"{escape(c['image'])}\"/>\n"
        f"{items}\n"
        "  </channel>\n"
        "</rss>\n"
    )


def main():
    episodes = json.loads(EPISODES_JSON.read_text()) if EPISODES_JSON.exists() else []
    FEED_XML.write_text(build_feed(episodes))
    print(f"wrote {FEED_XML} ({len(episodes)} episodes)")


if __name__ == "__main__":
    main()
