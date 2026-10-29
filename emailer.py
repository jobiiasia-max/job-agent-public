"""Send emails through the Resend web API (HTTPS)."""
import os

import requests


def _post_email(subject: str, text: str) -> None:
    api_key = os.environ["RESEND_API_KEY"].strip()
    receiver = os.environ["EMAIL_RECEIVER"].strip()

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": "Job Agent <onboarding@resend.dev>",
            "to": [receiver],
            "subject": subject,
            "text": text,
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Resend error {resp.status_code}: {resp.text}")


def send_email(good_jobs: list[dict]) -> None:
    lines = [f"{len(good_jobs)} new job(s) match your CV (best first):\n"]
    for j in good_jobs:
        lines.append(
            f"- {j['title']} at {j['company'] or 'N/A'}  [match {j['score']}/10]\n"
            f"  Why: {j['reason']}\n"
            f"  Source: {j['source']} | Matched skill: {j['keyword']}\n"
            f"  Apply: {j['url']}\n"
        )
    _post_email(
        subject=f"Job Agent: {len(good_jobs)} good match(es) for you",
        text="\n".join(lines),
    )


def send_status_email(message: str) -> None:
    _post_email(subject="Job Agent: no good matches this time", text=message)
