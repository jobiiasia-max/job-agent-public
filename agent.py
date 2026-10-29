"""Job Agent: CV (PDF) + Remotive + We Work Remotely -> LLM scores each new job -> email the best.

Local (loops forever):   python agent.py
GitHub Actions (once):   RUN_ONCE=1 python agent.py
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from cv_reader import extract_skills, read_cv_text
from emailer import send_email, send_status_email
from job_sources import fetch_remotive, fetch_weworkremotely
from matcher import get_llm, score_job

load_dotenv()

SEEN_FILE = Path("seen_jobs.json")
MIN_SCORE = int(os.getenv("MIN_SCORE", "4"))
MAX_JOBS_PER_RUN = int(os.getenv("MAX_JOBS_PER_RUN", "20"))  # keeps Groq usage low


def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def run_once(keywords: list[str], cv_text: str) -> None:
    print(f"\nChecking jobs for: {keywords}")
    seen = load_seen()
    llm = get_llm()

    # 1. collect jobs we have never seen (no duplicates)
    new_jobs, urls = [], set()
    for job in fetch_remotive(keywords) + fetch_weworkremotely(keywords):
        if job["url"] and job["url"] not in seen and job["url"] not in urls:
            new_jobs.append(job)
            urls.add(job["url"])

    if not new_jobs:
        print("No new jobs this time.")
        return
    

    # 2. score a limited number; the rest wait for the next run
    batch = new_jobs[:MAX_JOBS_PER_RUN]
    print(f"{len(new_jobs)} new job(s). Scoring {len(batch)} with Groq...")
    good_jobs, scored_urls = [], []
    for job in batch:
        result = score_job(llm, cv_text, job)
        time.sleep(2)  # be gentle with Groq rate limits
        if result is None:
            continue  # failed to score, try again next run
        job["score"], job["reason"] = result
        scored_urls.append(job["url"])
        print(f"  {job['score']}/10  {job['title']}")
        if job["score"] >= MIN_SCORE:
            good_jobs.append(job)

    # 3. email only the good matches
        # 3. email the good matches, or a short status email if there are none
    if good_jobs:
        good_jobs.sort(key=lambda j: j["score"], reverse=True)
        try:
            send_email(good_jobs)
            print(f"Email sent with {len(good_jobs)} job(s).")
        except Exception as e:
            print(f"Email failed: {e}")
            return  # do not mark as seen, so we retry next run
    else:
        print(f"No job scored {MIN_SCORE}+ this time.")
        try:
            print("inside try")
            send_status_email(
                f"No job scored {MIN_SCORE}+ this time. "
                f"The agent checked {len(scored_urls)} new job(s)."
            )
            print("try done")
        except Exception as e:
            print(f"Status email failed: {e}")
    seen.update(scored_urls)
    save_seen(seen)


def main() -> None:
    cv_text = os.getenv("CV_TEXT", "").strip()
    if cv_text:
        print("Using CV text from the CV_TEXT secret")
    else:
        cv_path = os.getenv("CV_PATH", "my_cv.pdf")
        print(f"Reading CV: {cv_path}")
        cv_text = read_cv_text(cv_path)

    manual = os.getenv("KEYWORDS", "").strip()
    if manual:
        keywords = [k.strip().lower() for k in manual.split(",") if k.strip()]
    else:
        keywords = extract_skills(cv_text)
    print(f"Skills used for job search: {keywords}")

    run_once(keywords, cv_text)

    # On GitHub Actions we run once and exit; GitHub starts us again on the schedule.
    if os.getenv("RUN_ONCE") == "1":
        return

    import schedule

    minutes = int(os.getenv("CHECK_EVERY_MINUTES", "360"))
    schedule.every(minutes).minutes.do(run_once, keywords, cv_text)
    print(f"Agent running. Checking again every {minutes} minutes. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
