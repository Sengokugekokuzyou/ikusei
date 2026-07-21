"""Image search providers (stdlib urllib; no extra deps).

Each provider.search(query) returns a list of candidate dicts:
  {image_url, page_url, author, license, attribution_required}

Networked providers are used on the user's machine; the parsing is unit-tested
offline. `none` disables fetching (local assets still work via the manager).
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod


class ImageProvider(ABC):
    name = "none"

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[dict]:
        ...


class NoneProvider(ImageProvider):
    name = "none"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        return []


def _get_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-navigator/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


class OpenverseProvider(ImageProvider):
    """Keyless CC image search. Attribution required for the credits list."""

    name = "openverse"
    ENDPOINT = "https://api.openverse.org/v1/images/"

    @staticmethod
    def parse(data: dict) -> list[dict]:
        out = []
        for r in data.get("results", []):
            lic = r.get("license", "")
            ver = r.get("license_version", "")
            out.append({
                "image_url": r.get("url", ""),
                "page_url": r.get("foreign_landing_url", "") or r.get("url", ""),
                "author": r.get("creator", "") or "Unknown",
                "license": f"CC {lic.upper()} {ver}".strip(),
                "attribution_required": True,
            })
        return [o for o in out if o["image_url"]]

    def search(self, query: str, limit: int = 5) -> list[dict]:
        qs = urllib.parse.urlencode({
            "q": query, "page_size": limit,
            "license_type": "commercial", "mature": "false",
        })
        return self.parse(_get_json(f"{self.ENDPOINT}?{qs}"))


class PixabayProvider(ImageProvider):
    """Free commercial-safe photos; no attribution required. Needs a free key."""

    name = "pixabay"
    ENDPOINT = "https://pixabay.com/api/"

    def __init__(self, api_key: str = "") -> None:
        self._key = api_key or os.environ.get("PIXABAY_API_KEY", "")
        if not self._key:
            raise ValueError(
                "PIXABAY_API_KEY が未設定です（.env に設定するか provider を openverse に）。"
            )

    @staticmethod
    def parse(data: dict) -> list[dict]:
        out = []
        for h in data.get("hits", []):
            out.append({
                "image_url": h.get("largeImageURL", "") or h.get("webformatURL", ""),
                "page_url": h.get("pageURL", ""),
                "author": h.get("user", ""),
                "license": "Pixabay Content License",
                "attribution_required": False,
            })
        return [o for o in out if o["image_url"]]

    def search(self, query: str, limit: int = 5) -> list[dict]:
        qs = urllib.parse.urlencode({
            "key": self._key, "q": query, "image_type": "photo",
            "safesearch": "true", "per_page": max(3, limit), "orientation": "horizontal",
        })
        return self.parse(_get_json(f"{self.ENDPOINT}?{qs}"))


def build_image_provider(name: str, *, api_key: str = "") -> ImageProvider:
    name = (name or "none").lower()
    if name in ("none", "local"):
        return NoneProvider()
    if name == "openverse":
        return OpenverseProvider()
    if name == "pixabay":
        return PixabayProvider(api_key=api_key)
    raise ValueError(f"Unknown image provider: {name!r}")
