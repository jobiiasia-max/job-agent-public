"""Step 3: let the Groq LLM compare each job with the CV and give a 0-10 score."""
import json
import os
import re

from langchain_groq import ChatGroq


def get_llm() -> ChatGroq:
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0,
        timeout=60,
        max_retries=2,
    )


def score_job(llm: ChatGroq, cv_text: str, job: dict):
    """Returns (score, reason), or None if the LLM call failed."""
    prompt = (
        "You are a strict recruiter. Compare the CV with the job and rate how well "
        "the candidate fits, from 0 (no fit) to 10 (perfect fit).\n"
        'Reply with ONLY JSON like {"score": 7, "reason": "one short sentence"}.\n\n'
        f"CV:\n{cv_text[:5000]}\n\n"
        f"JOB TITLE: {job['title']}\n"
        f"COMPANY: {job['company']}\n"
        f"JOB DESCRIPTION:\n{job['description']}"
    )
    try:
        reply = llm.invoke(prompt).content
        match = re.search(r"\{.*\}", reply, re.S)
        data = json.loads(match.group(0))
        return int(data["score"]), str(data["reason"])
    except Exception as e:
        print(f"  Could not score '{job['title']}': {e}")
        return None
