"""Step 2: fetch jobs from Remotive (JSON API) and We Work Remotely (RSS feeds)."""
import re

import feedparser
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (job-agent student project)"}

WWR_FEEDS = [
    "https://weworkremotely.com/remote-jobs.rss",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
]


def clean_html(html: str, limit: int = 1500) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def fetch_remotive(keywords: list[str]) -> list[dict]:
    jobs = []
    for kw in keywords:
        try:
            resp = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": kw, "limit": 20},
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            for j in resp.json().get("jobs", []):
                jobs.append(
                    {
                        "source": "Remotive",
                        "keyword": kw,
                        "title": j.get("title", ""),
                        "company": j.get("company_name", ""),
                        "url": j.get("url", ""),
                        "description": clean_html(j.get("description", "")),
                    }
                )
        except Exception as e:
            print(f"[Remotive] problem with '{kw}': {e}")
    return jobs


def fetch_weworkremotely(keywords: list[str]) -> list[dict]:
    jobs = []
    for feed_url in WWR_FEEDS:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"[WeWorkRemotely] problem with {feed_url}: {e}")
            continue

        for entry in feed.entries:
            text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
            for kw in keywords:
                if kw in text:
                    title = entry.get("title", "")
                    company, _, role = title.partition(": ")
                    jobs.append(
                        {
                            "source": "We Work Remotely",
                            "keyword": kw,
                            "title": role or title,
                            "company": company if role else "",
                            "url": entry.get("link", ""),
                            "description": clean_html(entry.get("summary", "")),
                        }
                    )
                    break  # one keyword match is enough
    return jobs
