"""
Async wrapper around the unofficial Aniwatch API.
Primary base: https://aniwatch-api.vercel.app
Docs: https://github.com/ghoshRitesh12/aniwatch-api
"""
import logging
import aiohttp
from config import ANIWATCH_API_BASE

logger = logging.getLogger(__name__)

BASE = ANIWATCH_API_BASE.rstrip("/")

_session: aiohttp.ClientSession | None = None
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://aniwatch.to/",
}


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers=HEADERS)
    return _session


async def _get(url: str, params: dict | None = None) -> dict | None:
    session = await _get_session()
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                return await r.json()
            logger.warning("Aniwatch API %s returned %s", url, r.status)
            return None
    except Exception as e:
        logger.error("Aniwatch API error: %s", e)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def search_anime(query: str) -> list[dict]:
    """Returns list of anime dicts: id, name, poster, type, episodes."""
    data = await _get(f"{BASE}/anime/search", {"q": query})
    if not data:
        return []
    animes = data.get("animes") or data.get("results") or []
    result = []
    for a in animes[:10]:
        result.append({
            "id":       a.get("id") or a.get("animeId", ""),
            "name":     a.get("name") or a.get("title", "Unknown"),
            "poster":   a.get("poster") or a.get("image", ""),
            "type":     a.get("type", "TV"),
            "sub_ep":   a.get("episodes", {}).get("sub", 0) if isinstance(a.get("episodes"), dict) else 0,
            "dub_ep":   a.get("episodes", {}).get("dub", 0) if isinstance(a.get("episodes"), dict) else 0,
        })
    return result


async def get_anime_info(anime_id: str) -> dict | None:
    """Full info about an anime including episode list."""
    data = await _get(f"{BASE}/anime/info", {"id": anime_id})
    if not data:
        return None
    info = data.get("anime", {}).get("info", {}) or data.get("info", {}) or data
    seasons = data.get("seasons", [])
    related  = data.get("relatedAnimes", [])
    return {
        "id":          info.get("id", anime_id),
        "name":        info.get("name") or info.get("title", "Unknown"),
        "description": info.get("description", "No description."),
        "poster":      info.get("poster") or info.get("image", ""),
        "type":        info.get("stats", {}).get("type", "?") if isinstance(info.get("stats"), dict) else "?",
        "status":      info.get("stats", {}).get("status", "?") if isinstance(info.get("stats"), dict) else "?",
        "episodes":    info.get("stats", {}).get("episodes", {}) if isinstance(info.get("stats"), dict) else {},
        "rating":      info.get("stats", {}).get("rating", "?") if isinstance(info.get("stats"), dict) else "?",
        "seasons":     seasons,
        "related":     related,
    }


async def get_episodes(anime_id: str) -> list[dict]:
    """Returns list of episode dicts: episodeId, title, number, isFiller."""
    data = await _get(f"{BASE}/anime/episodes", {"animeId": anime_id})
    if not data:
        return []
    eps = data.get("episodes") or []
    result = []
    for e in eps:
        result.append({
            "episode_id": e.get("episodeId", ""),
            "title":      e.get("title") or f"Episode {e.get('number', '?')}",
            "number":     int(e.get("number", 0)),
            "is_filler":  e.get("isFiller", False),
        })
    return result


async def get_episode_sources(
    episode_id: str,
    server: str = "hd-1",
    category: str = "sub",   # "sub" or "dub"
) -> dict | None:
    """
    Returns streaming sources dict:
      tracks, intro, outro, sources (list of {url, type, quality}), anilistID, malID
    """
    data = await _get(
        f"{BASE}/anime/episode-srcs",
        {"id": episode_id, "server": server, "category": category},
    )
    if not data:
        return None
    return {
        "sources":  data.get("sources", []),
        "tracks":   data.get("tracks", []),
        "intro":    data.get("intro", {}),
        "outro":    data.get("outro", {}),
        "server":   server,
        "category": category,
    }


async def get_servers(episode_id: str) -> dict:
    """Returns available servers for sub and dub."""
    data = await _get(f"{BASE}/anime/servers", {"episodeId": episode_id})
    if not data:
        return {"sub": [], "dub": []}
    return {
        "sub": data.get("sub", []),
        "dub": data.get("dub", []),
    }


async def get_schedule(date: str | None = None) -> list[dict]:
    """
    Returns today's (or given date's) airing schedule.
    date format: YYYY-MM-DD
    """
    params = {}
    if date:
        params["date"] = date
    data = await _get(f"{BASE}/anime/schedule", params)
    if not data:
        return []
    return data.get("scheduledAnimes") or data.get("animes") or []


async def get_home() -> dict:
    """Returns trending / spotlight / latest episode animes."""
    data = await _get(f"{BASE}/anime/home")
    return data or {}


async def close_session():
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None
