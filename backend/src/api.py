"""Steam Web API client for browsing Workshop items."""

import os
import re
import requests
from dataclasses import dataclass
from typing import Optional


STEAM_API_BASE = "https://api.steampowered.com"
STEAM_STORE_API = "https://store.steampowered.com/api"
STEAM_COMMUNITY_BASE = "https://steamcommunity.com"


@dataclass
class WorkshopItem:
    workshop_id: str
    title: str
    description: str
    app_id: str
    file_size: int
    subscriptions: int
    favorited: int
    tags: list[str]
    preview_url: str

    def size_human(self) -> str:
        size = self.file_size
        if size == 0:
            return "Unknown"
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


def get_api_key() -> Optional[str]:
    """Get Steam API key from environment variable."""
    return os.environ.get("STEAM_API_KEY")


def parse_workshop_id(url_or_id: str) -> Optional[str]:
    """Extract workshop item ID from URL or return as-is if numeric."""
    if url_or_id.isdigit():
        return url_or_id
    match = re.search(r"[?&]id=(\d+)", url_or_id)
    if match:
        return match.group(1)
    return None


def parse_app_id(url: str) -> Optional[str]:
    """Extract app ID from a Steam Workshop browse URL."""
    if url.isdigit():
        return url
    match = re.search(r"/app/(\d+)/workshop", url)
    if match:
        return match.group(1)
    match = re.search(r"appid=(\d+)", url)
    if match:
        return match.group(1)
    return None


def get_item_details(workshop_ids: list[str]) -> list[WorkshopItem]:
    """Fetch details for one or more workshop items. No API key required."""
    url = f"{STEAM_API_BASE}/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    data = {"itemcount": len(workshop_ids)}
    for i, wid in enumerate(workshop_ids):
        data[f"publishedfileids[{i}]"] = wid

    resp = requests.post(url, data=data)
    resp.raise_for_status()
    result = resp.json()

    items = []
    for file_detail in result["response"].get("publishedfiledetails", []):
        if file_detail.get("result") != 1:
            continue
        items.append(WorkshopItem(
            workshop_id=str(file_detail["publishedfileid"]),
            title=file_detail.get("title", "Unknown"),
            description=file_detail.get("description", ""),
            app_id=str(file_detail.get("consumer_app_id", "")),
            file_size=int(file_detail.get("file_size", 0) or 0),
            subscriptions=file_detail.get("subscriptions", 0),
            favorited=file_detail.get("favorited", 0),
            tags=[t["tag"] for t in file_detail.get("tags", [])],
            preview_url=file_detail.get("preview_url", ""),
        ))
    return items


def browse_workshop_with_key(
    app_id: str,
    api_key: str,
    query_type: int = 1,
    page: int = 1,
    count: int = 20,
    search_text: str = "",
) -> tuple[int, list[WorkshopItem]]:
    """Browse workshop using Steam API key (full metadata)."""
    url = f"{STEAM_API_BASE}/IPublishedFileService/QueryFiles/v1/"
    params = {
        "key": api_key,
        "query_type": query_type,
        "page": page,
        "numperpage": count,
        "appid": app_id,
        "return_metadata": 1,
        "return_tags": 1,
        "return_details": 1,
        "return_short_description": 1,
        "return_previews": 1,
    }
    if search_text:
        params["search_text"] = search_text

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    result = resp.json().get("response", {})

    total = result.get("total", 0)
    file_details = result.get("publishedfiledetails", [])

    items = []
    for f in file_details:
        items.append(WorkshopItem(
            workshop_id=str(f.get("publishedfileid", "")),
            title=f.get("title", "Unknown"),
            description=f.get("short_description", f.get("description", "")),
            app_id=str(f.get("consumer_app_id", app_id)),
            file_size=f.get("file_size", 0),
            subscriptions=f.get("subscriptions", 0),
            favorited=f.get("favorited", 0),
            tags=[t["tag"] for t in f.get("tags", [])],
            preview_url=f.get("preview_url", ""),
        ))
    return total, items


def browse_workshop_no_key(
    app_id: str,
    sort: str = "trend",
    page: int = 1,
    count: int = 20,
    search_text: str = "",
) -> tuple[int, list[WorkshopItem]]:
    """Browse workshop by scraping Steam Community (no API key needed)."""
    sort_map = {"trend": "trend", "top": "toprated", "new": "mostrecent", "favorites": "favorited"}
    browse_sort = sort_map.get(sort, "trend")

    url = f"{STEAM_COMMUNITY_BASE}/workshop/browse/"
    params = {
        "appid": app_id,
        "browsesort": browse_sort,
        "section": "readytouseitems",
        "actualsort": browse_sort,
        "p": page,
        "numperpage": min(count, 30),
    }
    if search_text:
        params["searchtext"] = search_text

    headers = {"User-Agent": "Mozilla/5.0 (compatible; SteamWorkshopDownloader/1.0)"}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()

    # Extract published file IDs from HTML
    ids = re.findall(r"SharedFileBindMouseHover\(\s*['\"]?(\d+)['\"]?", resp.text)
    if not ids:
        # Fallback: extract from data-publishedfileid attributes
        ids = re.findall(r'data-publishedfileid=["\']?(\d+)["\']?', resp.text)

    # Extract total count if available
    total_match = re.search(r'(\d[\d,]*)\s+results', resp.text)
    total = int(total_match.group(1).replace(",", "")) if total_match else len(ids)

    if not ids:
        return 0, []

    items = get_item_details(ids[:count])
    return total, items


def browse_workshop(
    app_id: str,
    query_type: int = 1,
    page: int = 1,
    count: int = 20,
    search_text: str = "",
    sort: str = "trend",
    api_key: Optional[str] = None,
) -> tuple[int, list[WorkshopItem]]:
    """
    Browse workshop items. Uses API key if available, otherwise scrapes Steam Community.
    query_type: 0=ranked, 1=trend, 2=favorites, 3=newest
    Returns (total_count, items)
    """
    key = api_key or get_api_key()
    if key:
        return browse_workshop_with_key(app_id, key, query_type, page, count, search_text)
    else:
        return browse_workshop_no_key(app_id, sort, page, count, search_text)
