#!/usr/bin/env python3
"""Rebuild feed.xml (RSS 2.0) from the digests in data/. Run after adding a digest."""
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
SITE = "https://mindtheaigap.vercel.app"
PAGE = SITE + "/news.html"
FEED = SITE + "/feed.xml"
DAYS = 14  # how many digests the feed carries
SGT = timezone(timedelta(hours=8))
LABELS = {"zero-day": "Zero-day / exploit", "appsec": "AppSec", "ai": "AI security"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main():
    dates = [d for d in json.loads((ROOT / "data/index.json").read_text())["dates"] if DATE.match(d)]
    dates = sorted(dates, reverse=True)[:DAYS]
    items = []
    for d in dates:
        path = ROOT / "data" / f"{d}.json"
        if not path.exists():
            continue
        y, m, day = map(int, d.split("-"))
        when = datetime(y, m, day, 7, 0, tzinfo=SGT)
        for n, it in enumerate(json.loads(path.read_text()).get("items", [])):
            url = it.get("url", "")
            if not url.startswith("https://") or not it.get("title"):
                continue
            tags = [t for t in [it.get("severity", "")] + list(it.get("cve") or []) if t]
            body = it.get("summary", "")
            if tags:
                body = "[" + " · ".join(tags) + "] " + body
            if it.get("source"):
                body += " (Source: " + it["source"] + ")"
            # stagger by a minute so readers keep the digest's order
            pub = format_datetime(when - timedelta(minutes=n))
            items.append(
                "    <item>\n"
                f"      <title>{escape(it['title'])}</title>\n"
                f"      <link>{escape(url)}</link>\n"
                f"      <guid isPermaLink=\"false\">{escape(d + '|' + url + '|' + it['title'])}</guid>\n"
                f"      <pubDate>{pub}</pubDate>\n"
                f"      <category>{escape(LABELS.get(it.get('category'), 'AppSec'))}</category>\n"
                f"      <description>{escape(body)}</description>\n"
                "    </item>\n"
            )
    built = format_datetime(datetime(*map(int, dates[0].split("-")), 7, 0, tzinfo=SGT)) if dates else ""
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>Daily Security Digest</title>\n"
        f"    <link>{PAGE}</link>\n"
        f'    <atom:link href="{FEED}" rel="self" type="application/rss+xml"/>\n'
        "    <description>Zero-days and exploited vulnerabilities, AppSec, and AI security. "
        "AI-written summaries with links to the original reporting.</description>\n"
        "    <language>en</language>\n"
        f"    <lastBuildDate>{built}</lastBuildDate>\n"
        + "".join(items)
        + "  </channel>\n</rss>\n"
    )
    (ROOT / "feed.xml").write_text(xml, encoding="utf-8")
    print(f"feed.xml: {len(items)} items from {len(dates)} digests")


if __name__ == "__main__":
    main()
