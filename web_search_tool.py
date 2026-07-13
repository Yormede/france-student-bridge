"""Outil de web search via Puppeteer (anti-detect style Obscura)."""
import json
import os
import subprocess
from pathlib import Path


def web_search_puppeteer(query: str, max_results: int = 5) -> dict:
    """Recherche web anti-detect via Puppeteer (similaire a Obscura)."""
    script = Path(__file__).parent / "web_search.js"
    env = os.environ.copy()
    result = subprocess.run(
        ["node", str(script), query, str(max_results)],
        capture_output=True, text=True, timeout=60,
        env=env,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip(), "query": query}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "parse_failed", "raw": result.stdout[:500], "query": query}
