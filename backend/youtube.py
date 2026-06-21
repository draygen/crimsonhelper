"""
YouTube guide lookup.
With an API key: fetches results inline via YouTube Data API v3.
Without: returns a search URL to open in the browser.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
with open(_root / "config.json") as _f:
    _cfg = json.load(_f)

_API_KEY: str = _cfg.get("youtube_api_key", "")
_GAME = "Crimson Desert"


def search_url(query: str) -> str:
    q = urllib.parse.quote_plus(f"{_GAME} {query}")
    return f"https://www.youtube.com/results?search_query={q}"


def search_api(query: str, max_results: int = 5) -> list[dict]:
    """Returns a list of {title, url, channel, thumbnail} dicts."""
    if not _API_KEY:
        return []
    q = urllib.parse.quote_plus(f"{_GAME} {query}")
    url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={q}&type=video&maxResults={max_results}&key={_API_KEY}"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
        results = []
        for item in data.get("items", []):
            vid_id = item["id"].get("videoId", "")
            snip = item.get("snippet", {})
            results.append({
                "title": snip.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "channel": snip.get("channelTitle", ""),
                "thumbnail": snip.get("thumbnails", {}).get("default", {}).get("url", ""),
            })
        return results
    except Exception as exc:
        print(f"[youtube] API error: {exc}")
        return []


def lookup(query: str, max_results: int = 5) -> dict:
    """Returns {search_url, results: [...], api_available: bool}."""
    results = search_api(query, max_results) if _API_KEY else []
    return {
        "search_url": search_url(query),
        "results": results,
        "api_available": bool(_API_KEY),
    }
