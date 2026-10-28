"""Step 1: read the CV PDF and let the Groq LLM pull out job-search keywords."""
import json
import os
import re

from langchain_groq import ChatGroq
from pypdf import PdfReader


def read_cv_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise ValueError("Could not read any text from the CV. Is it a scanned image PDF?")
    return text


def extract_skills(cv_text: str) -> list[str]:
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0,
    )
    prompt = (
        "You are a recruiter. Read this CV and list the 6 strongest skills or job titles "
        "this person could search for on a job board.\n"
        "Rules: each item must be 1-2 words (e.g. 'python', 'rag', 'langchain', 'data engineer'). "
        "Reply with ONLY a JSON list of strings, nothing else.\n\n"
        f"CV:\n{cv_text[:6000]}"
    )
    reply = llm.invoke(prompt).content
    match = re.search(r"\[.*\]", reply, re.S)
    if not match:
        raise ValueError(f"LLM did not return a JSON list: {reply}")
    skills = json.loads(match.group(0))
    return [s.strip().lower() for s in skills if isinstance(s, str) and s.strip()]
